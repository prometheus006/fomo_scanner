"""Gmail SMTP ile mail gönderimi. Kimlik bilgileri env değişkeninden gelir."""
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send(subject: str, text: str, html: str | None = None):
    address = os.environ["SMTP_USER"]
    app_password = os.environ["SMTP_PASS"]
    to_addr = os.environ.get("SMTP_TO") or address

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = address
    msg["To"] = to_addr
    msg.attach(MIMEText(text, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(address, app_password)
        server.send_message(msg)
