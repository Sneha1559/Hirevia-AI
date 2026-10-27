import os
from dotenv import load_dotenv
from utils.email_notifier import send_screening_email

load_dotenv()

success, message = send_screening_email(
    recipient_email=os.getenv("RECRUITER_EMAIL"),
    job_title="Data Science Intern",
    threshold=60,
    candidates=[
        {
            "candidate_name": "Test Candidate",
            "score": 85,
            "recommendation": "Shortlist",
        }
    ],
)

print(message)