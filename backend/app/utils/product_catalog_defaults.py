import re
from typing import Any

# Curated catalog defaults keyed by normalized product name for existing database records.
# Applied ONLY when the corresponding column on an existing product is NULL or empty,
# never overwriting existing valid product data or images.
PRODUCT_CATALOG_DEFAULTS: dict[str, dict[str, Any]] = {
    "wireless earbuds": {
        "brand": "SoranoAudio",
        "sku": "SG-AUD-001",
        "image_url": "/product-images/wireless-earbuds.jpg",
        "low_stock_threshold": 10,
        "target_audience": "Commuters, remote professionals, and everyday listeners",
        "specifications": "Connectivity: Bluetooth wireless | Feature: Active noise cancellation | Form factor: In-ear earbuds with charging case",
    },
    "bluetooth speaker": {
        "brand": "SoranoAudio",
        "sku": "SG-AUD-002",
        "image_url": "/product-images/bluetooth-speaker.jpg",
        "low_stock_threshold": 8,
        "target_audience": "Home listeners, travelers, and small gatherings",
        "specifications": "Connectivity: Bluetooth wireless | Design: Compact portable speaker | Controls: Integrated top playback controls",
    },
    "gaming mouse": {
        "brand": "SoranoGaming",
        "sku": "SG-GAM-003",
        "image_url": "/product-images/gaming-mouse.jpg",
        "low_stock_threshold": 12,
        "target_audience": "PC gamers and precision desktop users",
        "specifications": "Lighting: Customizable RGB accent lighting | Form factor: Ergonomic right-hand mouse | Use case: Gaming & precision input",
    },
    "mechanical keyboard": {
        "brand": "SoranoGaming",
        "sku": "SG-GAM-004",
        "image_url": "/product-images/mechanical-keyboard.jpg",
        "low_stock_threshold": 10,
        "target_audience": "Gamers, developers, and tactile typing enthusiasts",
        "specifications": "Switch type: Tactile mechanical switches | Backlighting: Illuminated keycaps | Use case: Gaming and high-speed typing",
    },
    "laptop backpack": {
        "brand": "SoranoCarry",
        "sku": "SG-BAG-005",
        "image_url": "/product-images/laptop-backpack.jpg",
        "low_stock_threshold": 8,
        "target_audience": "Business travelers, hybrid workers, and students",
        "specifications": "Compartments: Padded laptop sleeve and organizer pockets | Style: Structured business backpack | Carry: Padded shoulder straps",
    },
    "usb-c hub": {
        "brand": "SoranoConnect",
        "sku": "SG-ACC-006",
        "image_url": "/product-images/usb-c-hub.jpg",
        "low_stock_threshold": 8,
        "target_audience": "Laptop users expanding ports at desk or on the go",
        "specifications": "Ports: 7-in-1 multiport USB-C expansion hub | Host interface: USB Type-C | Enclosure: Compact aluminum housing",
    },
    "webcam hd": {
        "brand": "SoranoVision",
        "sku": "SG-WEB-007",
        "image_url": "/product-images/webcam-hd.jpg",
        "low_stock_threshold": 8,
        "target_audience": "Remote teams, educators, and video conference hosts",
        "specifications": "Resolution: 1080P HD video | Mounting: Monitor and desktop clip mount | Primary use: Video conferencing",
    },
    "wireless keyboard": {
        "brand": "SoranoWork",
        "sku": "SG-KBM-008",
        "image_url": "/product-images/wireless-keyboard.jpg",
        "low_stock_threshold": 10,
        "target_audience": "Office professionals and clean-desk setups",
        "specifications": "Connectivity: Cordless wireless | Profile: Slim low-profile office layout | Key feel: Quiet scissor-style keys",
    },
    "wireless mouse": {
        "brand": "SoranoWork",
        "sku": "SG-KBM-009",
        "image_url": "/product-images/wireless-mouse.jpg",
        "low_stock_threshold": 12,
        "target_audience": "Office and mobile laptop productivity users",
        "specifications": "Connectivity: Wireless | Shape: Contoured office ergonomics | Scroll: Precision scroll wheel",
    },
    "laptop pro 14": {
        "brand": "SoranoCompute",
        "sku": "SG-LAP-010",
        "image_url": "/product-images/laptop-pro-14.jpg",
        "low_stock_threshold": 5,
        "target_audience": "Executives, software engineers, and business professionals",
        "specifications": "Display class: 14-inch form factor | Category: Business productivity notebook | Chassis: Slim portable profile",
    },
    "gaming laptop x": {
        "brand": "SoranoGaming",
        "sku": "SG-LAP-011",
        "image_url": "/product-images/gaming-laptop-x.svg",
        "low_stock_threshold": 5,
        "target_audience": "Enthusiast gamers and demanding creative workloads",
        "specifications": "Class: High-performance gaming notebook | Keyboard: Illuminated gaming deck | Thermal design: Performance vented chassis",
    },
    "smart watch": {
        "brand": "SoranoPulse",
        "sku": "SG-WRB-012",
        "image_url": "/product-images/smart-watch.svg",
        "low_stock_threshold": 8,
        "target_audience": "Fitness-conscious users and active professionals",
        "specifications": "Category: Fitness tracking smartwatch | Display: Color touch watch face | Band: Comfort sport strap",
    },
    "power bank": {
        "brand": "SoranoVolt",
        "sku": "SG-PWR-013",
        "image_url": "/product-images/power-bank.svg",
        "low_stock_threshold": 12,
        "target_audience": "Travelers, commuters, and multi-device mobile users",
        "specifications": "Capacity: 20000mAh portable battery | Form factor: Travel-ready power bank | Use case: Mobile & accessory charging",
    },
    "bluetooth headset": {
        "brand": "SoranoAudio",
        "sku": "SG-AUD-014",
        "image_url": "/product-images/bluetooth-headset.svg",
        "low_stock_threshold": 8,
        "target_audience": "Customer support teams, call centers, and remote communicators",
        "specifications": "Connectivity: Bluetooth wireless | Microphone: Boom voice microphone | Comfort: Padded headset headband",
    },
    "monitor 24": {
        "brand": "SoranoVision",
        "sku": "SG-MON-015",
        "image_url": "/product-images/monitor-24.svg",
        "low_stock_threshold": 5,
        "target_audience": "Home offices, corporate desks, and dual-monitor workstations",
        "specifications": "Screen size: 24-inch diagonal | Panel technology: IPS display | Stand: Desktop ergonomic stand",
    },
}

CATEGORY_FALLBACK_IMAGES: dict[str, str] = {
    "audio": "/product-images/wireless-earbuds.jpg",
    "gaming accessories": "/product-images/gaming-mouse.jpg",
    "laptop bags & cases": "/product-images/laptop-backpack.jpg",
    "computer accessories": "/product-images/usb-c-hub.jpg",
    "webcams & video conferencing": "/product-images/webcam-hd.jpg",
    "keyboards & mice": "/product-images/wireless-keyboard.jpg",
    "laptops": "/product-images/laptop-pro-14.jpg",
    "wearables": "/product-images/smart-watch.svg",
    "power & charging": "/product-images/power-bank.svg",
    "monitors & displays": "/product-images/monitor-24.svg",
}

CATEGORY_SKU_CODES: dict[str, str] = {
    "audio": "AUD",
    "gaming accessories": "GAM",
    "laptop bags & cases": "BAG",
    "computer accessories": "ACC",
    "webcams & video conferencing": "WEB",
    "webcams": "WEB",
    "keyboards & mice": "KBM",
    "laptops": "LAP",
    "wearables": "WRB",
    "power & charging": "PWR",
    "monitors & displays": "MON",
}

DEFAULT_FALLBACK_IMAGE = "/product-images/fallback-product.svg"


def derive_sku_category_code(category: str | None, name: str | None = None) -> str:
    normalized_category = (category or "").strip().casefold()
    if normalized_category in CATEGORY_SKU_CODES:
        return CATEGORY_SKU_CODES[normalized_category]

    combined = f"{category or ''} {name or ''}".casefold()
    keyword_codes = (
        (("earbud", "speaker", "headset", "headphone", "audio"), "AUD"),
        (("gaming",), "GAM"),
        (("backpack", "bag", "case", "sleeve"), "BAG"),
        (("webcam", "camera", "conferencing"), "WEB"),
        (("keyboard", "mouse", "mice"), "KBM"),
        (("laptop", "notebook"), "LAP"),
        (("watch", "wearable", "band"), "WRB"),
        (("power", "charger", "charging", "battery"), "PWR"),
        (("monitor", "display"), "MON"),
        (("hub", "dock", "adapter", "cable", "accessory", "accessories"), "ACC"),
    )
    for keywords, code in keyword_codes:
        if any(kw in combined for kw in keywords):
            return code

    source = (category or "").strip() or (name or "").strip()
    alpha = re.sub(r"[^A-Z0-9]+", "", source.upper())
    if len(alpha) >= 3:
        return alpha[:3]
    if alpha:
        return alpha.ljust(3, "X")
    return "PRD"


def format_serial_sku(
    category: str | None, name: str | None, serial_number: int
) -> str:
    code = derive_sku_category_code(category, name)
    return f"SG-{code}-{max(1, int(serial_number)):03d}"


def resolve_product_defaults(
    name: str | None,
    category: str | None,
    product_id: int | None = None,
) -> dict[str, Any]:
    normalized_name = (name or "").strip().casefold()
    if normalized_name in PRODUCT_CATALOG_DEFAULTS:
        return dict(PRODUCT_CATALOG_DEFAULTS[normalized_name])

    # Partial keyword match for slightly varied product names before falling back to category
    for key, defaults in PRODUCT_CATALOG_DEFAULTS.items():
        if key and key in normalized_name:
            derived = dict(defaults)
            if product_id is not None:
                derived["sku"] = f"SG-PRD-{product_id:03d}"
            else:
                derived["sku"] = None
            return derived

    normalized_category = (category or "").strip().casefold()
    image_url = CATEGORY_FALLBACK_IMAGES.get(
        normalized_category, DEFAULT_FALLBACK_IMAGE
    )
    slug = re.sub(r"[^A-Z0-9]+", "", (category or "PRD").upper())[:3] or "PRD"
    sku = f"SG-{slug}-{product_id:03d}" if product_id is not None else None
    return {
        "brand": "SoranoGear",
        "sku": sku,
        "image_url": image_url,
        "low_stock_threshold": 10,
        "target_audience": "Everyday technology and workspace customers",
        "specifications": None,
    }
