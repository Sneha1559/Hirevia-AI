
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key or api_key == "your_actual_groq_api_key":
        raise ValueError(
            "GROQ_API_KEY is missing. Add your Groq API key to the .env file."
        )

    return Groq(api_key=api_key)


def ask_groq(prompt: str) -> str:
    model = os.getenv("GROQ_MODEL")

    if not model or model == "your_available_model_id":
        raise ValueError("Set a valid GROQ_MODEL in your .env file.")

    client = get_groq_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are Hirevia AI, an assistant for explainable "
                    "resume screening and job-description matching."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    return response.choices[0].message.content or ""


if __name__ == "__main__":
    try:
        answer = ask_groq(
            "Reply with exactly: Hirevia AI Groq connection successful."
        )
        print(answer)
    except Exception as error:
        print(f"Groq connection failed: {error}")
