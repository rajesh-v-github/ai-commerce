import re
import textwrap
import time
from typing import Any

import httpx
from ollama import Client

from app.core.config import settings
from app.core.logging import get_logger
from app.utils.product_catalog_defaults import resolve_product_defaults

logger = get_logger("ai_commerce.ollama")

SORANOGEAR_ANALYST_SYSTEM_PROMPT = (
    "You are SoranoGear's senior Commerce & Customer Support AI Analyst. "
    "Before writing any output, carefully analyze the user's exact intent: "
    "(1) identify target entities, chronological rank (latest/most recent vs. oldest/first), "
    "and exact count constraints (such as 'only one', 'top N', or 'all'); "
    "(2) cross-check every fact strictly against the supplied database records—never invent, "
    "guess, or extrapolate order numbers, statuses, dates, tracking details, product names, "
    "prices, stock counts, or specifications; "
    "(3) exclude any record that violates a stated constraint; and "
    "(4) produce only the requested output format (valid JSON when JSON is requested, or "
    "clean plain text without markdown clutter when plain text is requested)."
)

SORANOGEAR_COPYWRITER_SYSTEM_PROMPT = (
    "You are SoranoGear's senior e-commerce technology copywriter. "
    "Write clear, persuasive, strictly factual storefront copy grounded exclusively in "
    "the supplied product metadata without inventing unsupported technical specifications."
)


class AIServiceUnavailableError(RuntimeError):
    """Raised when Ollama and any configured fallback AI service are unavailable."""


def _strip_thinking_blocks(raw_text: str) -> str:
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text or "", flags=re.IGNORECASE)
    return cleaned.strip()


def _wants_json_output(prompt: str) -> bool:
    return bool(
        re.search(
            r"return\s+only\s+valid\s+json",
            prompt or "",
            flags=re.IGNORECASE,
        )
    )


def _call_ollama(
    prompt: str,
    *,
    system_prompt: str = SORANOGEAR_ANALYST_SYSTEM_PROMPT,
    temperature: float = 0.0,
    num_predict: int = 650,
    json_mode: bool | None = None,
) -> str:
    clean_prompt = textwrap.dedent(prompt or "").strip()
    use_json = _wants_json_output(clean_prompt) if json_mode is None else json_mode

    client = Client(host=settings.OLLAMA_BASE_URL)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": clean_prompt})

    chat_kwargs: dict[str, Any] = {
        "model": settings.OLLAMA_MODEL,
        "messages": messages,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "repeat_penalty": 1.12,
            "num_ctx": 4096,
            "num_predict": num_predict,
        },
        "keep_alive": "30m",
    }
    if use_json:
        chat_kwargs["format"] = "json"

    response = client.chat(**chat_kwargs)
    content = _strip_thinking_blocks(response.message.content or "")
    return content if use_json else content.strip('"')


def _call_fallback_provider(
    prompt: str,
    *,
    system_prompt: str = SORANOGEAR_ANALYST_SYSTEM_PROMPT,
    temperature: float = 0.0,
    max_tokens: int = 650,
    json_mode: bool | None = None,
) -> str:
    base_url = (settings.AI_FALLBACK_BASE_URL or "").strip().rstrip("/")
    api_key = (settings.AI_FALLBACK_API_KEY or "").strip()
    model = (settings.AI_FALLBACK_MODEL or "").strip()
    if not (base_url and api_key and model):
        raise AIServiceUnavailableError(
            f"Local Ollama service at {settings.OLLAMA_BASE_URL} "
            f"(model '{settings.OLLAMA_MODEL}') is unreachable, and no external "
            "AI fallback provider is configured."
        )

    clean_prompt = textwrap.dedent(prompt or "").strip()
    use_json = _wants_json_output(clean_prompt) if json_mode is None else json_mode

    endpoint = (
        base_url
        if base_url.endswith("/chat/completions")
        else f"{base_url}/chat/completions"
    )
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": clean_prompt})

    body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if use_json:
        body["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=20.0) as http_client:
        resp = http_client.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        payload = resp.json()
        choices = payload.get("choices") or []
        if not choices:
            raise AIServiceUnavailableError("Fallback AI provider returned no choices.")
        content = _strip_thinking_blocks(
            str(choices[0].get("message", {}).get("content", ""))
        )
        return content if use_json else content.strip('"')


def ask_llm(prompt: str) -> str:
    """Primary analytical LLM entry point shared by Support Copilot and Commerce AI features."""
    start = time.time()
    use_json = _wants_json_output(prompt)
    try:
        content = _call_ollama(
            prompt,
            system_prompt=SORANOGEAR_ANALYST_SYSTEM_PROMPT,
            temperature=0.0,
            num_predict=700,
            json_mode=use_json,
        )
        elapsed = time.time() - start
        logger.info(
            "Ollama call completed in %.2fs (model=%s, json_mode=%s)",
            elapsed,
            settings.OLLAMA_MODEL,
            use_json,
        )
        return content
    except Exception as ollama_exc:
        logger.warning("Ollama request failed: %s", ollama_exc)
        if settings.AI_FALLBACK_BASE_URL and settings.AI_FALLBACK_API_KEY:
            content = _call_fallback_provider(
                prompt,
                system_prompt=SORANOGEAR_ANALYST_SYSTEM_PROMPT,
                temperature=0.0,
                max_tokens=700,
                json_mode=use_json,
            )
            elapsed = time.time() - start
            logger.info("Fallback AI call completed in %.2fs", elapsed)
            return content
        raise


def check_ai_service_status() -> dict[str, Any]:
    """Check whether local Ollama (or configured fallback) is reachable."""
    ollama_available = False
    model_ready = False
    available_models: list[str] = []
    error_detail: str | None = None

    try:
        with httpx.Client(timeout=2.5) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            ollama_available = True
            available_models = [
                str(m.get("name", "")) for m in (data.get("models") or []) if m.get("name")
            ]
            target = settings.OLLAMA_MODEL.lower()
            model_ready = any(
                m.lower() == target or m.lower().startswith(f"{target}:")
                for m in available_models
            )
    except Exception as exc:
        error_detail = str(exc)

    fallback_configured = bool(
        settings.AI_FALLBACK_BASE_URL.strip()
        and settings.AI_FALLBACK_API_KEY.strip()
        and settings.AI_FALLBACK_MODEL.strip()
    )

    return {
        "ollama_available": ollama_available,
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "configured_model": settings.OLLAMA_MODEL,
        "model_ready": model_ready,
        "available_models": available_models,
        "fallback_configured": fallback_configured,
        "fallback_model": settings.AI_FALLBACK_MODEL or None,
        "builtin_fallback_enabled": True,
        "ready": True,
        "mode": (
            "ollama"
            if (ollama_available and model_ready)
            else ("external-fallback" if fallback_configured else "builtin-grounded")
        ),
        "detail": error_detail,
    }


def _humanize_spec_pairs(spec_text: str | None) -> list[str]:
    if not spec_text or not spec_text.strip():
        return []
    parts = [seg.strip() for seg in re.split(r"[|;\n]+", spec_text) if seg.strip()]
    phrases: list[str] = []
    for part in parts:
        if ":" in part:
            label, val = part.split(":", 1)
            clean_val = val.strip().rstrip(".")
            clean_label = label.strip().lower()
            if clean_val:
                if clean_label in {"class", "category", "design", "style", "feature"}:
                    phrases.append(clean_val.lower())
                else:
                    phrases.append(f"{clean_val} ({clean_label})")
        else:
            phrases.append(part.rstrip("."))
    return phrases


def _generate_grounded_copy_fallback(
    *,
    name: str,
    category: str | None = None,
    brand: str | None = None,
    attributes: str | None = None,
    specifications: str | None = None,
    features: str | None = None,
    target_audience: str | None = None,
    tone: str = "balanced",
) -> str:
    clean_name = name.strip()
    defaults = resolve_product_defaults(clean_name, category)
    clean_cat = (category or "").strip() or "technology accessories"
    clean_brand = (brand or "").strip() or defaults.get("brand") or "SoranoGear"
    audience = (
        (target_audience or "").strip()
        or defaults.get("target_audience")
        or "everyday home, office, and mobile setups"
    )
    audience_clause = audience[0].lower() + audience[1:] if audience else audience

    feature_items = [
        item.strip().rstrip(".")
        for item in re.split(r"[,;\n|]+", features or "")
        if item.strip()
    ]
    spec_items = _humanize_spec_pairs(
        specifications if (specifications and specifications.strip()) else defaults.get("specifications")
    )
    short_attr = (
        attributes.strip().rstrip(".")
        if attributes and len(attributes.strip()) <= 140
        else ""
    )

    highlights: list[str] = []
    for candidate in [*feature_items, *spec_items]:
        if candidate and candidate.lower() not in {h.lower() for h in highlights}:
            highlights.append(candidate)

    highlight_summary = (
        ", ".join(highlights[:4])
        if highlights
        else (short_attr.lower() if short_attr else f"dependable {clean_cat.lower()} performance")
    )

    normalized_tone = (tone or "balanced").strip().lower()

    if normalized_tone == "concise":
        return (
            f"The {clean_brand} {clean_name} delivers reliable {clean_cat.lower()} utility built around "
            f"{highlight_summary}. Designed for {audience_clause}, it offers straightforward setup and "
            f"practical day-to-day performance without unnecessary complexity."
        )

    if normalized_tone == "premium":
        return (
            f"Elevate your setup with the {clean_brand} {clean_name}, a refined addition to our {clean_cat} "
            f"collection tailored for {audience_clause}. Thoughtfully engineered around {highlight_summary}, "
            f"it brings cohesive polish and confident everyday capability to modern workspaces.\n\n"
            f"Whether paired with your primary workstation or carried between environments, the {clean_name} "
            f"combines purposeful design with effortless usability for discerning users."
        )

    if normalized_tone == "technical":
        spec_line = (
            f"Key configuration highlights include {highlight_summary}."
            if highlights
            else f"Baseline product classification: {short_attr or clean_cat}."
        )
        return (
            f"The {clean_brand} {clean_name} is a {clean_cat} solution engineered for {audience_clause}. "
            f"{spec_line}\n\n"
            f"Built for consistent operational reliability across daily workflows, the {clean_name} integrates "
            f"cleanly into standard {clean_cat.lower()} deployments while maintaining predictable handling and durability."
        )

    second_sentence = (
        f"Key highlights include {highlight_summary}, giving you practical versatility right out of the box."
        if highlights
        else "Its practical design focuses on dependable performance and seamless everyday usability."
    )
    return (
        f"Designed by {clean_brand} for {audience_clause}, the {clean_name} brings dependable quality to "
        f"the {clean_cat} lineup. {second_sentence}\n\n"
        f"Built to fit effortlessly into daily routines at home, in the office, or on the move, the "
        f"{clean_name} balances comfort, reliability, and clean modern styling."
    )


def _clean_generated_description(raw_text: str) -> str:
    cleaned = _strip_thinking_blocks(raw_text).replace("```", "").strip()
    cleaned = re.sub(
        r"^(?:here(?:'s| is)\s+(?:a|the|your)\s+[^:\n]*:\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"^(?:product\s+description\s*:\s*)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.replace("**", "").strip().strip('"')
    return cleaned


def generate_product_description(
    *,
    name: str,
    category: str | None = None,
    brand: str | None = None,
    attributes: str | None = None,
    specifications: str | None = None,
    features: str | None = None,
    target_audience: str | None = None,
    tone: str = "professional",
) -> dict[str, str]:
    """Generate a factual, SEO-conscious product description using Ollama (with optional fallback)."""
    fact_lines = [f"Product Name: {name.strip()}"]
    if category and category.strip():
        fact_lines.append(f"Category: {category.strip()}")
    if brand and brand.strip():
        fact_lines.append(f"Brand: {brand.strip()}")
    if attributes and attributes.strip():
        fact_lines.append(f"Product Attributes: {attributes.strip()}")
    if specifications and specifications.strip():
        fact_lines.append(f"Specifications: {specifications.strip()}")
    if features and features.strip():
        fact_lines.append(f"Key Features: {features.strip()}")
    if target_audience and target_audience.strip():
        fact_lines.append(f"Target Audience: {target_audience.strip()}")

    supplied_facts = "\n".join(fact_lines)

    prompt = f"""You are a senior e-commerce copywriter writing a product description for an online technology storefront.

Supplied Product Information:
{supplied_facts}

Tone: {tone}

STRICT ACCURACY & QUALITY RULES:
1. Write a compelling, customer-friendly, SEO-conscious product description in 2 short paragraphs (70 to 150 words total).
2. Use ONLY the facts explicitly provided above.
3. NEVER invent technical specifications, processor models, battery capacities, screen resolutions, refresh rates, certifications, waterproof ratings, warranties, or capabilities that are not stated in the Supplied Product Information.
4. Naturally incorporate the product name, category, and brand (if supplied) for search discoverability.
5. Return plain text only. Do NOT include markdown formatting, asterisks, bullet symbols, headings, quotation marks, or introductory phrases like "Here is the product description:".

Write the product description now:"""

    start = time.time()
    try:
        raw = _call_ollama(
            prompt,
            system_prompt=SORANOGEAR_COPYWRITER_SYSTEM_PROMPT,
            temperature=0.25,
            num_predict=300,
            json_mode=False,
        )
        provider = "ollama"
        model_used = settings.OLLAMA_MODEL
    except Exception as ollama_exc:
        logger.warning(
            "Ollama unavailable for product description generation: %s",
            ollama_exc,
        )
        if settings.AI_FALLBACK_BASE_URL and settings.AI_FALLBACK_API_KEY:
            try:
                raw = _call_fallback_provider(
                    prompt,
                    system_prompt=SORANOGEAR_COPYWRITER_SYSTEM_PROMPT,
                    temperature=0.25,
                    max_tokens=300,
                    json_mode=False,
                )
                provider = "fallback"
                model_used = settings.AI_FALLBACK_MODEL
            except Exception as fb_exc:
                logger.warning(
                    "External fallback AI provider also unavailable (%s); using built-in grounded copywriter.",
                    fb_exc,
                )
                raw = _generate_grounded_copy_fallback(
                    name=name,
                    category=category,
                    brand=brand,
                    attributes=attributes,
                    specifications=specifications,
                    features=features,
                    target_audience=target_audience,
                    tone=tone,
                )
                provider = "builtin-ai"
                model_used = "sorano-copywriter-v1"
        else:
            raw = _generate_grounded_copy_fallback(
                name=name,
                category=category,
                brand=brand,
                attributes=attributes,
                specifications=specifications,
                features=features,
                target_audience=target_audience,
                tone=tone,
            )
            provider = "builtin-ai"
            model_used = "sorano-copywriter-v1"

    description = _clean_generated_description(raw)
    if not description:
        raise AIServiceUnavailableError("The AI service returned an empty description.")

    logger.info(
        "Generated AI product description for '%s' in %.2fs via %s (%s)",
        name,
        time.time() - start,
        provider,
        model_used,
    )
    return {
        "description": description,
        "provider": provider,
        "model": model_used,
    }
