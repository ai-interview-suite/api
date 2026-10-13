from openai import OpenAI

from app.config import settings

client = OpenAI(
    base_url=settings.openrouter_base_url,
    api_key=settings.openrouter_api_key,
    timeout=30,
)


response = client.chat.completions.create(
    model=settings.ai_model,
    messages=[
        {
            "role": "user",
            "content": "How many r's are in the word 'strawberry'?",
        }
    ],
)


message = response.choices[0].message

print("Model:", response.model)
print("Answer:", message.content)
