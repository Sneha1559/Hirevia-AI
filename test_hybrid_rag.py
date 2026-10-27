
from utils.hybrid_retriever import HybridRetriever

documents = [
    """
    Candidate A: Python developer with experience in Machine Learning,
    Pandas, NumPy, Scikit-learn, and data preprocessing.
    Built predictive models and evaluated their performance.
    """,
    """
    Candidate B: Full-stack developer skilled in React, JavaScript,
    Node.js, Express, MongoDB, and REST APIs.
    Built an e-commerce web application.
    """,
    """
    Candidate C: Data analyst skilled in SQL, Python, Power BI,
    Excel, data visualization, and statistical analysis.
    Created dashboards and business reports.
    """,
]

retriever = HybridRetriever()
retriever.fit(documents)

query = "Looking for a candidate skilled in Python and machine learning"

results = retriever.retrieve(query, top_k=3, use_multi_query=True)

print("\nHYBRID RAG RETRIEVAL RESULTS")
print("=" * 50)

for rank, result in enumerate(results, start=1):
    print(f"\nRank: {rank} | RRF Score: {result['score']}")
    print(result["text"].strip())
    print("-" * 50)
