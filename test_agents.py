
from unittest.mock import patch, MagicMock

from utils.agent_workflow import (
    analyze_job,
    retrieve_evidence,
    score_and_explain,
    build_screening_workflow,
)


JOB = "Data Analyst. Required skills: Python, SQL, Pandas."
RESUMES = [
    {
        "name": "candidate1.pdf",
        "text": "Python, SQL, Pandas, and data visualization experience.",
    }
]


def test_job_analyzer():
    with patch(
        "utils.agent_workflow.ask_groq",
        return_value="Required: Python, SQL. Preferred: Power BI.",
    ):
        result = analyze_job({"job_description": JOB})

    assert "analysis" in result
    assert "Python" in result["analysis"]
    print("PASS: Job Analyzer")


def test_evidence_retriever():
    mock_retriever = MagicMock()
    mock_retriever.retrieve.return_value = [
        {
            "text": "Python, SQL, Pandas experience.",
            "score": 0.9,
        }
    ]

    with patch(
        "utils.agent_workflow.HybridRetriever",
        return_value=mock_retriever,
    ):
        result = retrieve_evidence({
            "job_description": JOB,
            "resumes": RESUMES,
        })

    assert "candidate1.pdf" in result["retrieved_evidence"]
    assert len(result["retrieved_evidence"]["candidate1.pdf"]) > 0
    print("PASS: Evidence Retriever")


def test_candidate_evaluator():
    state = {
        "job_description": JOB,
        "analysis": "Python and SQL are required.",
        "resumes": RESUMES,
        "retrieved_evidence": {
            "candidate1.pdf": [
                {"text": "Python, SQL, Pandas experience."}
            ]
        },
    }

    with patch(
        "utils.agent_workflow.ask_groq",
        return_value="Match score: 90/100. Strong Match.",
    ):
        result = score_and_explain(state)

    assert "result" in result
    assert "candidate1.pdf" in result["result"]
    assert "90/100" in result["result"]
    print("PASS: Candidate Evaluator")


def test_workflow_structure():
    workflow = build_screening_workflow()
    graph = workflow.get_graph()
    node_names = set(graph.nodes.keys())

    expected = {
        "job_analyzer",
        "evidence_retriever",
        "candidate_evaluator",
    }

    assert expected.issubset(node_names)
    print("PASS: LangGraph workflow structure")


if __name__ == "__main__":
    tests = [
        test_job_analyzer,
        test_evidence_retriever,
        test_candidate_evaluator,
        test_workflow_structure,
    ]

    failures = 0

    for test in tests:
        try:
            test()
        except Exception as error:
            failures += 1
            print(f"FAIL: {test.__name__}: {error}")

    print(f"\nResults: {len(tests) - failures}/{len(tests)} tests passed.")

    if failures:
        raise SystemExit(1)
