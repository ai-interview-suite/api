from openai import OpenAI
from app.config import settings

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key,
)


response = client.chat.completions.create(
    model="openrouter/free",
    messages=[
        {
            "role": "user",
            "content": "How many r's are in the word 'strawberry'?",
        }
    ],
    extra_body={
        "reasoning": {
            "enabled": True,
        }
    },
)


message = response.choices[0].message

print("Model:", response.model)
print("Answer:", message.content)
print("Reasoning details available:", bool(message.reasoning_details))