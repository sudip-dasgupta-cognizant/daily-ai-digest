# Daily AI Digest

Automated daily email digest that fetches AI news from nine RSS feeds, classifies each item as **Deep Read** or **Skim** based on your professional role, and delivers a formatted HTML email every morning at 7:30 AM IST — powered by GitHub Models API (no external API key required).

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│  GitHub Actions  —  cron "0 2 * * *"  (2:00 AM UTC / 7:30 AM IST)│
└──────────────────────────────┬───────────────────────────────────┘
                               │
          ┌────────────────────▼──────────────────┐
          │           src/fetch_news.py           │
          │  Polls 9 RSS feeds · 24-hour window   │
          │  Deduplicates by title · cap 40 items │
          └────────────────────┬──────────────────┘
                               │  news_items.json
          ┌────────────────────▼──────────────────┐
          │           src/classify.py             │
          │  GitHub Models API  (gpt-4o-mini)     │
          │  Role-specific prompt per item        │
          │  Output: deep-read / skim / skip      │
          └────────────────────┬──────────────────┘
                               │  classified_items.json
          ┌────────────────────▼──────────────────┐
          │           src/send_email.py           │
          │  Jinja2 HTML template                 │
          │  Gmail SMTP port 587 · STARTTLS       │
          └───────────────────────────────────────┘

Config:   config.json          → role, sender/recipient emails
Secrets:  GitHub Secrets       → GMAIL_USER, GMAIL_APP_PASSWORD
Token:    GITHUB_TOKEN         → auto-provided by GitHub Actions
```

## Quickstart

> No terminal or local installation required. Everything runs on GitHub's servers.

**1. Get a Gmail App Password**

Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create an App Password named `AI Digest`, and copy the 16-character password shown.

**2. Fork this repository**

Click **Fork** at the top of this page. This creates your own copy under your GitHub account where your secrets and scheduled workflow run independently.

**3. Add four GitHub Secrets**

In your forked repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | The 16-character App Password from Step 1 |
| `DIGEST_ROLE` | Your role — e.g. `Architect`, `Software Developer`, `Delivery Manager` (see full list below) |
| `DIGEST_RECIPIENT` | Your work email address |

**4. Run your first digest**

**Actions → Daily AI Digest → Run workflow → Run workflow**

Wait 5 minutes and check your inbox. The digest will also run automatically every morning at 7:30 AM IST.

---

## Role-based Classification

Each news item is sent to `gpt-4o-mini` (via GitHub Models API) with a system prompt tailored to your role. The model assigns one of three categories:

| Category | Meaning |
|---|---|
| **Deep Read** | High relevance — full summary, reason, and link in the email |
| **Skim** | Worth knowing — headline and link only |
| **Skip** | Filtered out entirely — not included in the email |

Supported roles include Architect, Software Developer, Data/AI Analyst, DevOps/Platform Engineer, Security Engineer, QA/Test Engineer, Business Analyst, Product Manager, Scrum Master/Agile Coach, Engineering Manager, Delivery Manager, Practice Lead/CoE Lead, Senior Management/Executive, Pre-Sales/Solutions Consultant, and Account Manager.

Each role has a distinct prompt that specifies which topics warrant deep reading vs. skimming for that role's priorities and responsibilities.

---

## Detailed Guides

- [docs/SETUP.md](docs/SETUP.md) — Full step-by-step setup from scratch
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Component design and data flow
- [docs/CUSTOMISATION.md](docs/CUSTOMISATION.md) — Adding sources, roles, and changing schedules
