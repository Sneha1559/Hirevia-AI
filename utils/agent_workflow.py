
import re
from typing import TypedDict, List, Dict, Any

from langgraph.graph import StateGraph, START, END

from utils.llm_client import ask_groq
from utils.hybrid_retriever import HybridRetriever


class ScreeningState(TypedDict, total=False):
    job_description: str
    resumes: List[Dict[str, str]]
    retrieved_evidence: Dict[str, List[Dict[str, Any]]]
    analysis: str
    candidate_reports: Dict[str, str]
    strengths: Dict[str, str]
    red_flags: Dict[str, str]
    rankings: str
    threshold: int
    threshold_results: Dict[str, str]
    result: str


def analyze_job(state: ScreeningState):
    """Agent 1: Extract job requirements."""
    prompt = f"""
Analyze the job description below.

Identify:
1. Required skills
2. Preferred skills
3. Required experience
4. Education or certifications explicitly required
5. Key responsibilities

Separate mandatory requirements from preferred requirements.
Do not invent requirements.

JOB DESCRIPTION:
{state['job_description']}

Return a concise, structured analysis.
"""
    return {"analysis": ask_groq(prompt)}


def retrieve_evidence(state: ScreeningState):
    """Agent 2: Retrieve relevant evidence separately for each resume."""
    evidence = {}
    job_description = state["job_description"]

    for resume in state["resumes"]:
        name = resume["name"]
        text = (resume.get("text") or "").strip()

        if not text:
            evidence[name] = []
            continue

        # Overlapping chunks preserve context near chunk boundaries.
        chunks = [
            text[i:i + 1000]
            for i in range(0, len(text), 750)
            if text[i:i + 1000].strip()
        ]

        retriever = HybridRetriever()
        retriever.fit(chunks)

        evidence[name] = retriever.retrieve(
            job_description,
            top_k=min(5, len(chunks)),
            use_multi_query=True,
        )

    return {"retrieved_evidence": evidence}


def score_and_explain(state: ScreeningState):
    """Agent 3: Evaluate each candidate using only their retrieved evidence."""
    reports = {}

    for resume in state["resumes"]:
        name = resume["name"]
        evidence = state.get("retrieved_evidence", {}).get(name, [])

        evidence_text = "\n\n".join(
            f"Evidence {index}:\n{item.get('text', '')}"
            for index, item in enumerate(evidence, start=1)
            if item.get("text")
        )

        if not evidence_text.strip():
            evidence_text = "No relevant resume evidence was retrieved."

        prompt = f"""
You are a careful resume-screening evaluator.

JOB DESCRIPTION:
{state['job_description']}

JOB REQUIREMENT ANALYSIS:
{state.get('analysis', '')}

CANDIDATE NAME:
{name}

RETRIEVED EVIDENCE FROM THIS CANDIDATE'S RESUME ONLY:
{evidence_text}

Evaluate this candidate against the job requirements.

Return these exact sections:

Match Score: <integer from 0 to 100>
Recommendation: <Strong Match, Potential Match, Low Match, or Not Enough Evidence>
Matched Skills:
- ...
Missing or Unverified Requirements:
- ...
Relevant Experience and Projects:
- ...
Evidence-Based Strengths:
- ...
Concerns:
- ...
Explanation:
...

STRICT RULES:
- Use only evidence provided above for this candidate.
- A skill mentioned in the job description is not proof the candidate has it.
- Only list a skill as matched when the resume evidence supports it.
- Never transfer information from another candidate.
- Distinguish "not demonstrated in the resume" from "does not have the skill."
- Do not invent experience, projects, education, or certifications.
- If evidence is inadequate, say so clearly and avoid false precision.
- Base the score on demonstrated required skills and relevant experience.
- Keep the score consistent with the written explanation.
- Ignore personal characteristics unrelated to job requirements.
"""
        reports[name] = ask_groq(prompt)

    combined = "\n\n".join(
        f"CANDIDATE: {name}\n{report}"
        for name, report in reports.items()
    )

    return {
        "candidate_reports": reports,
        "result": combined,
    }


def strengths_agent(state: ScreeningState):
    """Agent 4: Summarize supported strengths per candidate."""
    output = {}

    for name, report in state.get("candidate_reports", {}).items():
        evidence = state.get("retrieved_evidence", {}).get(name, [])

        evidence_text = "\n".join(
            item.get("text", "")
            for item in evidence
            if item.get("text")
        )

        prompt = f"""
Identify this candidate's job-related strengths.

JOB REQUIREMENTS:
{state.get('analysis', '')}

CANDIDATE EVALUATION:
{report}

CANDIDATE'S RETRIEVED RESUME EVIDENCE:
{evidence_text or 'No relevant evidence retrieved.'}

Rules:
- Include only skills, projects, and experience supported by the evidence.
- Do not repeat job requirements as candidate qualifications.
- Do not invent achievements or proficiency levels.
- If evidence is insufficient, state that explicitly.
- Keep the response concise.
"""
        output[name] = ask_groq(prompt)

    return {"strengths": output}


def red_flags_agent(state: ScreeningState):
    """Agent 5: Identify evidence gaps and job-related concerns."""
    output = {}

    for name, report in state.get("candidate_reports", {}).items():
        evidence = state.get("retrieved_evidence", {}).get(name, [])

        evidence_text = "\n".join(
            item.get("text", "")
            for item in evidence
            if item.get("text")
        )

        prompt = f"""
Identify evidence gaps and concerns for this candidate.

JOB REQUIREMENTS:
{state.get('analysis', '')}

CANDIDATE EVALUATION:
{report}

RETRIEVED RESUME EVIDENCE:
{evidence_text or 'No relevant evidence retrieved.'}

Rules:
- Identify required skills or experience not demonstrated in the evidence.
- Identify unclear or inconsistent job-related information.
- Missing evidence does not prove a candidate lacks a skill.
- Do not invent concerns or misconduct.
- Ignore personal characteristics unrelated to the job.
- If no specific concern is established, say so.
- Keep the response concise.
"""
        output[name] = ask_groq(prompt)

    return {"red_flags": output}


def _extract_score(report: str):
    """Extract an explicitly labelled score from an evaluation."""
    patterns = [
        r"(?im)^\s*(?:estimated\s+)?match\s+score\s*[:=-]\s*(\d{1,3}(?:\.\d+)?)\s*(?:/100)?\b",
        r"(?im)^\s*score\s*[:=-]\s*(\d{1,3}(?:\.\d+)?)\s*(?:/100)?\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, report or "")
        if match:
            try:
                score = float(match.group(1))
                if 0 <= score <= 100:
                    return score
            except ValueError:
                pass

    return None


def ranking_agent(state: ScreeningState):
    """Agent 6: Rank candidates using evidence and reported scores."""
    candidate_details = []

    for resume in state["resumes"]:
        name = resume["name"]
        report = state.get("candidate_reports", {}).get(name, "")
        strengths = state.get("strengths", {}).get(name, "")
        concerns = state.get("red_flags", {}).get(name, "")
        score = _extract_score(report)

        candidate_details.append(
            f"""
Candidate: {name}
Reported match score: {score if score is not None else 'Unavailable'}

Evaluation:
{report}

Evidence-supported strengths:
{strengths}

Evidence gaps and concerns:
{concerns}
"""
        )

    prompt = f"""
Rank candidates for the following job using job-related evidence.

JOB DESCRIPTION:
{state['job_description']}

JOB REQUIREMENT ANALYSIS:
{state.get('analysis', '')}

CANDIDATES:
{"".join(candidate_details)}

Return a numbered ranking. For each candidate provide:
- Exact candidate name
- Existing reported score, if available
- Evidence-based reason for placement
- Important evidence gaps

Rules:
- Rank by demonstrated required skills and relevant experience.
- Do not invent or change scores.
- Do not treat missing evidence as proof of inability.
- Do not transfer skills between candidates.
- Ignore personal characteristics unrelated to the job.
- If evidence is insufficient, clearly state that.
"""
    return {"rankings": ask_groq(prompt)}


def threshold_agent(state: ScreeningState):
    """Agent 7: Apply the user's configured score threshold."""
    threshold = max(0, min(100, int(state.get("threshold", 60))))
    output = {}

    for name, report in state.get("candidate_reports", {}).items():
        score = _extract_score(report)

        if score is None:
            output[name] = (
                f"Manual review required: no valid labelled score was found. "
                f"Configured threshold: {threshold}/100."
            )
        elif score >= threshold:
            output[name] = (
                f"Meets the configured score threshold "
                f"({score:g}/100 >= {threshold}/100). "
                f"Review supporting evidence before shortlisting."
            )
        else:
            output[name] = (
                f"Below the configured score threshold "
                f"({score:g}/100 < {threshold}/100). "
                f"Review the full application before making a decision."
            )

    return {"threshold_results": output}


def build_screening_workflow():
    """Build the seven-agent LangGraph workflow."""
    workflow = StateGraph(ScreeningState)

    workflow.add_node("job_analyzer", analyze_job)
    workflow.add_node("evidence_retriever", retrieve_evidence)
    workflow.add_node("candidate_evaluator", score_and_explain)
    workflow.add_node("strengths_agent", strengths_agent)
    workflow.add_node("red_flags_agent", red_flags_agent)
    workflow.add_node("ranking_agent", ranking_agent)
    workflow.add_node("threshold_agent", threshold_agent)

    workflow.add_edge(START, "job_analyzer")
    workflow.add_edge("job_analyzer", "evidence_retriever")
    workflow.add_edge("evidence_retriever", "candidate_evaluator")
    workflow.add_edge("candidate_evaluator", "strengths_agent")
    workflow.add_edge("strengths_agent", "red_flags_agent")
    workflow.add_edge("red_flags_agent", "ranking_agent")
    workflow.add_edge("ranking_agent", "threshold_agent")
    workflow.add_edge("threshold_agent", END)

    return workflow.compile()


def screen_candidates(
    job_description,
    resumes,
    threshold=60,
):
    """Run the complete multi-agent screening workflow."""
    if not job_description or not job_description.strip():
        raise ValueError("Job description cannot be empty.")

    if not resumes:
        raise ValueError("Upload at least one resume.")

    app = build_screening_workflow()

    return app.invoke({
        "job_description": job_description,
        "resumes": resumes,
        "threshold": threshold,
    })
