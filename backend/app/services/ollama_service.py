import time
from ollama import chat


def ask_llm(prompt: str):

    start = time.time()

    response = chat(
        model="llama3.2:1b",
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.1, "num_predict": 250},
    )

    elapsed = time.time() - start

    print(f"OLLAMA CALL COMPLETED IN " f"{elapsed:.2f}s")

    return response.message.content.strip().strip('"')
