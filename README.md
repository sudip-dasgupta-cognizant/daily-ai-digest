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

**1. Clone and install**

```bash
git clone https://github.com/YOUR_USERNAME/daily-ai-digest.git
cd daily-ai-digest
pip install -r requirements.txt
```

**2. Run the setup wizard**

```bash
python setup.py
```

Select your role, enter email addresses. `config.json` is created locally.

**3. Add GitHub Secrets**

In your repo: **Settings → Secrets and variables → Actions → New repository secret**

| Secret name | Value |
|---|---|
| `GMAIL_USER` | Your Gmail address |
| `GMAIL_APP_PASSWORD` | 16-char Gmail App Password (see [docs/SETUP.md](docs/SETUP.md)) |

**4. Commit and push**

```bash
git add config.json
git commit -m "Add digest configuration"
git push
```

**5. Trigger or wait**

The digest runs automatically at 7:30 AM IST. For an immediate test:
**Actions → Daily AI Digest → Run workflow**

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
