
from unittest.mock import patch

from utils.agent_workflow import (
    strengths_agent,
    red_flags_agent,
    ranking_agent,
    threshold_agent,
    build_screening_workflow,
)


def sample_state():
    return {
        "job_description": "Junior Data Analyst requiring Python and SQL.",
        "analysis": "Required skills: Python and SQL.",
        "candidate_reports": {
            "analyst.pdf": "Match Score: 85/100. Python and SQL demonstrated.",
            "developer.pdf": "Match Score: 15/100. No analytics skills demonstrated.",
            "uncertain.pdf": "Unable to determine a reliable score.",
        },
        "resumes": [
            {"name": "analyst.pdf", "text": "Python and SQL projects."},
            {"name": "developer.pdf", "text": "Java backend projects."},
        ],
        "strengths": {},
        "red_flags": {},
        "threshold": 60,
    }


def test_strengths_agent():
    with patch(
        "utils.agent_workflow.ask_groq",
        return_value="Python and SQL experience supported by evidence.",
    ):
        result = strengths_agent(sample_state())

    assert "analyst.pdf" in result["strengths"]
    assert "Python" in result["strengths"]["analyst.pdf"]
    print("PASS: Strengths Agent")


def test_red_flags_agent():
    with patch(
        "utils.agent_workflow.ask_groq",
        return_value="SQL experience cannot be verified.",
    ):
        result = red_flags_agent(sample_state())

    assert "developer.pdf" in result["red_flags"]
    assert "SQL" in result["red_flags"]["developer.pdf"]
    print("PASS: Red Flags Agent")


def test_ranking_agent():
    state = sample_state()
    state["strengths"] = {"analyst.pdf": "Python and SQL"}
    state["red_flags"] = {"analyst.pdf": "No major evidence gaps"}

    with patch(
        "utils.agent_workflow.ask_groq",
        return_value="1. analyst.pdf\n2. developer.pdf",
    ):
        result = ranking_agent(state)

    assert "analyst.pdf" in result["rankings"]
    print("PASS: Ranking Agent")


def test_threshold_agent():
    result = threshold_agent(sample_state())
    decisions = result["threshold_results"]

    assert "Meets" in decisions["analyst.pdf"]
    assert "Below" in decisions["developer.pdf"]
    assert "manual review" in decisions["uncertain.pdf"].lower()

    print("PASS: Threshold Agent")


def test_workflow_structure():
    graph = build_screening_workflow()
    nodes = set(graph.get_graph().nodes)

    expected = {
        "job_analyzer",
        "evidence_retriever",
        "candidate_evaluator",
        "strengths_agent",
        "red_flags_agent",
        "ranking_agent",
        "threshold_agent",
    }

    missing = expected - nodes
    assert not missing, f"Missing workflow nodes: {missing}"

    print("PASS: All seven workflow nodes are registered")


if __name__ == "__main__":
    tests = [
        test_strengths_agent,
        test_red_flags_agent,
        test_ranking_agent,
        test_threshold_agent,
        test_workflow_structure,
    ]

    failures = []

    for test in tests:
        try:
            test()
        except Exception as error:
            failures.append((test.__name__, error))
            print(f"FAIL: {test.__name__}: {error}")

    print(f"\nResults: {len(tests) - len(failures)}/{len(tests)} tests passed.")

    if failures:
        raise SystemExit(1)
