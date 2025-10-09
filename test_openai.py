import os
import openai

# Set your API key
openai.api_key = "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"

try:
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Hello, how are you?"}]
    )
    print(response.choices[0].message.content)

except openai.APIError as e:
    print(f"OpenAI Error: {e}" )
except openai.RateLimitError as e:
    print(f"OpenAI Error: {e}" )
except Exception as e:
    print(f"OpenAI Error: {e}" )