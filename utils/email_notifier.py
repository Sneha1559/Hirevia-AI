import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()


def send_screening_email(recipient_email, job_title, threshold, candidates):
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_APP_PASSWORD")

    if not sender or not password:
        return False, "SMTP credentials missing in .env"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"Hirevia AI Screening Report - {job_title}"
        msg["From"] = sender
        msg["To"] = recipient_email

        lines = [
            "Hirevia AI - Resume Screening Report",
            f"Job: {job_title}",
            f"Threshold: {threshold}%",
            "",
            "Candidate Results:",
            "",
        ]

        for i, candidate in enumerate(candidates, 1):
            name = candidate.get("candidate_name", candidate.get("name", f"Candidate {i}"))
            score = candidate.get("score", candidate.get("match_score", "N/A"))
            recommendation = candidate.get("recommendation", "Not specified")

            lines.extend([
                f"{i}. {name}",
                f"Score: {score}",
                f"Recommendation: {recommendation}",
                "",
            ])

        msg.set_content("\n".join(lines))

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        return True, f"Email sent to {recipient_email}"

    except Exception as e:
        return False, f"Email failed: {type(e).__name__}"


import re


def send_candidate_shortlist_email(recipient_email, candidate_name, job_title):
    sender = os.getenv("SMTP_EMAIL")
    password = os.getenv("SMTP_APP_PASSWORD")

    if not sender or not password:
        return False, "SMTP credentials missing in .env"

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", recipient_email or ""):
        return False, "Invalid recipient email address"

    try:
        msg = EmailMessage()
        msg["Subject"] = f"Application Update - {job_title}"
        msg["From"] = sender
        msg["To"] = recipient_email

        msg.set_content(
            f"""Hello {candidate_name},

Thank you for your interest in the {job_title} position.

Congratulations! 🎉

We are pleased to inform you that your application has been shortlisted for further consideration.

Further details regarding the next steps in the recruitment process will be communicated to you shortly.
Congratulations once again, and we wish you all the very best for the upcoming stages!

Best regards,
Recruitment Team
Hirevia AI
"""
        )

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)

        return True, "Email accepted by SMTP server"

    except Exception as error:
        return False, f"Email failed: {type(error).__name__}"
