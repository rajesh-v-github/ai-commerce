# test_ollama.py

from ollama import chat

response = chat(
    model="llama3.1",
    messages=[{"role": "user", "content": "Say hello in one sentence."}],
)

print(response.message.content)
