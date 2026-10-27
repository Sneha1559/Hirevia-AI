
from utils.hybrid_retriever import HybridRetriever

job_description = """
Data Analyst role requiring Python, SQL, Pandas,
data cleaning, and data visualization.
"""

resumes = [
    {
        "name": "python_candidate",
        "text": (
            "Experienced in Python, SQL, Pandas, data cleaning "
            "and dashboard development."
        ),
    },
    {
        "name": "java_candidate",
        "text": (
            "Experienced in Java, Spring Boot, REST APIs "
            "and backend application development."
        ),
    },
]

retriever = HybridRetriever()

chunks = [resume["text"] for resume in resumes]
retriever.fit(chunks)

results = retriever.retrieve(
    job_description,
    top_k=2,
    use_multi_query=False,
)

print("\nHybrid RAG Retrieval Results")
print("=" * 45)

for index, result in enumerate(results, start=1):
    print(f"\nRank: {index}")
    print("Text:", result.get("text", result))
    print("Score:", result.get("score", "Not provided"))

if results:
    top_text = str(results[0].get("text", results[0])).lower()
    if "python" in top_text or "pandas" in top_text:
        print("\nPASS: Relevant evidence retrieved.")
    else:
        print("\nCHECK: Review the top result for relevance.")
else:
    print("\nFAIL: No evidence retrieved.")
