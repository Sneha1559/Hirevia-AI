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