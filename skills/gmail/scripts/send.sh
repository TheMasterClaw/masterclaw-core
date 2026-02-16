#!/usr/bin/env python3
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def get_creds():
    user_file = os.path.expanduser("~/.openclaw/gmail-user")
    pass_file = os.path.expanduser("~/.openclaw/gmail-pass")
    
    if not os.path.exists(user_file) or not os.path.exists(pass_file):
        print("Error: Gmail credentials not found.")
        exit(1)
    
    with open(user_file) as f:
        user = f.read().strip()
    with open(pass_file) as f:
        password = f.read().strip()
    
    return user, password

def send_email(to_addr, subject, body):
    user, password = get_creds()
    
    msg = MIMEMultipart()
    msg["From"] = user
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(user, password)
    server.send_message(msg)
    server.quit()
    
    print(f"✅ Email sent to {to_addr}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: send.sh \"to@example.com\" \"Subject\" \"Body\"")
        exit(1)
    
    send_email(sys.argv[1], sys.argv[2], sys.argv[3])
