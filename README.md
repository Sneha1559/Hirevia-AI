\# Hirevia AI – Goal-Based Multi-Agent Resume Screening System



Hirevia AI is an AI-powered resume screening system that automates candidate evaluation by comparing resumes with job descriptions using a multi-agent architecture, Hybrid Retrieval-Augmented Generation (RAG), and a Large Language Model (LLM).



\## Key Features



\- \*\*Resume Upload:\*\* Upload and process candidate resumes in PDF format.

\- \*\*Job Description Analysis:\*\* Analyze job requirements and identify relevant skills.

\- \*\*Hybrid RAG:\*\* Combines dense retrieval, sparse BM25 retrieval, and multi-query retrieval to find relevant evidence from resumes.

\- \*\*Multi-Agent Screening:\*\* Uses specialized agents to evaluate candidates and generate screening results.

\- \*\*Candidate Scoring and Ranking:\*\* Scores candidates, ranks them, and generates recommendations based on a configurable threshold.

\- \*\*Strengths and Red Flags:\*\* Identifies relevant candidate strengths and potential gaps.

\- \*\*Explainable Results:\*\* Provides explanations to support screening decisions.

\- \*\*Email Notifications:\*\* Sends recruiter summaries and shortlist notifications to candidates.

\- \*\*Result Tracking:\*\* Stores screening results and email status using SQLite.



\## Technology Stack



| Component | Technologies |

|---|---|

| Programming Language | Python |

| User Interface | Streamlit |

| Agent Orchestration | LangGraph |

| LLM Integration | Groq API, Llama 3.3 |

| Retrieval | Dense Retrieval, BM25, Multi-Query Retrieval |

| Vector Search | FAISS |

| Embeddings | Sentence Transformers |

| Database | SQLite |

| Data Processing | Pandas, NumPy |



\## System Workflow



1\. The recruiter uploads resumes and a job description.

2\. The system extracts and preprocesses resume text.

3\. The job requirements and resume content are processed through Hybrid RAG.

4\. The LLM and multi-agent workflow evaluate candidate profiles.

5\. Candidates receive scores, rankings, recommendations, and explanations.

6\. The recruiter reviews results and can send shortlist notifications.

7\. Screening history and email statuses are stored in the database.



\## Project Structure



```text

Hirevia-AI/

├── agents/       # Specialized AI agents

├── core/         # Core screening workflow

├── models/       # Data models

├── rag/          # Hybrid RAG components

├── tests/        # Project tests

├── utils/        # Helper utilities and email notifications

├── app.py        # Streamlit application

├── .env.example  # Example environment configuration

├── .gitignore

└── README.md

```



\## Installation and Setup



\### 1. Clone the repository



```bash

git clone https://github.com/Sneha1559/Hirevia-AI.git

cd Hirevia-AI

```



\### 2. Create a virtual environment



```bash

python -m venv venv

```



Activate it on Windows:



```powershell

.\\venv\\Scripts\\activate

```



\### 3. Install dependencies



If a `requirements.txt` file is available:



```bash

pip install -r requirements.txt

```



\### 4. Configure environment variables



Create a `.env` file based on `.env.example` and add your own Groq API key and any required email configuration.



\*\*Never commit your `.env` file or API keys to GitHub.\*\*



\### 5. Run the application



```bash

python -m streamlit run app.py

```



\## Testing



Run the project's available tests with:



```bash

python -m pytest tests/

```



\## Security



\- Keep API keys and email credentials private.

\- Do not commit local databases or sensitive candidate information.

\- Use environment variables for secrets.



\## Project Information



\*\*Project:\*\* Hirevia AI  

\*\*Category:\*\* Artificial Intelligence, Natural Language Processing, Information Retrieval  

\*\*Purpose:\*\* Goal-based, explainable resume screening and candidate ranking



\---



\*Developed as a B.Tech final-year project.\*

