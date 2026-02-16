#!/usr/bin/env python3
import imaplib
import email
from email.header import decode_header
import os

def get_creds():
    user_file = os.path.expanduser("~/.openclaw/gmail-user")
    pass_file = os.path.expanduser("~/.openclaw/gmail-pass")
    
    if not os.path.exists(user_file) or not os.path.exists(pass_file):
        print("Error: Gmail credentials not found.")
        print("Run: echo 'your-email@gmail.com' > ~/.openclaw/gmail-user")
        print("     echo 'your-app-password' > ~/.openclaw/gmail-pass")
        exit(1)
    
    with open(user_file) as f:
        user = f.read().strip()
    with open(pass_file) as f:
        password = f.read().strip()
    
    return user, password

def read_unread():
    user, password = get_creds()
    
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user, password)
    imap.select("INBOX")
    
    status, messages = imap.search(None, "UNSEEN")
    if status != "OK" or not messages[0]:
        print("No unread emails.")
        imap.logout()
        return
    
    msg_ids = messages[0].split()
    print(f"📧 {len(msg_ids)} unread email(s):\n")
    
    for msg_id in msg_ids[:10]:  # Limit to 10
        status, msg_data = imap.fetch(msg_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                from_addr = msg.get("From", "Unknown")
                print(f"From: {from_addr}")
                print(f"Subject: {subject}")
                print("-" * 40)
    
    imap.logout()

if __name__ == "__main__":
    read_unread()
