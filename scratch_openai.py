import openai
import os

try:
    openai.api_key = 'fake-key'
    response = openai.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{'role': 'user', 'content': 'test'}]
    )
    print("Success")
except Exception as e:
    print(f"Error: {e}")
