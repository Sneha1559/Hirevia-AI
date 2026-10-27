
from utils.llm_client import ask_groq

prompt = """
You are testing a resume-screening AI.

Job requirements: Python, SQL, and Pandas.
Candidate evidence: Python and SQL experience; no Pandas evidence provided.

Return:
1. Identified matching skills
2. Missing or unverified skills
3. A brief explanation

Do not invent qualifications.
"""

try:
    response = ask_groq(prompt)

    if not response or not str(response).strip():
        print("FAIL: Groq returned an empty response.")
    else:
        print("PASS: Groq returned a response.")
        print("\nResponse:")
        print(response)

except Exception as error:
    print("FAIL: Groq test failed.")
    print(type(error).__name__, str(error))
