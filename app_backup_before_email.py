import re
from datetime import datetime

import pandas as pd
import streamlit as st
import os
from dotenv import load_dotenv
from utils.email_notifier import send_screening_email

load_dotenv()

from utils.resume_parser import extract_text_from_pdf
from utils.resume_preprocessor import prepare_resume
from utils.screening_service import run_screening
from utils.result_formatter import results_to_dataframe
from utils.database import (
    initialize_database,
    save_job,
    get_jobs,
    delete_job,
    save_screening,
    get_screening_history,
    get_screening_details,
)


# =========================================================
# PAGE CONFIGURATION
# =========================================================

st.set_page_config(
    page_title="Hirevia AI",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# CUSTOM STYLING
# =========================================================

st.markdown(
    """
    <style>
    .stApp {
        background-color: #0B1120;
        color: #E5E7EB;
    }

    [data-testid="stSidebar"] {
        background-color: #111827;
        border-right: 1px solid #263449;
    }

    h1, h2, h3 {
        color: #F8FAFC;
    }

    [data-testid="stMetric"] {
        background-color: #111D30;
        border: 1px solid #263449;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #94A3B8;
    }

    [data-testid="stMetricValue"] {
        color: #2DD4BF;
    }

    .metric-card {
        background-color: #111D30;
        border: 1px solid #263449;
        padding: 20px;
        border-radius: 12px;
        min-height: 135px;
    }

    .metric-label {
        color: #94A3B8;
        font-size: 14px;
        margin-bottom: 10px;
    }

    .metric-value {
        color: #2DD4BF;
        font-size: 30px;
        font-weight: 700;
    }

    .metric-caption {
        color: #94A3B8;
        font-size: 12px;
        margin-top: 8px;
    }

    .section-card {
        background-color: #111D30;
        border: 1px solid #263449;
        border-radius: 12px;
        padding: 18px;
    }

    .stButton > button {
        border-radius: 8px;
        min-height: 40px;
    }

    div[data-testid="stFileUploader"] {
        background-color: #111827;
        border-radius: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

try:
    initialize_database()
except Exception as error:
    st.error(f"Database initialization failed: {error}")
    st.stop()


# =========================================================
# SESSION STATE
# =========================================================

DEFAULTS = {
    "uploaded_resumes": [],
    "job_descriptions": [],
    "minimum_threshold": 60,
    "ai_screening_results": [],
    "ai_screening_job": "",
    "ai_structured_results": [],
    "last_screening_session_id": None,
    "agent_strengths": {},
    "agent_red_flags": {},
    "agent_rankings": "",
    "threshold_results": {},
    "loaded_saved_screening": None,
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value.copy() if isinstance(
            value, (dict, list)
        ) else value


# Load saved job profiles from SQLite.
try:
    saved_jobs = get_jobs()

    st.session_state.job_descriptions = [
        {
            "database_id": job["id"],
            "title": job["title"],
            "company": job.get("company", ""),
            "description": job["description"],
            "required_skills": job.get("required_skills", []),
            "preferred_skills": job.get("preferred_skills", []),
            "minimum_experience": job.get("minimum_experience", 0),
            "created_at": job.get("created_at", ""),
        }
        for job in saved_jobs
    ]

except Exception as error:
    st.error(f"Could not load saved job profiles: {error}")


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def metric(label, value, caption=""):
    """Render a dashboard metric using valid HTML."""

    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title, subtitle):
    st.title(title)
    st.caption(subtitle)


def add_resumes(files):
    """Add selected PDF files to the current session."""

    existing = {
        resume["name"]
        for resume in st.session_state.uploaded_resumes
    }

    added = 0

    for file in files or []:
        if file.name in existing:
            continue

        st.session_state.uploaded_resumes.append(
            {
                "name": file.name,
                "content": file.getvalue(),
                "size": file.size,
                "uploaded_at": datetime.now().strftime(
                    "%d %b %Y %H:%M"
                ),
                "extracted_text": "",
                "extraction_error": "",
                "prepared_data": {},
            }
        )

        existing.add(file.name)
        added += 1

    return added


def process_resume(resume):
    """Extract and preprocess text from one PDF resume."""

    try:
        extracted_text = extract_text_from_pdf(resume["content"])

        if not extracted_text or not extracted_text.strip():
            raise ValueError(
                "No text was extracted. This PDF may be scanned or image-only."
            )

        prepared_data = prepare_resume(extracted_text)

        resume["extracted_text"] = extracted_text
        resume["prepared_data"] = prepared_data
        resume["extraction_error"] = ""

        return True, "Resume processed successfully."

    except Exception as error:
        resume["extracted_text"] = ""
        resume["prepared_data"] = {}
        resume["extraction_error"] = str(error)

        return False, str(error)


def clear_ai_results():
    """Clear previous AI results when necessary."""

    st.session_state.ai_screening_results = []
    st.session_state.ai_structured_results = []
    st.session_state.ai_screening_job = ""
    st.session_state.agent_strengths = {}
    st.session_state.agent_red_flags = {}
    st.session_state.agent_rankings = ""
    st.session_state.threshold_results = {}
    st.session_state.last_screening_session_id = None


def get_processed_resumes():
    return [
        resume
        for resume in st.session_state.uploaded_resumes
        if resume.get("extracted_text")
    ]


def get_candidate_name(candidate):
    return candidate.get(
        "candidate_name",
        candidate.get("Candidate", "Unknown candidate"),
    )


def render_candidate_agent_analysis(candidate_names):
    """Display the outputs of the downstream AI agents."""

    st.subheader("Multi-Agent Analysis")

    if not candidate_names:
        st.info("No candidate results are available.")
        return

    selected_candidate = st.selectbox(
        "Select candidate for agent analysis",
        candidate_names,
        key="agent_analysis_candidate",
    )

    strengths = st.session_state.get("agent_strengths", {})
    red_flags = st.session_state.get("agent_red_flags", {})
    rankings = st.session_state.get("agent_rankings", "")
    threshold_results = st.session_state.get("threshold_results", {})

    with st.expander("Strengths Agent", expanded=True):
        st.write(
            strengths.get(
                selected_candidate,
                "No strengths analysis was returned for this candidate.",
            )
        )

    with st.expander("Red Flags Agent"):
        st.write(
            red_flags.get(
                selected_candidate,
                "No red-flag analysis was returned for this candidate.",
            )
        )

    with st.expander("Ranking Agent"):
        if rankings:
            st.write(rankings)
        else:
            st.info("No ranking analysis was returned.")

    with st.expander("Threshold Agent"):
        st.write(
            threshold_results.get(
                selected_candidate,
                "No threshold decision was returned for this candidate.",
            )
        )

    st.caption(
        "AI outputs are decision-support estimates. Review the original "
        "resume evidence before making hiring decisions."
    )



def run_and_save_screening(job):
    """Run screening, save results, and email the recruiter."""

    processed_resumes = get_processed_resumes()

    if not processed_resumes:
        st.error("Please process at least one resume before screening.")
        return

    job_description = (
        f"Job Title: {job['title']}\n"
        f"Company: {job.get('company', '')}\n"
        f"Description: {job['description']}\n"
        f"Required Skills: {', '.join(job.get('required_skills', []))}\n"
        f"Preferred Skills: {', '.join(job.get('preferred_skills', []))}\n"
        f"Minimum Experience: {job.get('minimum_experience', 0)} years"
    )

    workflow_resumes = [
        {
            "name": resume["name"],
            "text": (
                resume.get("prepared_data", {}).get("cleaned_text")
                or resume.get("extracted_text", "")
            ),
        }
        for resume in processed_resumes
    ]

    try:
        with st.spinner(
            "Running Hybrid RAG and the multi-agent screening workflow..."
        ):
            output = run_screening(
                job_title=job["title"],
                job_description=job_description,
                resumes=workflow_resumes,
                threshold=st.session_state.minimum_threshold,
            )

        # Save the screening session first.
        session_id = save_screening(
            output,
            job_id=job.get("database_id"),
        )

        # Preserve existing application state.
        st.session_state.last_screening_session_id = session_id
        st.session_state.ai_structured_results = output.get("results", [])
        st.session_state.agent_strengths = output.get("agent_strengths", {})
        st.session_state.agent_red_flags = output.get("agent_red_flags", {})
        st.session_state.agent_rankings = output.get("agent_rankings", "")
        st.session_state.threshold_results = output.get("threshold_results", {})

        report = output.get("report", "")

        st.session_state.ai_screening_results = [
            {
                "Job Title": job["title"],
                "Candidate Reports": report,
                "Generated At": datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "Session ID": session_id,
            }
        ]

        st.session_state.ai_screening_job = job["title"]
        st.session_state.loaded_saved_screening = None

        # Email notification: do not let email failure undo screening.
        recipient = os.getenv("RECRUITER_EMAIL", "").strip()

        if recipient:
            with st.spinner("Sending screening report email..."):
                email_success, email_message = send_screening_email(
                    recipient_email=recipient,
                    job_title=job["title"],
                    threshold=st.session_state.minimum_threshold,
                    candidates=st.session_state.ai_structured_results,
                    session_id=session_id,
                )

            if email_success:
                st.session_state["last_email_status"] = (
                    f"Email sent successfully to {recipient}"
                )
            else:
                st.session_state["last_email_status"] = email_message
        else:
            st.session_state["last_email_status"] = (
                "Email not sent: RECRUITER_EMAIL is missing from .env"
            )

        st.success(
            f"AI screening completed. Session ID: {session_id}"
        )

        # Display email status without failing the screening.
        email_status = st.session_state.get("last_email_status", "")
        if email_status.startswith("Email sent successfully"):
            st.success(email_status)
        else:
            st.warning(email_status)

        st.rerun()

    except Exception as error:
        st.error(f"AI screening failed: {error}")

        with st.expander("Troubleshooting details"):
            st.write(
                "Check your Groq API key, model configuration, resume text "
                "extraction, and utility function compatibility."
            )
            st.exception(error)



# =========================================================
# SIDEBAR NAVIGATION
# =========================================================

with st.sidebar:
    st.markdown("# 🎯 Hirevia AI")
    st.caption("Goal-Based Multi-Agent Resume Screening")
    st.divider()

    page = st.radio(
        "Navigation",
        [
            "Dashboard",
            "Upload Resumes",
            "Job Descriptions",
            "Screening Goals",
            "Candidate Analysis",
            "Reports",
            "Settings",
        ],
        key="navigation_page",
    )

    st.divider()

    st.caption(
        f"Resumes: {len(st.session_state.uploaded_resumes)}"
    )

    st.caption(
        f"Job profiles: {len(st.session_state.job_descriptions)}"
    )

    st.caption(
        f"Screening threshold: {st.session_state.minimum_threshold}%"
    )


# =========================================================
# DASHBOARD
# =========================================================

if page == "Dashboard":

    page_header(
        "Dashboard",
        "Manage resumes, job profiles, and AI-powered candidate screening.",
    )

    resumes = st.session_state.uploaded_resumes
    jobs = st.session_state.job_descriptions

    processed_count = sum(
        bool(resume.get("extracted_text"))
        for resume in resumes
    )

    try:
        history = get_screening_history(limit=100)
        screening_count = len(history)
    except Exception:
        screening_count = 0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        metric("Resumes", len(resumes), "Uploaded PDF files")

    with col2:
        metric(
            "Processed",
            processed_count,
            "Successfully extracted resumes",
        )

    with col3:
        metric("Job Profiles", len(jobs), "Saved job descriptions")

    with col4:
        metric(
            "AI Screenings",
            screening_count,
            "Saved screening sessions",
        )

    st.divider()
    st.subheader("How Hirevia AI Works")

    workflow_col1, workflow_col2 = st.columns(2)

    with workflow_col1:
        st.markdown(
            """
            **1. Resume Processing**

            - Upload PDF resumes.
            - Extract and clean resume text.
            - Detect relevant skills and information.

            **2. Job Configuration**

            - Create a job profile.
            - Define required and preferred skills.
            - Set a minimum screening threshold.
            """
        )

    with workflow_col2:
        st.markdown(
            """
            **3. Hybrid RAG Retrieval**

            - Dense semantic retrieval.
            - Sparse retrieval using BM25.
            - Multi-query retrieval.
            - Combine relevant evidence for evaluation.

            **4. Multi-Agent Screening**

            - Job Analyzer Agent.
            - Evidence Retrieval Agent.
            - Candidate Evaluation Agent.
            - Strengths and Red Flags Agents.
            - Ranking and Threshold Agents.
            """
        )

    st.info(
        "Start by uploading resumes, creating a job profile, and then "
        "opening Candidate Analysis to run the AI workflow."
    )


# =========================================================
# UPLOAD RESUMES
# =========================================================

elif page == "Upload Resumes":

    page_header(
        "Upload Resumes",
        "Upload PDF resumes, extract text, and prepare candidates for screening.",
    )

    files = st.file_uploader(
        "Select PDF resumes",
        type=["pdf"],
        accept_multiple_files=True,
        key="resume_uploader",
    )

    if st.button(
        "Add Selected Resumes",
        type="primary",
        use_container_width=False,
    ):
        count = add_resumes(files)

        if count:
            st.success(f"Added {count} resume(s).")
        else:
            st.info("No new resumes were added.")

    resumes = st.session_state.uploaded_resumes

    st.divider()
    st.subheader(f"Resume Library ({len(resumes)})")

    if resumes:
        if st.button(
            "Process All Resumes",
            type="primary",
            use_container_width=True,
        ):
            progress = st.progress(0)
            successful = 0

            for index, resume in enumerate(resumes):
                success, _ = process_resume(resume)

                if success:
                    successful += 1

                progress.progress((index + 1) / len(resumes))

            st.success(
                f"Successfully processed {successful} of {len(resumes)} resumes."
            )
            st.rerun()

    if not resumes:
        st.info("No resumes uploaded yet. Select PDF files above.")

    for index, resume in enumerate(resumes):

        with st.expander(resume["name"]):

            st.caption(
                f"File size: {resume['size']:,} bytes · "
                f"Uploaded: {resume['uploaded_at']}"
            )

            if resume.get("extracted_text"):

                st.success("Resume processed successfully.")

                prepared = resume.get("prepared_data", {})

                info1, info2 = st.columns(2)

                with info1:
                    st.metric(
                        "Word Count",
                        prepared.get("word_count", 0),
                    )

                with info2:
                    st.metric(
                        "Character Count",
                        prepared.get("character_count", 0),
                    )

                st.markdown("**Detected Skills**")

                skills = prepared.get("skills", [])

                if skills:
                    st.write(", ".join(skills))
                else:
                    st.write("No skills detected.")

                with st.expander("View Extracted Resume Text"):
                    st.text_area(
                        "Extracted text",
                        value=(
                            prepared.get("cleaned_text")
                            or resume["extracted_text"]
                        ),
                        height=250,
                        key=f"resume_text_{index}",
                    )

            elif resume.get("extraction_error"):
                st.error(resume["extraction_error"])

            else:
                st.warning("Resume has not been processed yet.")

            col_retry, col_remove = st.columns(2)

            with col_retry:
                if st.button(
                    "Extract / Retry",
                    key=f"retry_resume_{index}",
                    use_container_width=True,
                ):
                    success, message = process_resume(resume)

                    if success:
                        st.success(message)
                    else:
                        st.error(message)

                    st.rerun()

            with col_remove:
                if st.button(
                    "Remove Resume",
                    key=f"remove_resume_{index}",
                    use_container_width=True,
                ):
                    st.session_state.uploaded_resumes.pop(index)
                    clear_ai_results()
                    st.rerun()

    st.caption(
        "Uploaded PDF contents are held in Streamlit session state. "
        "Job profiles and screening sessions are stored in SQLite."
    )


# =========================================================
# JOB DESCRIPTIONS
# =========================================================

elif page == "Job Descriptions":

    page_header(
        "Job Descriptions",
        "Create and manage job profiles used by the AI screening workflow.",
    )

    with st.form("job_form", clear_on_submit=True):

        title = st.text_input("Job Title")
        company = st.text_input("Company Name")

        description = st.text_area(
            "Full Job Description",
            height=180,
            placeholder="Enter the responsibilities, qualifications, and role details...",
        )

        required = st.text_input(
            "Required Skills",
            placeholder="Python, SQL, Machine Learning",
        )

        preferred = st.text_input(
            "Preferred Skills",
            placeholder="AWS, NLP, Docker",
        )

        experience = st.number_input(
            "Minimum Experience (years)",
            min_value=0.0,
            max_value=50.0,
            value=0.0,
            step=0.5,
        )

        submitted = st.form_submit_button(
            "Save Job Description",
            type="primary",
            use_container_width=True,
        )

    if submitted:

        if not title.strip() or not description.strip():
            st.error("Enter both a job title and a job description.")

        else:

            required_skills = [
                skill.strip()
                for skill in required.split(",")
                if skill.strip()
            ]

            preferred_skills = [
                skill.strip()
                for skill in preferred.split(",")
                if skill.strip()
            ]

            try:
                save_job(
                    title=title.strip(),
                    description=description.strip(),
                    threshold=st.session_state.minimum_threshold,
                    company=company.strip(),
                    required_skills=required_skills,
                    preferred_skills=preferred_skills,
                    minimum_experience=experience,
                )

                st.success("Job description saved successfully.")
                st.rerun()

            except Exception as error:
                st.error(f"Could not save job description: {error}")

    st.divider()
    st.subheader("Saved Job Profiles")

    jobs = st.session_state.job_descriptions

    if not jobs:
        st.info("No job profiles saved yet.")

    for index, job in enumerate(jobs):

        with st.expander(job["title"]):

            st.write(
                "**Company:**",
                job.get("company") or "Not specified",
            )

            st.markdown("**Job Description**")
            st.write(job["description"])

            st.markdown("**Required Skills**")
            st.write(
                ", ".join(job.get("required_skills", []))
                or "Not specified"
            )

            st.markdown("**Preferred Skills**")
            st.write(
                ", ".join(job.get("preferred_skills", []))
                or "Not specified"
            )

            st.write(
                "**Minimum Experience:**",
                job.get("minimum_experience", 0),
                "years",
            )

            if st.button(
                "Delete Job Profile",
                key=f"delete_job_{index}",
            ):

                database_id = job.get("database_id")

                if database_id is None:
                    st.error("This job profile has no database ID.")

                else:
                    try:
                        deleted = delete_job(database_id)

                        if deleted:
                            st.success("Job profile deleted.")
                            st.rerun()
                        else:
                            st.error("Job profile was not found.")

                    except Exception as error:
                        st.error(f"Could not delete job profile: {error}")


# =========================================================
# SCREENING GOALS
# =========================================================

elif page == "Screening Goals":

    page_header(
        "Screening Goals",
        "Set the minimum AI match score used by the Threshold Agent.",
    )

    st.markdown(
        """
        The threshold defines the minimum AI-reported match score for a
        candidate to meet the configured screening goal. It does not
        change the retrieval algorithm or guarantee hiring suitability.
        """
    )

    threshold = st.slider(
        "Minimum Screening Threshold (%)",
        min_value=0,
        max_value=100,
        value=int(st.session_state.minimum_threshold),
        step=5,
        key="threshold_slider",
    )

    st.metric("Current Threshold", f"{threshold}%")

    if threshold >= 80:
        st.warning(
            "A high threshold is strict and may exclude candidates "
            "whose resumes contain limited evidence."
        )
    elif threshold <= 40:
        st.info(
            "A lower threshold allows more candidates to pass for further review."
        )

    if st.button(
        "Save Screening Threshold",
        type="primary",
    ):
        st.session_state.minimum_threshold = threshold
        st.success(f"Screening threshold saved at {threshold}%.")

    st.divider()
    st.subheader("What the Threshold Agent Does")

    st.markdown(
        """
        1. Receives the candidate's AI evaluation score.
        2. Compares the score with the configured threshold.
        3. Produces a threshold-based recommendation.
        4. Supports recruiter review alongside retrieved resume evidence.
        """
    )


# =========================================================
# CANDIDATE ANALYSIS
# =========================================================

elif page == "Candidate Analysis":

    page_header(
        "Candidate Analysis",
        "Run Hybrid RAG and the multi-agent resume screening workflow.",
    )

    resumes = get_processed_resumes()
    jobs = st.session_state.job_descriptions

    col1, col2, col3 = st.columns(3)

    with col1:
        metric("Processed Resumes", len(resumes))

    with col2:
        metric("Job Profiles", len(jobs))

    with col3:
        metric(
            "AI Threshold",
            f"{st.session_state.minimum_threshold}%",
        )

    if not resumes:
        st.warning(
            "No processed resumes are available. Open Upload Resumes "
            "and click Process All Resumes."
        )

    elif not jobs:
        st.warning(
            "No job profiles are available. Create a profile in Job Descriptions."
        )

    else:

        job_labels = [
            f"{job['title']} — {job.get('company') or 'No company'}"
            for job in jobs
        ]

        selected_label = st.selectbox(
            "Select Job Profile",
            job_labels,
            key="analysis_job_select",
        )

        job = jobs[job_labels.index(selected_label)]

        st.divider()

        st.subheader("Selected Job Requirements")

        st.write("**Job Title:**", job["title"])

        st.write(
            "**Company:**",
            job.get("company") or "Not specified",
        )

        st.write(
            "**Required Skills:**",
            ", ".join(job.get("required_skills", []))
            or "Not specified",
        )

        st.write(
            "**Preferred Skills:**",
            ", ".join(job.get("preferred_skills", []))
            or "Not specified",
        )

        st.write(
            "**Minimum Experience:**",
            job.get("minimum_experience", 0),
            "years",
        )

        with st.expander("View Full Job Description"):
            st.write(job["description"])

        st.divider()

        st.subheader("AI Multi-Agent Screening")

        st.markdown(
            """
            The workflow uses:

            - **Dense retrieval:** Finds semantically relevant resume passages.
            - **BM25 retrieval:** Finds relevant passages using lexical matching.
            - **Multi-query retrieval:** Expands the search with alternate queries.
            - **Job Analyzer Agent:** Identifies the job's requirements.
            - **Candidate Evaluation Agent:** Evaluates retrieved evidence.
            - **Strengths Agent:** Identifies supported candidate strengths.
            - **Red Flags Agent:** Identifies evidence gaps and concerns.
            - **Ranking Agent:** Ranks candidates using job-related evidence.
            - **Threshold Agent:** Applies the screening threshold.
            """
        )

        st.info(
            f"The current minimum screening threshold is "
            f"{st.session_state.minimum_threshold}%."
        )

        if st.button(
            "Run AI Multi-Agent Screening",
            type="primary",
            use_container_width=True,
        ):
            run_and_save_screening(job)

        # Display the latest AI results.
        ai_results = st.session_state.ai_screening_results

        if ai_results:

            st.divider()
            st.subheader("AI Screening Results")

            st.caption(
                f"Job profile: {st.session_state.ai_screening_job}"
            )

            st.caption(
                f"Screening session: "
                f"{st.session_state.last_screening_session_id}"
            )

            report = ai_results[0].get("Candidate Reports", "")
            structured_results = st.session_state.ai_structured_results

            if structured_results:

                st.markdown("### Candidate Rankings")

                structured_df = results_to_dataframe(structured_results)

                st.dataframe(
                    structured_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "Download Candidate Rankings CSV",
                    data=structured_df.to_csv(index=False).encode("utf-8"),
                    file_name="hirevia_candidate_rankings.csv",
                    mime="text/csv",
                    key="download_ai_rankings",
                )

                st.markdown("### Candidate Details")

                candidate_names = []

                for candidate in structured_results:

                    name = get_candidate_name(candidate)
                    candidate_names.append(name)

                    score = candidate.get(
                        "score",
                        candidate.get("Score (%)", "N/A"),
                    )

                    rank = candidate.get(
                        "rank",
                        candidate.get("Rank", "?"),
                    )

                    recommendation = candidate.get(
                        "recommendation",
                        candidate.get("Recommendation", "Review"),
                    )

                    with st.expander(
                        f"#{rank} {name} — {score}%"
                    ):

                        st.write(
                            "**Recommendation:**",
                            recommendation,
                        )

                        matched_skills = candidate.get(
                            "matched_skills",
                            candidate.get("Matched Skills", []),
                        )

                        missing_skills = candidate.get(
                            "missing_skills",
                            candidate.get("Missing Skills", []),
                        )

                        strengths = candidate.get(
                            "strengths",
                            candidate.get("Strengths", []),
                        )

                        concerns = candidate.get(
                            "concerns",
                            candidate.get("Concerns", []),
                        )

                        explanation = candidate.get(
                            "explanation",
                            candidate.get("Explanation", "Not specified"),
                        )

                        if isinstance(matched_skills, list):
                            matched_skills = ", ".join(matched_skills)

                        if isinstance(missing_skills, list):
                            missing_skills = ", ".join(missing_skills)

                        if isinstance(strengths, list):
                            strengths = ", ".join(strengths)

                        if isinstance(concerns, list):
                            concerns = ", ".join(concerns)

                        st.write(
                            "**Matched Skills:**",
                            matched_skills or "Not specified",
                        )

                        st.write(
                            "**Missing Skills:**",
                            missing_skills or "Not specified",
                        )

                        st.write(
                            "**Strengths:**",
                            strengths or "Not specified",
                        )

                        st.write(
                            "**Concerns:**",
                            concerns or "Not specified",
                        )

                        st.write(
                            "**Explanation:**",
                            explanation,
                        )

                st.divider()

                render_candidate_agent_analysis(
                    list(dict.fromkeys(candidate_names))
                )

            else:
                st.warning(
                    "The AI report was generated, but structured candidate "
                    "results were not returned. Review the full report below."
                )

            with st.expander("Full AI Screening Report", expanded=True):
                st.markdown(report if report else "No report was returned.")

            st.download_button(
                "Download Full AI Report",
                data=report.encode("utf-8"),
                file_name="hirevia_ai_screening_report.txt",
                mime="text/plain",
                key="download_full_ai_report",
            )

            st.caption(
                "AI scores are estimates based on retrieved evidence. "
                "Review the original resumes before making hiring decisions."
            )


# =========================================================
# REPORTS
# =========================================================

elif page == "Reports":

    page_header(
        "Reports",
        "View, download, and revisit AI screening results.",
    )

    st.subheader("Latest AI Screening Report")

    ai_results = st.session_state.ai_screening_results

    if ai_results:

        report = ai_results[0].get("Candidate Reports", "")
        structured = st.session_state.ai_structured_results

        st.caption(
            f"Job profile: {st.session_state.ai_screening_job}"
        )

        st.text_area(
            "AI screening report",
            value=report,
            height=300,
            key="latest_ai_report",
        )

        st.download_button(
            "Download AI Report (TXT)",
            data=report.encode("utf-8"),
            file_name="hirevia_ai_screening_report.txt",
            mime="text/plain",
            key="reports_download_ai_txt",
        )

        if structured:

            st.subheader("Candidate Ranking Table")

            ai_df = results_to_dataframe(structured)

            st.dataframe(
                ai_df,
                use_container_width=True,
                hide_index=True,
            )

            st.download_button(
                "Download AI Results (CSV)",
                data=ai_df.to_csv(index=False).encode("utf-8"),
                file_name="hirevia_ai_results.csv",
                mime="text/csv",
                key="reports_download_ai_csv",
            )

    else:
        st.info(
            "No AI screening results are available in this session. "
            "Run a screening from Candidate Analysis."
        )

    st.divider()
    st.subheader("Saved Screening History")

    try:
        history = get_screening_history(limit=50)
    except Exception as error:
        history = []
        st.error(f"Could not load screening history: {error}")

    if history:

        history_df = pd.DataFrame(history)

        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
        )

        session_options = {
            (
                f"#{item['id']} — {item['job_title']} — "
                f"{item['created_at']}"
            ): item["id"]
            for item in history
        }

        selected_session_label = st.selectbox(
            "Select a saved screening session",
            list(session_options.keys()),
            key="saved_session_select",
        )

        if st.button(
            "Load Saved Screening",
            type="primary",
        ):

            try:
                saved = get_screening_details(
                    session_options[selected_session_label]
                )

                if saved:
                    st.session_state.loaded_saved_screening = saved
                    st.success("Saved screening loaded.")
                else:
                    st.error("The selected screening session was not found.")

            except Exception as error:
                st.error(f"Could not load saved screening: {error}")

        saved = st.session_state.get("loaded_saved_screening")

        if saved:

            st.divider()
            st.subheader("Loaded Screening Session")

            st.write(
                "**Job Title:**",
                saved.get("job_title", "Saved screening"),
            )

            st.write(
                "**Threshold:**",
                f"{saved.get('threshold', 'N/A')}%",
            )

            st.write(
                "**Processed Resumes:**",
                saved.get("processed_count", 0),
            )

            st.write(
                "**Created At:**",
                saved.get("created_at", ""),
            )

            candidates = saved.get("candidates", [])

            if candidates:

                saved_df = pd.DataFrame(candidates)

                st.dataframe(
                    saved_df,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "Download Saved Session CSV",
                    data=saved_df.to_csv(index=False).encode("utf-8"),
                    file_name=(
                        f"hirevia_session_{saved.get('id', 'saved')}.csv"
                    ),
                    mime="text/csv",
                    key=f"download_saved_{saved.get('id', 'saved')}",
                )

            st.text_area(
                "Saved Full Report",
                value=saved.get("report", ""),
                height=250,
                key=f"saved_report_{saved.get('id', 'saved')}",
            )

    else:
        st.info(
            "No saved screening sessions yet. Run an AI screening to "
            "create your first saved report."
        )

    st.divider()
    st.subheader("Resume Processing Report")

    resume_rows = []

    for resume in st.session_state.uploaded_resumes:

        prepared = resume.get("prepared_data", {})

        if resume.get("extracted_text"):
            status = "Processed"
        elif resume.get("extraction_error"):
            status = "Failed"
        else:
            status = "Pending"

        resume_rows.append(
            {
                "Resume": resume["name"],
                "Status": status,
                "Words": prepared.get("word_count", 0),
                "Detected Skills": ", ".join(
                    prepared.get("skills", [])
                ),
            }
        )

    if resume_rows:

        resume_df = pd.DataFrame(resume_rows)

        st.dataframe(
            resume_df,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download Resume Processing CSV",
            data=resume_df.to_csv(index=False).encode("utf-8"),
            file_name="hirevia_resume_processing_report.csv",
            mime="text/csv",
            key="download_resume_processing_report",
        )

    else:
        st.info("No resumes have been uploaded yet.")


# =========================================================
# SETTINGS
# =========================================================

elif page == "Settings":

    page_header(
        "Settings",
        "Application information, AI components, and workflow configuration.",
    )

    

    st.subheader("AI Components")

    components = [
        "PDF Resume Text Extraction",
        "Resume Text Preprocessing",
        "Groq Large Language Model",
        "Dense Semantic Retrieval",
        "BM25 Sparse Retrieval",
        "Multi-Query Retrieval",
        "Hybrid RAG Evidence Retrieval",
        "LangGraph Multi-Agent Workflow",
        "Job Analyzer Agent",
        "Candidate Evaluation Agent",
        "Strengths Agent",
        "Red Flags Agent",
        "Ranking Agent",
        "Threshold Agent",
        "SQLite Job Profiles",
        "SQLite Screening History",
        "CSV and TXT Report Exports",
    ]

    for component in components:
        st.markdown(f"- {component}")

    st.divider()
    st.subheader("Multi-Agent Workflow")

    st.markdown(
        """
        **1. Job Analyzer Agent**

        Extracts job requirements, required skills, preferred skills,
        and relevant qualifications from the job description.

        **2. Evidence Retrieval Agent**

        Retrieves relevant resume evidence using dense semantic retrieval,
        BM25 sparse retrieval, and multi-query retrieval.

        **3. Candidate Evaluation Agent**

        Evaluates candidate evidence against job-related requirements and
        generates a match score and explanation.

        **4. Strengths Agent**

        Identifies strengths supported by the available resume evidence.

        **5. Red Flags Agent**

        Highlights missing evidence, possible gaps, and concerns requiring
        recruiter verification.

        **6. Ranking Agent**

        Compares candidates using their job-related screening results.

        **7. Threshold Agent**

        Compares the AI-reported score with the configured screening
        threshold and provides a recommendation.
        """
    )

    st.divider()
    st.subheader("Environment Configuration")

    st.code(
        "GROQ_API_KEY=your_private_api_key\n"
        "GROQ_MODEL=your_configured_model_id",
        language="text",
    )

    st.warning(
        "Keep API keys in your .env file. Never share your real API key "
        "or commit it to a public Git repository."
    )

    st.caption(
        "Hirevia AI is a recruitment decision-support prototype. "
        "AI scores are estimates, not validated predictions. "
        "Human review is required before hiring decisions."
    )
    st.subheader("Automatic Email Notifications")

st.write(
    "A screening summary is emailed to the configured recruiter "
    "after the screening results are saved."
)

configured_email = os.getenv("RECRUITER_EMAIL", "").strip()

if configured_email:
    st.success(f"Recruiter email configured: {configured_email}")
else:
    st.warning(
        "Recruiter email is not configured. Add RECRUITER_EMAIL "
        "to your .env file and restart Streamlit."
    )

st.caption(
    "Email sending uses Gmail SMTP and the App Password stored in .env."
)