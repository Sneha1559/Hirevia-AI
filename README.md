\# Hirevia AI



**Goal-Based Multi-Agent Resume Screening System Using Hybrid RAG and LLM**



Hirevia AI is an AI-powered resume screening system that automates candidate evaluation by matching resumes with job descriptions using Hybrid Retrieval-Augmented Generation (RAG), Large Language Models (LLMs), and a multi-agent architecture.



The system helps recruiters analyze candidate profiles, generate screening scores, rank applicants, understand candidate strengths and potential gaps, and notify shortlisted candidates.





\## Key Features



\- Resume Parsing:\*\* Extract text from PDF resumes.

\- Job Description Analysis:\*\* Identify required skills and qualifications.

\- Hybrid RAG:\*\* Combine dense retrieval, BM25 sparse retrieval, and multi-query retrieval.

\- Multi-Agent Screening:\*\* Analyze candidate profiles through specialized AI agents.

\- Candidate Scoring:\*\* Generate candidate evaluation scores.

\- Candidate Ranking:\*\* Rank candidates based on screening results.

\- Strengths and Red Flags:\*\* Highlight relevant strengths and potential skill gaps.

\- Explainable Results:\*\* Generate explanations and recommendations.

\- Configurable Threshold:\*\* Set a minimum screening score.

\- Email Notifications:\*\* Send recruiter summaries and shortlisted-candidate emails.

\- Result Tracking:\*\* Store screening information and email status using SQLite.



\## System Workflow



Recruiter Uploads Resumes and Job Description

&#x20;                   |

&#x20;                   v

&#x20;          Resume Preprocessing

&#x20;                   |

&#x20;                   v

&#x20;            Hybrid RAG

&#x20;      Dense + BM25 + Multi-Query

&#x20;                   |

&#x20;                   v

&#x20;         Multi-Agent Screening

&#x20;                   |

&#x20;                   v

&#x20;         LLM-Based Evaluation

&#x20;                   |

&#x20;                   v

&#x20;         Scoring and Ranking

&#x20;                   |

&#x20;                   v

&#x20;      Candidate Results and Reports

&#x20;                   |

&#x20;                   v

&#x20;           Email Notifications



\## Technology Stack



| Component - Technology 

| Programming Language - Python 

| User Interface - Streamlit 

| Agent Orchestration - LangGraph 

| LLM Provider - Groq API 

| Language Model - Llama 3.3 

| Dense Retrieval - Sentence Transformers 

| Sparse Retrieval - BM25 

| Vector Search - FAISS 

| Database - SQLite 

| Data Processing - Pandas, NumPy 

| Testing - Pytest 



\## Hybrid RAG



Hirevia AI uses three retrieval methods to find relevant information for candidate evaluation.



1\. Dense Retrieval:\*\* Finds semantically relevant resume content using embeddings.

2\. Sparse Retrieval (BM25):\*\* Retrieves content based on keyword relevance.

3\. Multi-Query Retrieval:\*\* Uses alternative queries to find additional relevant information.



The retrieved evidence is combined and provided as context to the LLM, supporting candidate analysis and explainable screening results.



\## Project Structure



Hirevia-AI/

|

|-- agents/       # Specialized AI agents

|-- core/         # Core screening workflow

|-- models/       # Data models

|-- rag/          # Hybrid RAG implementation

|-- tests/        # Automated tests

|-- utils/        # Utility and email functions

|

|-- app.py        # Streamlit application

|-- .env.example  # Example environment variables

|-- .gitignore    # Git exclusions

|-- README.md     # Project documentation





\## Installation and Setup



\### 1. Clone the Repository



git clone https://github.com/Sneha1559/Hirevia-AI.git

cd Hirevia-AI





\### 2. Create a Virtual Environment



python -m venv venv





Activate the environment on Windows PowerShell: .\\venv\\Scripts\\Activate.ps1





\### 3. Install Dependencies



If the repository contains a `requirements.txt` file, run: pip install -r requirements.txt





\### 4. Configure Environment Variables



Create a `.env` file using `.env.example` as a reference. Add your Groq API key and any other configuration required by your application.



GROQ\_API\_KEY=your\_groq\_api\_key





Use the exact variable names expected by your code. Never upload real API keys or email credentials to GitHub.



\### 5. Run the Application



python -m streamlit run app.py





Open the local URL displayed in the terminal to access the application.



\## Testing



If Pytest is configured in the project, run: python -m pytest tests/





\## Security and Privacy



\- Keep API keys and credentials in environment variables.

\- Do not commit `.env` files or private configuration.

\- Avoid uploading databases containing personal candidate information.

\- Review AI-generated screening recommendations before making recruitment decisions.



\## Future Enhancements



\- Improve retrieval relevance evaluation.

\- Expand candidate comparison and screening analytics.

\- Enhance screening history and audit trails.

\- Integrate with additional recruitment platforms.

\- Strengthen privacy and access controls.



\## Project Information



Project Name: Hirevia AI  

Project Type: B.Tech Final-Year Project  

Domain:Artificial Intelligence, Natural Language Processing, Information Retrieval



GitHub Repository: https://github.com/Sneha1559/Hirevia-AI



**"Hirevia AI — Making resume screening smarter, faster, and more explainable."**

