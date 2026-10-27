import re
from datetime import datetime
import pandas as pd
import streamlit as st
from utils.resume_parser import extract_text_from_pdf
from utils.resume_preprocessor import prepare_resume
from utils.screening_service import run_screening
from utils.result_formatter import results_to_dataframe
from utils.database import (
    initialize_database,
    save_job,
    get_jobs,
    save_screening,
    get_screening_history,
    get_screening_details,
)
# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="Hirevia AI",
    page_icon="🎯",
    layout="wide",
)
st.markdown("""
<style>
.stApp {
    background: #0B1120;
    color: #E5E7EB;
}
[data-testid="stSidebar"] {
    background: #111827;
}
h1, h2, h3 {
    color: #F8FAFC;
}
.metric {
    background: #111D30;
    border: 1px solid #263449;
    padding: 18px;
    border-radius: 12px;
}
.metric-label {
    color: #94A3B8;
    font-size: 13px;
}
.metric-value {
    font-size: 27px;
    font-weight: bold;
    color: #2DD4BF;
}
.stButton > button {
    border-radius: 8px;
    min-height: 42px;
}
</style>
""", unsafe_allow_html=True)
# Initialize persistent storage
initialize_database()
# =========================================================
initialize_database()

# SESSION STATE
# =========================================================
DEFAULTS = {
    "uploaded_resumes": [],
    "job_descriptions": [],
    "screening_weights": {
        "Skills Match": 35,
        "Experience": 25,
        "Education": 15,
        "Preferred Skills": 15,
        "Projects": 10,
    },
    "minimum_threshold": 60,
    "require_all_skills": False,
    "analysis_results": [],
    "ai_screening_results": [],
    "ai_screening_job": "",
    "ai_structured_results": [],
    "last_screening_session_id": None,
    "ai_structured_results": [],
    "last_screening_session_id": None,
}
for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value
# =========================================================
# HELPERS
# =========================================================
def metric(label, value, caption=""):
    st.markdown(
        f"""
        <div class="metric">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-label">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
def page_header(title, subtitle):
    st.title(title)
    st.caption(subtitle)
def add_resumes(files):
    existing = {
        resume["name"]
        for resume in st.session_state.uploaded_resumes
    }
    added = 0
    for file in files or []:
        if file.name in existing:
            continue
        st.session_state.uploaded_resumes.append({
            "name": file.name,
            "content": file.getvalue(),
            "size": file.size,
            "uploaded_at": datetime.now().strftime(
                "%d %b %Y %H:%M"
            ),
            "extracted_text": "",
            "extraction_error": "",
            "prepared_data": {},
        })
        existing.add(file.name)
        added += 1
    return added
def process_resume(resume):
    try:
        text = extract_text_from_pdf(resume["content"])
        prepared = prepare_resume(text)
        resume["extracted_text"] = text
        resume["prepared_data"] = prepared
        resume["extraction_error"] = ""
        return True, "Resume processed successfully."
    except Exception as error:
        resume["extraction_error"] = str(error)
        resume["extracted_text"] = ""
        resume["prepared_data"] = {}
        return False, str(error)
def normalize_skill(skill):
    return re.sub(r"\s+", " ", skill.strip().casefold())
def experience_from_text(text):
    patterns = [
        r"(\d+(?:\.\d+)?)\+?\s*years?\s+(?:of\s+)?experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*years?",
    ]
    values = []
    for pattern in patterns:
        for match in re.findall(pattern, text, re.IGNORECASE):
            try:
                values.append(float(match))
            except ValueError:
                pass
    return max(values, default=0.0)
def score_candidate(resume, job):
    """Transparent rule-based baseline score."""
    prepared = resume.get("prepared_data", {})
    text = prepared.get("cleaned_text", "")
    if not text:
        text = resume.get("extracted_text", "")
    text_lower = text.casefold()
    detected_skills = {
        normalize_skill(skill)
        for skill in prepared.get("skills", [])
    }
    required = job.get("required_skills", [])
    preferred = job.get("preferred_skills", [])
    required_found = [
        skill for skill in required
        if normalize_skill(skill) in detected_skills
    ]
    preferred_found = [
        skill for skill in preferred
        if normalize_skill(skill) in detected_skills
    ]
    skills_score = (
        100 * len(required_found) / len(required)
        if required else (100 if detected_skills else 0)
    )
    preferred_score = (
        100 * len(preferred_found) / len(preferred)
        if preferred else 100
    )
    actual_experience = experience_from_text(text)
    target_experience = float(
        job.get("minimum_experience", 0)
    )
    experience_score = (
        100 if target_experience <= 0
        else min(100, 100 * actual_experience / target_experience)
    )
    education_terms = [
        "b.tech", "btech", "bachelor", "b.e.", "b.sc",
        "m.tech", "mtech", "master", "ph.d", "phd", "degree",
    ]
    project_terms = [
        "project", "projects", "developed",
        "implementation", "github", "built",
    ]
    education_score = (
        100 if any(term in text_lower for term in education_terms)
        else 0
    )
    project_score = (
        100 if any(term in text_lower for term in project_terms)
        else 0
    )
    component_scores = {
        "Skills Match": skills_score,
        "Experience": experience_score,
        "Education": education_score,
        "Preferred Skills": preferred_score,
        "Projects": project_score,
    }
    weights = st.session_state.screening_weights
    total_weight = sum(weights.values())
    final_score = (
        sum(component_scores[name] * weight
            for name, weight in weights.items()) / total_weight
        if total_weight else 0
    )
    missing_required = [
        skill for skill in required
        if skill not in required_found
    ]
    meets_threshold = (
        final_score >= st.session_state.minimum_threshold
    )
    if st.session_state.require_all_skills and missing_required:
        meets_threshold = False
    return {
        "Candidate": resume["name"],
        "Job Title": job["title"],
        "Score (%)": round(final_score, 2),
        "Decision": (
            "Meets Criteria" if meets_threshold
            else "Below Criteria"
        ),
        "Required Skills Found": ", ".join(required_found),
        "Missing Required Skills": ", ".join(missing_required),
        "Preferred Skills Found": ", ".join(preferred_found),
        "Detected Experience (years)": actual_experience,
        "Education Indicator (%)": education_score,
        "Project Indicator (%)": project_score,
        "Skills Score (%)": round(skills_score, 2),
        "Experience Score (%)": round(experience_score, 2),
        "Preferred Skills Score (%)": round(preferred_score, 2),
    }
# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("# 🎯 Hirevia AI")
    st.caption("Multi-Agent Resume Screening System")
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
    )
    st.divider()
    st.caption(
        f"Resumes: {len(st.session_state.uploaded_resumes)}"
    )
    st.caption(
        f"Job profiles: {len(st.session_state.job_descriptions)}"
    )
# =========================================================
# DASHBOARD
# =========================================================
if page == "Dashboard":
    page_header(
        "Dashboard",
        "Manage resumes, job profiles, and AI-powered screening.",
    )
    resumes = st.session_state.uploaded_resumes
    jobs = st.session_state.job_descriptions
    processed = sum(bool(r.get("extracted_text")) for r in resumes)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric("Resumes", len(resumes), "Uploaded PDFs")
    with c2:
        metric("Processed", processed, "Readable resumes")
    with c3:
        metric("Job Profiles", len(jobs), "Saved descriptions")
    with c4:
        metric(
            "AI Reports",
            len(st.session_state.ai_screening_results),
            "Candidate reports",
        )
    st.divider()
    st.subheader("Workflow")
    st.markdown("""
    1. Upload PDF resumes and process their text.
    2. Create a job profile with required and preferred skills.
    3. Configure the baseline screening weights.
    4. Run rule-based matching or AI screening.
    5. Review evidence and candidate explanations.
    6. Export your reports.
    """)
    st.info(
        "AI screening uses Groq, Hybrid RAG, and the LangGraph "
        "workflow. Baseline scores are calculated separately using "
        "rule-based heuristics."
    )
# =========================================================
# UPLOAD RESUMES
# =========================================================
elif page == "Upload Resumes":
    page_header(
        "Upload Resumes",
        "Upload PDF resumes and extract candidate information.",
    )
    files = st.file_uploader(
        "Select PDF resumes",
        type=["pdf"],
        accept_multiple_files=True,
    )
    if st.button("Add Selected Resumes", type="primary"):
        count = add_resumes(files)
        if count:
            st.success(f"Added {count} resume(s).")
        else:
            st.info("No new files added.")
    resumes = st.session_state.uploaded_resumes
    st.divider()
    st.subheader(f"Resume Library ({len(resumes)})")
    if resumes and st.button(
        "Process All Resumes",
        type="primary",
        use_container_width=True,
    ):
        progress = st.progress(0)
        success_count = 0
        for i, resume in enumerate(resumes):
            success, _ = process_resume(resume)
            if success:
                success_count += 1
            progress.progress((i + 1) / len(resumes))
        st.success(
            f"Processed {success_count} of {len(resumes)} resumes."
        )
        st.rerun()
    for index, resume in enumerate(resumes):
        with st.expander(resume["name"]):
            st.caption(f"File size: {resume['size']:,} bytes")
            if resume.get("extracted_text"):
                st.success("Resume processed successfully.")
                prepared = resume.get("prepared_data", {})
                st.write(f"Words: {prepared.get('word_count', 0)}")
                st.write(
                    f"Characters: {prepared.get('character_count', 0)}"
                )
                st.write("**Detected Skills**")
                skills = prepared.get("skills", [])
                st.write(", ".join(skills) if skills else "None detected")
                with st.expander("View Extracted Text"):
                    st.text_area(
                        "Resume text",
                        value=(
                            prepared.get("cleaned_text")
                            or resume["extracted_text"]
                        ),
                        height=220,
                        key=f"resume_text_{index}",
                    )
            elif resume.get("extraction_error"):
                st.error(resume["extraction_error"])
            if st.button("Extract / Retry", key=f"retry_{index}"):
                success, message = process_resume(resume)
                if success:
                    st.success(message)
                else:
                    st.error(message)
                st.rerun()
            if st.button("Remove Resume", key=f"remove_{index}"):
                st.session_state.uploaded_resumes.pop(index)
                st.session_state.analysis_results = []
                st.session_state.ai_screening_results = []
                st.rerun()
    st.caption(
        "Resumes are held in Streamlit session state, not a permanent database."
    )
# =========================================================
# JOB DESCRIPTIONS
# =========================================================
elif page == "Job Descriptions":
    page_header(
        "Job Descriptions",
        "Create job profiles for candidate screening.",
    )
    with st.form("job_form", clear_on_submit=True):
        title = st.text_input("Job Title")
        company = st.text_input("Company")
        description = st.text_area("Full Job Description", height=180)
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
            step=0.5,
        )
        submitted = st.form_submit_button(
            "Save Job Description",
            type="primary",
        )
    if submitted:
        if not title.strip() or not description.strip():
            st.error("Enter both a job title and description.")
        else:
            job_record = {
                "title": title.strip(),
                "company": company.strip(),
                "description": description.strip(),
                "required_skills": [s.strip() for s in required.split(",") if s.strip()],
                "preferred_skills": [s.strip() for s in preferred.split(",") if s.strip()],
                "minimum_experience": experience,
                "created_at": datetime.now().isoformat(),
            }
            try:
                job_record["database_id"] = save_job(
                    job_record["title"],
                    (
                        f"Company: {job_record['company']}\n"
                        f"Description: {job_record['description']}\n"
                        f"Required skills: {', '.join(job_record['required_skills'])}\n"
                        f"Preferred skills: {', '.join(job_record['preferred_skills'])}\n"
                        f"Minimum experience: {job_record['minimum_experience']} years"
                    ),
                    st.session_state.minimum_threshold,
                )
            except Exception as error:
                st.warning(f"Could not persist job to SQLite: {error}")
            st.session_state.job_descriptions.append(job_record)
            st.success("Job description saved.")
            st.rerun()
    st.divider()
    st.subheader("Saved Job Profiles")
    for index, job in enumerate(st.session_state.job_descriptions):
        with st.expander(job["title"]):
            st.write("**Company:**", job.get("company") or "Not specified")
            st.write(job["description"])
            st.write(
                "**Required skills:**",
                ", ".join(job["required_skills"]) or "None",
            )
            st.write(
                "**Preferred skills:**",
                ", ".join(job["preferred_skills"]) or "None",
            )
            st.write(
                "**Minimum experience:**",
                job["minimum_experience"],
                "years",
            )
            if st.button("Delete Job", key=f"delete_job_{index}"):
                st.session_state.job_descriptions.pop(index)
                st.session_state.analysis_results = []
                st.session_state.ai_screening_results = []
                st.rerun()
# =========================================================
# SCREENING GOALS
# =========================================================
elif page == "Screening Goals":
    page_header(
        "Screening Goals",
        "Configure weights for the rule-based baseline score.",
    )
    new_weights = {}
    for name, old_value in st.session_state.screening_weights.items():
        new_weights[name] = st.slider(
            name,
            min_value=0,
            max_value=100,
            value=int(old_value),
            key=f"slider_{name}",
        )
    total = sum(new_weights.values())
    st.subheader(f"Total weight: {total}%")
    if total == 100:
        st.success("Weights total 100%.")
    else:
        st.warning("Weights must total exactly 100%.")
    threshold = st.slider(
        "Minimum Baseline Screening Score (%)",
        min_value=0,
        max_value=100,
        value=int(st.session_state.minimum_threshold),
    )
    require_all = st.checkbox(
        "Require all required skills to be present",
        value=st.session_state.require_all_skills,
    )
    if st.button("Save Screening Goals", type="primary"):
        if total != 100:
            st.error("Weights must total exactly 100%.")
        else:
            st.session_state.screening_weights = new_weights
            st.session_state.minimum_threshold = threshold
            st.session_state.require_all_skills = require_all
            st.success("Screening goals saved.")
    st.caption(
        "These weights apply to baseline matching, not the LLM-generated "
        "AI match estimates."
    )
# =========================================================
# CANDIDATE ANALYSIS
# =========================================================
elif page == "Candidate Analysis":
    page_header(
        "Candidate Analysis",
        "Compare rule-based matching with AI-powered screening.",
    )
    resumes = [
        r for r in st.session_state.uploaded_resumes
        if r.get("extracted_text")
    ]
    jobs = st.session_state.job_descriptions
    c1, c2, c3 = st.columns(3)
    with c1:
        metric("Processed Resumes", len(resumes))
    with c2:
        metric("Job Profiles", len(jobs))
    with c3:
        metric("Baseline Threshold", f"{st.session_state.minimum_threshold}%")
    if not resumes:
        st.warning("Upload resumes and click Process All Resumes first.")
    elif not jobs:
        st.warning("Create a job description first.")
    else:
        job_labels = [
            f"{job['title']} — {job.get('company') or 'No company'}"
            for job in jobs
        ]
        selected_label = st.selectbox("Select Job Description", job_labels)
        selected_index = job_labels.index(selected_label)
        job = jobs[selected_index]
        st.markdown("**Required Skills**")
        st.write(", ".join(job["required_skills"]) or "None specified")
        st.markdown("**Preferred Skills**")
        st.write(", ".join(job["preferred_skills"]) or "None specified")
        st.divider()
        st.subheader("Choose Screening Method")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Rule-Based Matching")
            st.caption(
                "Weighted skills, experience, education, and project indicators."
            )
            if st.button(
                "Run Baseline Matching",
                type="secondary",
                use_container_width=True,
            ):
                results = [
                    score_candidate(resume, job)
                    for resume in resumes
                ]
                results.sort(
                    key=lambda item: item["Score (%)"],
                    reverse=True,
                )
                for rank, result in enumerate(results, start=1):
                    result["Rank"] = rank
                st.session_state.analysis_results = results
                st.session_state.ai_screening_results = []
                st.session_state.ai_screening_job = ""
                st.rerun()
        with col2:
            st.markdown("### AI Multi-Agent Screening")
            st.caption(
                "Groq + Dense Retrieval + BM25 + Multi-Query + LangGraph."
            )
            if st.button(
                "Run AI Screening",
                type="primary",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Running Hybrid RAG + LangGraph screening..."):
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
                            for resume in resumes
                        ]
                        output = run_screening(
                            job_title=job["title"],
                            job_description=job_description,
                            resumes=workflow_resumes,
                            threshold=st.session_state.minimum_threshold,
                        )
                    session_id = save_screening(output, job_id=job.get("database_id"))
                    st.session_state.last_screening_session_id = session_id
                    st.session_state.ai_structured_results = output["results"]
                    st.session_state.ai_screening_results = [{
                        "Job Title": job["title"],
                        "Candidate Reports": output["report"],
                        "Generated At": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "Session ID": session_id,
                    }]
                    st.session_state.ai_screening_job = job["title"]
                    st.success(f"AI screening completed and saved as session #{session_id}.")
                    st.rerun()
                except Exception as error:
                    st.error(f"AI screening failed: {error}")
                    st.info(
                        "Check your .env configuration, Groq model access, "
                        "dependencies, and the terminal traceback."
                    )
        # Display baseline results
        results = st.session_state.analysis_results
        if results:
            st.divider()
            st.subheader("Baseline Candidate Rankings")
            results_df = pd.DataFrame(results)
            preferred_columns = [
                "Rank",
                "Candidate",
                "Job Title",
                "Score (%)",
                "Decision",
                "Required Skills Found",
                "Missing Required Skills",
            ]
            st.dataframe(
                results_df[preferred_columns],
                use_container_width=True,
                hide_index=True,
            )
            st.subheader("Baseline Candidate Details")
            for result in results:
                with st.expander(
                    f"#{result['Rank']} {result['Candidate']} "
                    f"— {result['Score (%)']}%"
                ):
                    st.write("**Decision:**", result["Decision"])
                    st.write(
                        "**Required skills found:**",
                        result["Required Skills Found"] or "None",
                    )
                    st.write(
                        "**Missing required skills:**",
                        result["Missing Required Skills"] or "None",
                    )
                    st.write(
                        "**Preferred skills found:**",
                        result["Preferred Skills Found"] or "None",
                    )
                    st.json({
                        key: value for key, value in result.items()
                        if key.endswith("(%)")
                        or key == "Detected Experience (years)"
                    })
            st.caption(
                "Baseline scores use heuristics and are not validated hiring "
                "recommendations. Missing information does not prove a candidate "
                "lacks a skill."
            )
        # Display AI results
        ai_results = st.session_state.ai_screening_results
        if ai_results:
            st.divider()
            st.subheader("AI Screening Report")
            st.caption(
                f"Job profile: {st.session_state.ai_screening_job}"
            )
            report = ai_results[0]["Candidate Reports"]
            structured_results = st.session_state.get("ai_structured_results", [])
            if structured_results:
                st.subheader("Structured Candidate Rankings")
                structured_df = results_to_dataframe(structured_results)
                st.dataframe(structured_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Candidate Rankings (CSV)",
                    data=structured_df.to_csv(index=False).encode("utf-8"),
                    file_name="hirevia_candidate_rankings.csv",
                    mime="text/csv",
                    type="primary",
                )
                for candidate in structured_results:
                    with st.expander(
                        f"#{candidate.get('rank', '?')} "
                        f"{candidate.get('candidate_name', 'Candidate')} "
                        f"— {candidate.get('score', 'N/A')}%"
                    ):
                        st.write("**Recommendation:**", candidate.get("recommendation", "Not specified"))
                        st.write("**Matched skills:**", ", ".join(candidate.get("matched_skills", [])) or "Not specified")
                        st.write("**Missing skills:**", ", ".join(candidate.get("missing_skills", [])) or "Not specified")
                        st.write("**Strengths:**", ", ".join(candidate.get("strengths", [])) or "Not specified")
                        st.write("**Concerns:**", ", ".join(candidate.get("concerns", [])) or "Not specified")
                        st.write("**Explanation:**", candidate.get("explanation", "Not specified"))
            st.subheader("Full AI Screening Report")
            st.markdown(report)
            st.download_button(
                "Download AI Screening Report (TXT)",
                data=report.encode("utf-8"),
                file_name="hirevia_ai_screening_report.txt",
                mime="text/plain",
                type="primary",
            )
            ai_csv_df = (
                results_to_dataframe(st.session_state.ai_structured_results)
                if st.session_state.get("ai_structured_results")
                else pd.DataFrame(ai_results)
            )
            st.download_button(
                "Download AI Screening Results (CSV)",
                data=ai_csv_df.to_csv(index=False).encode("utf-8"),
                file_name="hirevia_ai_screening_results.csv",
                mime="text/csv",
            )
            st.caption(
                "AI scores and recommendations are estimates generated from "
                "retrieved evidence. Review the underlying resume and verify "
                "claims before making hiring decisions."
            )
# =========================================================
# REPORTS
# =========================================================
elif page == "Reports":
    page_header(
        "Reports",
        "Review and export baseline and AI screening results.",
    )
    results = st.session_state.analysis_results
    st.subheader("Baseline Screening Report")
    if results:
        df = pd.DataFrame(results)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download Baseline Report (CSV)",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="hirevia_baseline_report.csv",
            mime="text/csv",
            type="primary",
        )
    else:
        st.info("No baseline results yet.")
    st.divider()
    st.subheader("AI Screening Report")
    ai_results = st.session_state.ai_screening_results
    if ai_results:
        report = ai_results[0]["Candidate Reports"]
        st.text_area(
            "Latest AI report",
            value=report,
            height=300,
        )
        st.download_button(
            "Download AI Report (TXT)",
            data=report.encode("utf-8"),
            file_name="hirevia_ai_screening_report.txt",
            mime="text/plain",
        )
    else:
        st.info("No AI screening results yet.")
    st.divider()
    st.subheader("Saved Screening History")
    history = get_screening_history(limit=50)
    if history:
        history_df = pd.DataFrame(history)
        st.dataframe(history_df, use_container_width=True, hide_index=True)
        session_options = {
            f"#{item['id']} — {item['job_title']} — {item['created_at']}": item["id"]
            for item in history
        }
        selected_session_label = st.selectbox(
            "View saved screening session", list(session_options.keys())
        )
        if st.button("Load Saved Screening", key="load_saved_screening"):
            saved = get_screening_details(session_options[selected_session_label])
            if saved:
                st.session_state["loaded_saved_screening"] = saved
                st.success("Saved screening loaded below.")
        saved = st.session_state.get("loaded_saved_screening")
        if saved:
            st.markdown(
                f"**{saved['job_title']}** · Threshold {saved['threshold']}% · "
                f"{saved['processed_count']} resumes · {saved['created_at']}"
            )
            if saved.get("candidates"):
                saved_df = pd.DataFrame(saved["candidates"])
                st.dataframe(saved_df, use_container_width=True, hide_index=True)
                st.download_button(
                    "Download Saved Session CSV",
                    data=saved_df.to_csv(index=False).encode("utf-8"),
                    file_name=f"hirevia_session_{saved['id']}.csv",
                    mime="text/csv",
                    key=f"download_saved_{saved['id']}",
                )
            st.text_area(
                "Saved full report",
                value=saved.get("report", ""),
                height=220,
                key=f"saved_report_{saved['id']}",
            )
    else:
        st.info("No saved AI screening sessions yet.")

    st.subheader("Resume Processing Report")
    resume_rows = []
    for resume in st.session_state.uploaded_resumes:
        prepared = resume.get("prepared_data", {})
        resume_rows.append({
            "Resume": resume["name"],
            "Status": (
                "Processed" if resume.get("extracted_text")
                else "Failed" if resume.get("extraction_error")
                else "Pending"
            ),
            "Words": prepared.get("word_count", 0),
            "Detected Skills": ", ".join(prepared.get("skills", [])),
        })
    if resume_rows:
        resume_df = pd.DataFrame(resume_rows)
        st.dataframe(
            resume_df,
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download Resume Report (CSV)",
            data=resume_df.to_csv(index=False).encode("utf-8"),
            file_name="hirevia_resume_report.csv",
            mime="text/csv",
        )
    else:
        st.info("No resumes uploaded yet.")
# =========================================================
# SETTINGS
# =========================================================
elif page == "Settings":
    page_header(
        "Settings",
        "Application configuration and AI workflow status.",
    )
    st.subheader("Implemented Components")
    st.markdown("""
    - PDF resume text extraction and preprocessing
    - Rule-based candidate scoring and ranking
    - Groq LLM connection
    - Dense semantic retrieval
    - BM25 sparse retrieval
    - Multi-query retrieval
    - LangGraph screening workflow
    - AI-generated candidate explanations
    - CSV and text report exports
    """)
    st.subheader("AI Workflow")
    st.markdown("""
    1. Job Analyzer — summarizes job requirements.
    2. Hybrid RAG Retriever — retrieves relevant resume evidence.
    3. Candidate Evaluator — generates scores and explanations.
    """)
    st.warning(
        "The workflow is an initial prototype. AI-generated scores are "
        "not validated predictions, and the current workflow does not "
        "yet implement separate strength, red-flag, ranking, or email agents."
    )
    st.subheader("Environment Variables")
    st.code(
        "GROQ_API_KEY=your_private_api_key\n"
        "GROQ_MODEL=your_configured_model_id",
        language="text",
    )
    st.caption(
        "Keep secrets in .env. Never commit API keys to Git. "
        "Uploaded PDF bytes remain in session state; job profiles and AI screening history are saved in SQLite."
    )
