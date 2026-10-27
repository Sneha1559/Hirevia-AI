# Hirevia AI

### Goal-Based Multi-Agent Resume Screening System Using Hybrid RAG and LLM

Hirevia AI is an AI-powered resume screening system that evaluates candidate resumes against job descriptions using Hybrid Retrieval-Augmented Generation (RAG), a Large Language Model (LLM), and a multi-agent workflow.

The application helps recruiters review candidate profiles, compare relevant evidence, generate screening scores and recommendations, and notify shortlisted applicants.

---

## Key Features

- **Resume Parsing:** Extracts text from PDF resumes.
- **Job Description Analysis:** Identifies job requirements and relevant skills.
- **Hybrid RAG:** Combines dense retrieval, BM25 sparse retrieval, and multi-query retrieval.
- **Multi-Agent Screening:** Uses specialized agents to evaluate candidate profiles.
- **Candidate Scoring and Ranking:** Produces scores, rankings, and recommendations.
- **Strengths and Red Flags:** Highlights relevant strengths and potential skill gaps.
- **Explainable Results:** Provides explanations to support screening outcomes.
- **Configurable Threshold:** Allows recruiters to set a screening threshold.
- **Email Notifications:** Supports recruiter summaries and shortlist notifications.
- **Result Tracking:** Stores screening information and email status using SQLite.

## System Workflow

```text
Recruiter uploads resumes and job description
                    |
                    v
          Resume preprocessing
                    |
                    v
       Hybrid RAG: Dense + BM25
             + Multi-Query
                    |
                    v
         Multi-agent screening
                    |
                    v
           LLM-based analysis
                    |
                    v
           Scoring and ranking
                    |
                    v
       Results and email notifications
```

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| User Interface | Streamlit |
| Agent Orchestration | LangGraph |
| LLM Provider | Groq API |
| Language Model | Llama 3.3 |
| Dense Retrieval | Sentence Transformers |
| Sparse Retrieval | BM25 |
| Vector Search | FAISS |
| Database | SQLite |
| Data Processing | Pandas, NumPy |
| Testing | Pytest |

## Hybrid RAG

Hirevia AI uses three retrieval approaches to find relevant evidence for candidate evaluation:

1. **Dense Retrieval:** Finds semantically relevant content using embeddings.
2. **Sparse Retrieval (BM25):** Retrieves content based on keyword relevance.
3. **Multi-Query Retrieval:** Uses alternative queries to find additional relevant evidence.

Retrieved evidence is combined and supplied as context to the LLM to support candidate analysis and explanations.

## Project Structure

```text
Hirevia-AI/
├── agents/          # Specialized AI agents
├── core/            # Core screening workflow
├── models/          # Data models
├── rag/             # Hybrid RAG components
├── tests/           # Automated tests
├── utils/           # Utility and email functions
├── app.py           # Streamlit application
├── .env.example     # Example environment configuration
├── .gitignore       # Git exclusions
└── README.md        # Project documentation
```

## Installation and Setup

### Prerequisites

- Python 3.11 recommended
- Git
- A Groq API key

### 1. Clone the repository

```bash
git clone https://github.com/Sneha1559/Hirevia-AI.git
cd Hirevia-AI
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it in Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

If the repository contains a `requirements.txt` file:

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file using `.env.example` as a reference. Add your Groq API key and any other settings required by your code.

```env
GROQ_API_KEY=your_groq_api_key
```

Use the exact variable names expected by your application. Never commit real API keys, passwords, or email credentials.

### 5. Run the application

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

## Testing

If Pytest is configured in the project, run:

```bash
python -m pytest tests/
```

## Security and Privacy

- Keep API keys and credentials in environment variables.
- Do not commit `.env` files or private configuration.
- Avoid uploading databases containing personal candidate information.
- Review AI-generated recommendations before making recruitment decisions.

## Future Enhancements

- Improve retrieval relevance evaluation.
- Expand candidate comparison and screening analytics.
- Enhance screening history and audit trails.
- Integrate with additional recruitment platforms.
- Strengthen privacy and access controls.

## Project Information

- **Project Name:** Hirevia AI
- **Project Type:** B.Tech Final-Year Project
- **Domain:** Artificial Intelligence, Natural Language Processing, and Information Retrieval
- **Repository:** [Sneha1559/Hirevia-AI](https://github.com/Sneha1559/Hirevia-AI)

---

*Hirevia AI — Making resume screening smarter, faster, and more explainable.*
