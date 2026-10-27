
from utils.agent_workflow import screen_candidates

job_description = """
Looking for a Python and Machine Learning engineer.
Required skills: Python, Pandas, NumPy, Scikit-learn.
Preferred: SQL and data visualization.
Responsibilities: build and evaluate predictive models.
"""

resumes = [
    {
        "name": "Candidate_A",
        "text": """
        Python developer with Machine Learning experience.
        Skilled in Pandas, NumPy, and Scikit-learn.
        Built predictive models and evaluated their performance.
        """
    },
    {
        "name": "Candidate_B",
        "text": """
        Full-stack developer skilled in React, JavaScript,
        Node.js, Express, and MongoDB.
        Built an e-commerce application.
        """
    },
]

result = screen_candidates(job_description, resumes)

print("\nHIREVIA AI - MULTI-AGENT SCREENING RESULTS")
print("=" * 60)
print(result["result"])
