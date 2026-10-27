
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, START, END

from utils.llm_client import ask_groq
from utils.hybrid_retriever import HybridRetriever


class ScreeningState(TypedDict, total=False):
    job_description: str
    resumes: List[Dict[str, str]]
    retrieved_evidence: Dict[str, List[Dict[str, Any]]]
    analysis: str
    result: str


def analyze_job(state: ScreeningState):
    """Agent 1: Analyze the job requirements."""
    prompt = f"""
Analyze this job description for resume screening.

Identify:
1. Required technical skills
2. Preferred skills
3. Experience requirements
4. Education requirements
5. Key responsibilities

Job Description:
{state['job_description']}
"""
    return {"analysis": ask_groq(prompt)}


def retrieve_evidence(state: ScreeningState):
    """Agent 2: Retrieve relevant evidence for each resume."""
    retriever = HybridRetriever()

    evidence = {}

    for resume in state["resumes"]:
        name = resume["name"]
        text = resume["text"]

        chunks = [
            text[i:i + 800]
            for i in range(0, len(text), 600)
            if text[i:i + 800].strip()
        ]

        if not chunks:
            evidence[name] = []
            continue

        retriever.fit(chunks)

        evidence[name] = retriever.retrieve(
            state["job_description"],
            top_k=min(4, len(chunks)),
            use_multi_query=True,
        )

    return {"retrieved_evidence": evidence}


def score_and_explain(state: ScreeningState):
    """Agent 3: Evaluate candidates and explain the evidence."""
    reports = []

    for resume in state["resumes"]:
        name = resume["name"]
        evidence = state["retrieved_evidence"].get(name, [])

        evidence_text = "\n".join(
            item["text"] for item in evidence
        ) or "No relevant evidence retrieved."

        prompt = f"""
You are a careful, evidence-based resume screening assistant.

JOB DESCRIPTION:
{state['job_description']}

JOB REQUIREMENT ANALYSIS:
{state['analysis']}

CANDIDATE:
{name}

RETRIEVED RESUME EVIDENCE:
{evidence_text}

Prepare a report with:
- Match score from 0 to 100 (an estimate, not a validated prediction)
- Relevant skills supported by evidence
- Missing or unverified requirements
- Relevant experience and projects
- Short explanation of the score
- Recommendation: Strong Match, Potential Match, or Low Match

Rules:
- Do not invent candidate qualifications.
- Do not treat missing evidence as proof that a skill is absent.
- Base the assessment only on the supplied evidence.
- Ignore personal characteristics unrelated to job requirements.
- Clearly state uncertainty.
"""
        report = ask_groq(prompt)
        reports.append(f"CANDIDATE: {name}\n{report}")

    return {"result": "\n\n" + ("\n" + "=" * 60 + "\n").join(reports)}


def build_screening_workflow():
    workflow = StateGraph(ScreeningState)

    workflow.add_node("job_analyzer", analyze_job)
    workflow.add_node("evidence_retriever", retrieve_evidence)
    workflow.add_node("candidate_evaluator", score_and_explain)

    workflow.add_edge(START, "job_analyzer")
    workflow.add_edge("job_analyzer", "evidence_retriever")
    workflow.add_edge("evidence_retriever", "candidate_evaluator")
    workflow.add_edge("candidate_evaluator", END)

    return workflow.compile()


def screen_candidates(job_description, resumes):
    app = build_screening_workflow()

    return app.invoke({
        "job_description": job_description,
        "resumes": resumes,
    })
