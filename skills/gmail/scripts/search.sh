#!/usr/bin/env python3
import imaplib
import email
from email.header import decode_header
import os
import sys

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

def search_emails(query):
    user, password = get_creds()
    
    imap = imaplib.IMAP4_SSL("imap.gmail.com")
    imap.login(user, password)
    imap.select("INBOX")
    
    # Convert simple query to IMAP search
    if "from:" in query:
        search_term = query.replace("from:", "").strip()
        status, messages = imap.search(None, f'FROM "{search_term}"')
    elif "subject:" in query:
        search_term = query.replace("subject:", "").strip()
        status, messages = imap.search(None, f'SUBJECT "{search_term}"')
    else:
        status, messages = imap.search(None, f'TEXT "{query}"')
    
    if status != "OK" or not messages[0]:
        print(f"No emails found for: {query}")
        imap.logout()
        return
    
    msg_ids = messages[0].split()
    print(f"📧 {len(msg_ids)} email(s) found:\n")
    
    for msg_id in msg_ids[:10]:
        status, msg_data = imap.fetch(msg_id, "(RFC822)")
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                subject = decode_header(msg["Subject"])[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode()
                from_addr = msg.get("From", "Unknown")
                date = msg.get("Date", "Unknown")
                print(f"From: {from_addr}")
                print(f"Subject: {subject}")
                print(f"Date: {date}")
                print("-" * 40)
    
    imap.logout()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: search.sh \"query\"")
        print("Examples:")
        print('  search.sh "from:boss@company.com"')
        print('  search.sh "subject:invoice"')
        print('  search.sh "project alpha"')
        exit(1)
    
    search_emails(sys.argv[1])
