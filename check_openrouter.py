import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
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