#!/usr/bin/env python3
"""
Daily AI Digest – one-time setup wizard.

Run this locally once to create config.json, then commit it to your repository.
Gmail credentials are never written to config.json — they go in GitHub Secrets.
"""
import json
import os
import sys

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

ROLES = [
    "Architect",
    "Software Developer",
    "Data / AI Analyst",
    "DevOps / Platform Engineer",
    "Security Engineer",
    "QA / Test Engineer",
    "Business Analyst",
    "Product Manager",
    "Scrum Master / Agile Coach",
    "Engineering Manager",
    "Delivery Manager",
    "Practice Lead / CoE Lead",
    "Senior Management / Executive",
    "Pre-Sales / Solutions Consultant",
    "Account Manager",
]


def prompt_email(label: str) -> str:
    while True:
        value = input(f"{label}: ").strip()
        if "@" in value and "." in value.split("@")[-1]:
            return value
        print("  Invalid address — please try again.")


def prompt_role() -> str:
    print("\nSelect your role:")
    print("-" * 40)
    for i, role in enumerate(ROLES, 1):
        print(f"  {i:>2}. {role}")
    print("-" * 40)
    while True:
        try:
            choice = int(input(f"Enter role number (1-{len(ROLES)}): ").strip())
            if 1 <= choice <= len(ROLES):
                return ROLES[choice - 1]
        except ValueError:
            pass
        print(f"  Please enter a number between 1 and {len(ROLES)}.")


def main() -> None:
    print()
    print("=" * 60)
    print("  Daily AI Digest  –  Setup Wizard")
    print("=" * 60)
    print(
        "\nThis wizard creates config.json with your digest settings.\n"
        "Your Gmail password is NOT stored here — it goes in GitHub Secrets.\n"
    )

    sender_email = prompt_email("Sender Gmail address (the account that sends the digest)")
    recipient_email = prompt_email("Recipient email address (where the digest is delivered)")
    role = prompt_role()

    config = {
        "role": role,
        "sender_email": sender_email,
        "recipient_email": recipient_email,
    }

    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

    print()
    print("=" * 60)
    print("  Configuration saved to config.json")
    print("=" * 60)
    print(f"  Role      : {role}")
    print(f"  Sender    : {sender_email}")
    print(f"  Recipient : {recipient_email}")

    print("""
======================================================================
  NEXT STEPS — Add GitHub Secrets
======================================================================

Your Gmail credentials must be stored as GitHub repository secrets
so GitHub Actions can send emails on your behalf.

  1. Open your repository on GitHub.
  2. Go to  Settings → Secrets and variables → Actions.
  3. Click "New repository secret" and add:

       Name  : GMAIL_USER
       Value : {sender}

  4. Click "New repository secret" again and add:

       Name  : GMAIL_APP_PASSWORD
       Value : <your 16-character Gmail App Password>

  HOW TO GET A GMAIL APP PASSWORD:
  ─────────────────────────────────
  a. Sign in to your Google account and visit:
       https://myaccount.google.com/security
  b. Enable "2-Step Verification" if not already on.
  c. Visit:  https://myaccount.google.com/apppasswords
  d. Choose app "Mail" and device "Other (custom name)".
  e. Copy the 16-character password shown — paste it as
     the GMAIL_APP_PASSWORD secret value.

  5. Commit and push config.json to your repository:

       git add config.json
       git commit -m "Add digest configuration"
       git push

  6. The digest runs automatically at 7:30 AM IST every day.
     To trigger it now for testing:
       GitHub → Actions → Daily AI Digest → Run workflow

======================================================================
""".format(sender=sender_email))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(0)
