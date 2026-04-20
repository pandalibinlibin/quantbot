"""Test SMTP connection directly"""

import smtplib
import os

# Clear proxy environment variables for SMTP
for key in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]:
    os.environ.pop(key, None)
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Get settings from environment
smtp_host = os.getenv("SMTP_HOST", "smtp.qq.com")
smtp_port = int(os.getenv("SMTP_PORT", "465"))
smtp_user = os.getenv("SMTP_USER", "")
smtp_password = os.getenv("SMTP_PASSWORD", "")
smtp_ssl = os.getenv("SMTP_SSL", "True").lower() == "true"
from_email = os.getenv("EMAILS_FROM_EMAIL", smtp_user)
to_email = "23249735@qq.com"

print(f"SMTP Host: {smtp_host}")
print(f"SMTP Port: {smtp_port}")
print(f"SMTP User: {smtp_user}")
print(f"SMTP SSL: {smtp_ssl}")
print(f"From: {from_email}")
print(f"To: {to_email}")
print()

# Create message
msg = MIMEMultipart()
msg["From"] = from_email
msg["To"] = to_email
msg["Subject"] = "QuantBot Test Email"
body = "<h2>Test Email</h2><p>This is a test email from QuantBot.</p>"
msg.attach(MIMEText(body, "html"))

try:
    print("Connecting to SMTP server...")
    if smtp_ssl:
        # Use SSL (port 465)
        server = smtplib.SMTP_SSL(smtp_host, smtp_port)
    else:
        # Use TLS (port 587)
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()

    print("Connected. Logging in...")
    server.login(smtp_user, smtp_password)

    print("Logged in. Sending email...")
    server.sendmail(from_email, to_email, msg.as_string())

    print("Email sent successfully!")
    server.quit()

except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
