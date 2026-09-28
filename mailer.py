"""Gmail SMTP ile mail gönderimi. Kimlik bilgileri env değişkeninden gelir."""
import os
import smtplib
from email.mime.text import MIMEText


def send(subject: str, body: str):
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to_addr = os.environ.get("MAIL_TO", address)

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = to_addr

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.send_message(msg)
