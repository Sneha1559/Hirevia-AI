
from utils.screening_service import run_screening


job_description = """
We are hiring a Junior Data Analyst.

Required skills:
- Python
- SQL
- Pandas
- Data cleaning
- Data visualization

Preferred skills:
- Power BI
- Dashboard development

Experience: 0-2 years.
"""

resumes = [
    {
        "name": "python_analyst.pdf",
        "text": """
        Junior Data Analyst with experience in Python, SQL and Pandas.
        Worked on data cleaning, exploratory data analysis and dashboard
        development. Built data visualization projects using Matplotlib.
        """
    },
    {
        "name": "java_developer.pdf",
        "text": """
        Software developer with experience in Java, Spring Boot,
        REST APIs and backend development. Built web applications.
        No data analytics projects mentioned.
        """
    }
]

try:
    output = run_screening(
        job_title="Junior Data Analyst",
        job_description=job_description,
        resumes=resumes,
        threshold=60,
    )

    print("\nFULL SCREENING TEST")
    print("=" * 50)
    print("Processed candidates:", output["processed_count"])
    print("Structured results:", output["structured_count"])

    print("\nCANDIDATE RESULTS")
    print(output["dataframe"].to_string(index=False))

    print("\nVALIDATION")
    assert output["processed_count"] == 2
    assert output["structured_count"] > 0
    assert len(output["results"]) > 0

    print("\nPASS: Full screening pipeline returned results.")

except Exception as error:
    print("\nFAIL: Full screening pipeline failed.")
    print(type(error).__name__, str(error))
