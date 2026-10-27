import re
from typing import Any


def clean_resume_text(text: str) -> str:
    """
    Clean extracted resume text while preserving useful content.
    """

    if not isinstance(text, str):
        raise TypeError("Resume text must be a string.")

    if not text.strip():
        return ""

    # Normalize line endings and remove null characters.
    text = text.replace("\x00", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Remove repeated spaces and tabs.
    text = re.sub(r"[ \t]+", " ", text)

    # Remove excessive blank lines.
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)

    # Repair common PDF extraction artifacts.
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize whitespace around line breaks.
    text = re.sub(r" *\n *", "\n", text)

    return text.strip()


def extract_email_addresses(text: str) -> list[str]:
    """Find email addresses in resume text."""

    if not text:
        return []

    pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"

    return sorted(set(re.findall(pattern, text)))


def extract_phone_numbers(text: str) -> list[str]:
    """
    Find phone-like sequences.

    This is a basic pattern, not a guarantee that every result
    is a valid phone number.
    """

    if not text:
        return []

    pattern = r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)"

    matches = re.findall(pattern, text)

    cleaned_numbers = []

    for number in matches:
        normalized = re.sub(r"\s+", " ", number).strip()

        # Avoid treating short numeric strings as phone numbers.
        digit_count = sum(character.isdigit() for character in normalized)

        if 8 <= digit_count <= 15:
            cleaned_numbers.append(normalized)

    return sorted(set(cleaned_numbers))


def extract_skills(
    text: str,
    skill_catalog: list[str] | None = None,
) -> list[str]:
    """
    Match skills from a configurable catalog.

    This performs literal catalog matching, not semantic AI matching.
    """

    if not text:
        return []

    if skill_catalog is None:
        skill_catalog = [
            "Python",
            "Java",
            "C++",
            "C",
            "JavaScript",
            "TypeScript",
            "HTML",
            "CSS",
            "React",
            "Node.js",
            "Express.js",
            "MongoDB",
            "MySQL",
            "PostgreSQL",
            "SQL",
            "Pandas",
            "NumPy",
            "Scikit-learn",
            "TensorFlow",
            "PyTorch",
            "Machine Learning",
            "Deep Learning",
            "Data Science",
            "Data Analysis",
            "Natural Language Processing",
            "NLP",
            "Generative AI",
            "Large Language Models",
            "LLM",
            "RAG",
            "LangChain",
            "LangGraph",
            "FAISS",
            "BM25",
            "Streamlit",
            "FastAPI",
            "Flask",
            "REST API",
            "Git",
            "GitHub",
            "Linux",
            "Docker",
            "Kubernetes",
            "AWS",
            "Microsoft Azure",
            "Google Cloud",
            "Power BI",
            "Tableau",
            "Excel",
            "Data Structures",
            "Algorithms",
            "Object-Oriented Programming",
            "OOP",
            "DBMS",
            "Operating Systems",
            "Computer Networks",
            "Cybersecurity",
            "SAP",
            "SAP Security",
            "Governance Risk and Compliance",
            "GRC",
        ]

    searchable_text = text.casefold()
    found_skills = []

    for skill in skill_catalog:
        skill = skill.strip()

        if not skill:
            continue

        # Match whole words for short names such as C, C++, and SQL.
        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(skill.casefold())
            + r"(?![A-Za-z0-9])"
        )

        if re.search(pattern, searchable_text):
            found_skills.append(skill)

    # Preserve catalog order while removing duplicates.
    return list(dict.fromkeys(found_skills))


def prepare_resume(
    resume_text: str,
    skill_catalog: list[str] | None = None,
) -> dict[str, Any]:
    """
    Prepare extracted resume text for downstream screening.

    Returns cleaned text and basic extracted metadata.
    """

    cleaned_text = clean_resume_text(resume_text)

    if not cleaned_text:
        raise ValueError(
            "Cannot prepare a resume with empty text."
        )

    return {
        "cleaned_text": cleaned_text,
        "emails": extract_email_addresses(cleaned_text),
        "phone_numbers": extract_phone_numbers(cleaned_text),
        "skills": extract_skills(
            cleaned_text,
            skill_catalog=skill_catalog,
        ),
        "character_count": len(cleaned_text),
        "word_count": len(cleaned_text.split()),
    }