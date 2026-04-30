# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Daily AI Digest fetches AI news from 9 RSS feeds, classifies each item as `deep-read`, `skim`, or `skip` using GitHub Models API (gpt-4o-mini), and emails a formatted HTML digest daily at 7:30 AM IST via GitHub Actions.

## Pipeline

```
fetch_news.py → news_items.json → classify.py → classified_items.json → send_email.py
```

All three scripts are run sequentially by `.github/workflows/daily_digest.yml`. Intermediate JSON files live in the repo root.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# One-time local setup (generates config.json)
python setup.py

# Run pipeline locally (requires env vars below)
export GITHUB_TOKEN=<github_pat>
export GMAIL_USER=<gmail_address>
export GMAIL_APP_PASSWORD=<16_char_app_password>

python src/fetch_news.py      # writes news_items.json
python src/classify.py        # reads news_items.json, writes classified_items.json
python src/send_email.py      # reads classified_items.json + config.json, sends email
```

## Key files

- `src/sources.py` — RSS feed list (edit here to add/remove sources)
- `src/classify.py` — `SYSTEM_PROMPTS` dict maps role name → classification prompt
- `src/send_email.py` — `HTML_TEMPLATE` string is the full Jinja2 email template
- `config.json` — role, sender email, recipient email (committed; no credentials)
- `.github/workflows/daily_digest.yml` — cron `"0 2 * * *"` = 2:00 AM UTC = 7:30 AM IST

## GitHub Models API

The OpenAI SDK is used with a custom base URL:
```python
OpenAI(base_url="https://models.inference.ai.azure.com", api_key=GITHUB_TOKEN)
```
`GITHUB_TOKEN` is auto-injected by GitHub Actions. No external API key or billing is required. Model: `gpt-4o-mini`.

## Roles

15 supported roles defined in both `setup.py` (menu) and `classify.py` (prompts). Role names must match exactly between the two files. To add a role: add to `ROLES` list in `setup.py` and add a corresponding key in `SYSTEM_PROMPTS` in `classify.py`.

## Config vs secrets

`config.json` (role, emails) is committed. `GMAIL_USER` and `GMAIL_APP_PASSWORD` are GitHub Secrets, never committed.
