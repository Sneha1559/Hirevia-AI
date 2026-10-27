
from utils.agent_workflow import screen_candidates
from utils.result_formatter import (
    format_screening_results,
    results_to_dataframe,
)


def run_screening(
    job_title: str,
    job_description: str,
    resumes: list[dict],
    threshold: int = 60,
) -> dict:
    """Run Hybrid RAG + seven-agent screening and format results."""

    if not job_description or not job_description.strip():
        raise ValueError("Please provide a job description.")

    if not resumes:
        raise ValueError("Upload at least one resume.")

    valid_resumes = [
        {
            "name": str(resume.get("name") or "Unknown candidate"),
            "text": str(resume.get("text") or "").strip(),
        }
        for resume in resumes
        if str(resume.get("text") or "").strip()
    ]

    if not valid_resumes:
        raise ValueError("No readable resume text was found.")

    threshold = max(0, min(100, int(threshold)))

    # Run all seven agents, passing the configured threshold.
    agent_results = screen_candidates(
        job_description=job_description,
        resumes=valid_resumes,
        threshold=threshold,
    )

    report_text = str(
        agent_results.get("result", "")
        if isinstance(agent_results, dict)
        else agent_results
    )

    if not report_text.strip():
        report_text = "\n\n".join(
            f"CANDIDATE: {name}\n{candidate_report}"
            for name, candidate_report in (
                agent_results.get("candidate_reports", {}).items()
                if isinstance(agent_results, dict)
                else []
            )
        )

    if not report_text.strip():
        raise ValueError("The screening agents did not produce a report.")

    # Preserve the individual agents' outputs for the Streamlit UI.
    strengths = agent_results.get("strengths", {})
    red_flags = agent_results.get("red_flags", {})
    rankings = agent_results.get("rankings", "")
    threshold_results = agent_results.get("threshold_results", {})

    candidate_names = [resume["name"] for resume in valid_resumes]

    structured_results = format_screening_results(
        job_title=job_title,
        report_text=report_text,
        candidate_names=candidate_names,
        threshold=threshold,
    )

    dataframe = results_to_dataframe(structured_results)

    return {
        "job_title": job_title,
        "threshold": threshold,
        "report": report_text,
        "results": structured_results,
        "dataframe": dataframe,
        "processed_count": len(valid_resumes),
        "structured_count": len(structured_results),
        "agent_strengths": strengths,
        "agent_red_flags": red_flags,
        "agent_rankings": rankings,
        "threshold_results": threshold_results,
    }
