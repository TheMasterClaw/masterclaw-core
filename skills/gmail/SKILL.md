---
name: gmail
description: Read and send Gmail using IMAP/SMTP with App Passwords. Use for checking emails, sending messages, and managing inbox.
---

# Gmail Skill

Access Gmail via IMAP/SMTP using App Passwords.

## Setup

1. Enable 2FA on your Google Account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Save credentials:
   ```bash
   echo "your-email@gmail.com" > ~/.openclaw/gmail-user
   echo "your-app-password" > ~/.openclaw/gmail-pass
   chmod 600 ~/.openclaw/gmail-*
   ```

## Usage

### Read unread emails
```bash
./skills/gmail/scripts/read.sh
```

### Send email
```bash
./skills/gmail/scripts/send.sh "to@example.com" "Subject" "Body text"
```

### Search emails
```bash
./skills/gmail/scripts/search.sh "from:boss@company.com"
```

## Requirements

- `python3` with `imaplib` and `smtplib` (built-in)
