import json
import re
from typing import Any

import pandas as pd

from utils.llm_client import ask_groq


RESULT_COLUMNS = [
    "rank",
    "candidate_name",
    "score",
    "recommendation",
    "matched_skills",
    "missing_skills",
    "strengths",
    "concerns",
    "explanation",
]


def _extract_json(text: str) -> Any:
    """Extract JSON from a Groq response, including fenced JSON."""
    text = (text or "").strip()

    text = re.sub(
        r"^\s*```(?:json)?\s*|\s*```\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting a JSON object or array from surrounding text.
    for opening, closing in (("{", "}"), ("[", "]")):
        start = text.find(opening)
        end = text.rfind(closing)

        if start != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                continue

    raise ValueError("The AI response did not contain valid JSON.")


def _as_list(value: Any) -> list[str]:
    """Convert strings, lists, or other values into clean string lists."""
    if value is None:
        return []

    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        values = re.split(r"[,;\n]+", value)
    else:
        values = [value]

    cleaned = []

    for value in values:
        item = str(value).strip().strip(" -*•\t")
        if item and item not in cleaned:
            cleaned.append(item)

    return cleaned


def _normalize_skill(value: str) -> str:
    """Normalize skill wording for comparisons."""
    return re.sub(r"[^a-z0-9+#.]+", " ", value.lower()).strip()


def _remove_contradicted_matches(candidate: dict) -> dict:
    """
    Remove matched skills that are explicitly listed as missing or
    explicitly contradicted by the candidate's own explanation.
    """
    matched = candidate["matched_skills"]
    missing = candidate["missing_skills"]

    missing_normalized = {_normalize_skill(skill) for skill in missing}

    # Do not claim a skill as matched when it is also listed as missing.
    matched = [
        skill
        for skill in matched
        if _normalize_skill(skill) not in missing_normalized
    ]

    negative_text = " ".join(
        candidate["concerns"] + [candidate["explanation"]]
    ).lower()

    # Catch common explicit statements that contradict a skill match.
    contradiction_patterns = [
        r"\bno evidence of\b",
        r"\blacks?\b",
        r"\bdoes not demonstrate\b",
        r"\bdoesn't demonstrate\b",
        r"\bnot demonstrated\b",
        r"\bnot found\b",
        r"\bno demonstrated experience\b",
        r"\bhas not demonstrated\b",
        r"\bunable to verify\b",
    ]

    filtered = []

    for skill in matched:
        normalized_skill = _normalize_skill(skill)
        contradicted = False

        if normalized_skill:
            for pattern in contradiction_patterns:
                for match in re.finditer(pattern, negative_text):
                    # Examine the words immediately following the
                    # negative phrase for a reference to this skill.
                    following_text = negative_text[match.end():match.end() + 100]
                    if normalized_skill in _normalize_skill(following_text):
                        contradicted = True
                        break

                if contradicted:
                    break

        if not contradicted:
            filtered.append(skill)

    candidate["matched_skills"] = filtered
    return candidate


def _normalize_candidate(item: dict, threshold: int) -> dict:
    """Validate and normalize a single candidate record."""
    name = str(
        item.get("candidate_name")
        or item.get("name")
        or ""
    ).strip()

    raw_score = item.get("score", 0)

    try:
        score = float(raw_score)
        if not 0 <= score <= 100:
            score = 0.0
    except (TypeError, ValueError):
        score = 0.0

    matched = _as_list(
        item.get("matched_skills", item.get("skills_matched", []))
    )
    missing = _as_list(
        item.get("missing_skills", item.get("skills_missing", []))
    )
    strengths = _as_list(item.get("strengths", []))
    concerns = _as_list(
        item.get("concerns", item.get("red_flags", []))
    )
    explanation = str(item.get("explanation", "")).strip()

    # A fixed threshold makes the recommendation consistent with the score.
    evidence_text = " ".join(
        strengths + concerns + [explanation]
    ).lower()

    insufficient_evidence = any(
        phrase in evidence_text
        for phrase in [
            "insufficient evidence",
            "not enough evidence",
            "unable to assess",
            "could not be assessed",
            "insufficient information",
        ]
    )

    if insufficient_evidence:
        recommendation = "Not enough evidence"
    elif score >= threshold:
        recommendation = "Shortlist"
    else:
        recommendation = "Review"

    candidate = {
        "rank": 0,
        "candidate_name": name or "Unknown candidate",
        "score": round(score, 2),
        "recommendation": recommendation,
        "matched_skills": matched,
        "missing_skills": missing,
        "strengths": strengths,
        "concerns": concerns,
        "explanation": explanation,
    }

    return _remove_contradicted_matches(candidate)


def format_screening_results(
    job_title: str,
    report_text: str,
    candidate_names: list[str],
    threshold: int = 60,
) -> list[dict]:
    """Convert a screening report into structured candidate results."""
    if not report_text or not report_text.strip():
        raise ValueError("The screening report is empty.")

    if not candidate_names:
        raise ValueError("No candidate names were supplied.")

    names = list(dict.fromkeys(
        str(name).strip()
        for name in candidate_names
        if str(name).strip()
    ))

    if not names:
        raise ValueError("No valid candidate names were supplied.")

    threshold = max(0, min(100, int(threshold)))

    prompt = f"""
You are a careful information-extraction agent for a resume-screening
decision-support system.

Job title: {job_title}
Shortlisting threshold: {threshold}/100

Exact candidate filenames supplied by the application:
{json.dumps(names, ensure_ascii=False)}

SCREENING REPORT:
<REPORT>
{report_text[:24000]}
</REPORT>

Return ONLY valid JSON using this structure:
{{
  "candidates": [
    {{
      "candidate_name": "exact filename from the supplied list",
      "score": 0,
      "recommendation": "Review",
      "matched_skills": [],
      "missing_skills": [],
      "strengths": [],
      "concerns": [],
      "explanation": "Brief evidence-based explanation"
    }}
  ]
}}

STRICT RULES:
1. Return no more than one record per supplied candidate.
2. Use only exact candidate names from the supplied list.
3. Read each candidate's own section independently. Never transfer skills,
   scores, strengths, or experience from one candidate to another.
4. A matched skill must be explicitly supported for that candidate in the
   report. A skill mentioned only in the job description is NOT a match.
5. If the report says a candidate lacks a skill, that skill must not appear
   in matched_skills.
6. Do not infer qualifications from job titles or unrelated experience.
7. Do not invent evidence, years of experience, certifications, or skills.
8. Preserve a candidate's reported score when clearly available. If there
   is no defensible score, use 0 and explain that it is unavailable.
9. Use "Shortlist" only when the score meets the threshold and the report
   provides sufficient evidence. Otherwise use "Review". Use
   "Not enough evidence" when the report does not support an assessment.
10. List missing skills only when the report explicitly identifies them as
    missing or the evidence clearly establishes the gap.
11. If the report contradicts itself, do not invent a resolution. Remove
    unsupported matches and mention the inconsistency in concerns.
12. Return concise strings and arrays of strings. No markdown fences.
"""

    raw = ask_groq(prompt)
    parsed = _extract_json(raw)

    if isinstance(parsed, dict):
        candidates = parsed.get("candidates", [])
    elif isinstance(parsed, list):
        candidates = parsed
    else:
        raise ValueError("AI JSON did not contain a candidate list.")

    if not isinstance(candidates, list):
        raise ValueError("AI JSON did not contain a candidate list.")

    allowed_names = set(names)
    unique = {}

    for item in candidates:
        if not isinstance(item, dict):
            continue

        candidate = _normalize_candidate(item, threshold)
        name = candidate["candidate_name"]

        # Ignore names that do not match an uploaded candidate exactly.
        if name in allowed_names:
            unique[name] = candidate

    results = list(unique.values())
    results.sort(key=lambda row: row["score"], reverse=True)

    for rank, candidate in enumerate(results, start=1):
        candidate["rank"] = rank

    return results


def results_to_dataframe(results: list[dict]) -> pd.DataFrame:
    """Create a consistent DataFrame for display and CSV export."""
    rows = []

    for result in results:
        row = dict(result)

        for field in (
            "matched_skills",
            "missing_skills",
            "strengths",
            "concerns",
        ):
            row[field] = "; ".join(_as_list(row.get(field)))

        rows.append(row)

    return pd.DataFrame(rows, columns=RESULT_COLUMNS)