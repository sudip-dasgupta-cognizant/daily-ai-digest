# Setup Guide

This guide walks through setting up Daily AI Digest from scratch — from creating a GitHub account to receiving your first email.

---

## Prerequisites

- A GitHub account ([github.com/signup](https://github.com/signup))
- A Gmail account (existing or new — using a dedicated sending account is recommended)
- Python 3.11 or later ([python.org/downloads](https://www.python.org/downloads/))
- Git ([git-scm.com/downloads](https://git-scm.com/downloads))

---

## Step 1 — Create the GitHub Repository

**Option A: Fork or clone from GitHub**

If this project is already on GitHub:
```bash
git clone https://github.com/YOUR_USERNAME/daily-ai-digest.git
cd daily-ai-digest
```

**Option B: Create a new repository**

1. Go to [github.com/new](https://github.com/new)
2. Name it `daily-ai-digest`
3. Set visibility to **Private** (recommended)
4. Do not initialise with README, .gitignore, or licence
5. Click **Create repository**

Then initialise locally:
```bash
mkdir daily-ai-digest
cd daily-ai-digest
git init
git remote add origin https://github.com/YOUR_USERNAME/daily-ai-digest.git
```

Copy all project files into this directory, then:
```bash
git add .
git commit -m "Initial project files"
git push -u origin main
```

---

## Step 2 — Install Python Dependencies

From the project root directory:

```bash
pip install -r requirements.txt
```

This installs: `feedparser`, `openai`, `requests`, `jinja2`.

If you use a virtual environment (recommended):
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Step 3 — Run the Setup Wizard to Identify Your Values

```bash
python setup.py
```

The wizard asks for your sender Gmail address, recipient email address, and role (chosen from a numbered menu of 15 options). It writes these to `config.json` locally so you can see the exact values — **this file is for your reference only**.

`config.json` is blocked from being committed by `.gitignore`. Do not add or force-commit it. The workflow generates `config.json` at runtime from GitHub Secrets — no one, including the repo owner, should ever commit it.

Note the three values the wizard shows you — you will enter them as GitHub Secrets in Step 5:

| Wizard output field | GitHub Secret name |
|---|---|
| Role | `DIGEST_ROLE` |
| Sender Gmail address | `GMAIL_USER` |
| Recipient email address | `DIGEST_RECIPIENT` |

---

## Step 4 — Generate a Gmail App Password

Gmail requires an **App Password** for SMTP access when 2-Step Verification is enabled. You cannot use your regular Gmail password here.

1. Sign in to the Gmail account that will send the digest
2. Visit [myaccount.google.com/security](https://myaccount.google.com/security)
3. Under "How you sign in to Google", click **2-Step Verification** and enable it if not already on
4. After enabling 2SV, visit [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
5. In the "App name" field, type `Daily AI Digest` and click **Create**
6. Google shows a **16-character password** (e.g. `abcd efgh ijkl mnop` — spaces are for display only, remove them)
7. Copy this password immediately — it is only shown once

---

## Step 5 — Add GitHub Secrets

This step applies to **everyone** — both the original repo owner and anyone who forks the repo. Each person adds secrets to their own repository or fork. All configuration lives in secrets; nothing personal is ever committed to the code.

1. Go to your repository (or fork) on GitHub
2. Click **Settings** (top navigation bar, not account settings)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Add each of the following four secrets using **New repository secret**:

   ```
   Name:  GMAIL_USER
   Value: mydigest@gmail.com        ← the Gmail account that sends the digest
   ```

   ```
   Name:  GMAIL_APP_PASSWORD
   Value: abcdefghijklmnop          ← the 16-character App Password (no spaces)
   ```

   ```
   Name:  DIGEST_ROLE
   Value: Software Developer        ← your role, exactly as shown in setup.py
   ```

   ```
   Name:  DIGEST_RECIPIENT
   Value: me@company.com            ← where the digest is delivered
   ```

5. After adding all four, your secrets list should show: `DIGEST_RECIPIENT`, `DIGEST_ROLE`, `GMAIL_APP_PASSWORD`, `GMAIL_USER`.

The `GITHUB_TOKEN` secret is automatically provided by GitHub Actions — you do not need to add it.

---

## Step 6 — Confirm config.json Is Not Tracked

`config.json` is listed in `.gitignore` and must never be committed. The workflow generates it at runtime from your GitHub Secrets. Verify it is excluded:

```bash
git status
```

`config.json` should not appear in the output. If it does, your `.gitignore` is missing or not being applied — do not stage or commit it.

---

## Step 7 — Enable GitHub Actions

GitHub Actions is enabled by default for new repositories. Verify it is active:

1. Go to your repository on GitHub
2. Click the **Actions** tab
3. If you see a banner asking to enable workflows, click **I understand my workflows, go ahead and enable them**

---

## Step 8 — Trigger a Test Run

The digest runs automatically at 7:30 AM IST every day. To test it immediately:

1. Go to **Actions** tab in your repository
2. In the left sidebar, click **Daily AI Digest**
3. Click the **Run workflow** dropdown on the right
4. Select branch `main` and click **Run workflow**

The workflow takes approximately 60–90 seconds. Click the running job to watch the live logs.

---

## Step 9 — Verify Email Delivery

Check the recipient inbox for an email with subject:
```
AI Digest – Wednesday, 30 April 2026 | Software Developer
```

If the email does not arrive:
- Check your spam/junk folder
- Check the Actions workflow logs for errors (see Troubleshooting below)

---

## Troubleshooting

### HTTP 403 error when running pip install

**Error**: HTTP 403 or download blocked during `pip install -r requirements.txt`

**Cause**: Some corporate networks block the `sgmllib3k` package (a dependency pulled in by `feedparser`).

**Fix**: Install dependencies in two steps, skipping `sgmllib3k`:

```bash
pip install feedparser --no-deps
pip install openai jinja2 requests
```

This only affects local setup on corporate networks. GitHub Actions runs on GitHub-hosted runners and is unaffected.

---

### ModuleNotFoundError: No module named 'sgmllib'

**Error**: `ModuleNotFoundError: No module named 'sgmllib'` when running `fetch_news.py`

**Cause**: `feedparser` 6.x requires `sgmllib3k`, which may be blocked on corporate networks.

**Fix**: This has already been resolved in the codebase — `fetch_news.py` now uses `requests` and Python's built-in `xml.etree.ElementTree` instead of `feedparser`. If you see this error, ensure you are on the latest version of the repo:

```bash
git pull origin main
```

Then reinstall dependencies:

```bash
pip install openai jinja2 requests
```

No `feedparser` installation is needed.

---

### Gmail App Password issues

**Error**: `SMTPAuthenticationError: 535 Authentication Failed`

- Confirm 2-Step Verification is enabled on the sending Gmail account
- Regenerate the App Password at [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and update the `GMAIL_APP_PASSWORD` secret
- Ensure the secret value contains no spaces or newlines
- Make sure `GMAIL_USER` matches the account that generated the App Password

### Email going to spam

- Ask the recipient to mark the email as "Not spam" and add the sender to contacts
- Using a sending address with a reputation (your main Gmail rather than a new account) helps
- The `CAUTION` banner in the email is intentional and should not affect deliverability

### GitHub Actions workflow not running

- Confirm the workflow file is at `.github/workflows/daily_digest.yml` (check capitalisation)
- Confirm the file was pushed to the `main` branch
- GitHub occasionally delays cron jobs by up to 30 minutes — check the Actions tab for pending runs
- Check that Actions is enabled for the repository (Step 7)

### classify.py errors: rate limits

**Error**: `RateLimitError` or HTTP 429

- The GitHub Models API has per-token rate limits. Increase `RATE_LIMIT_DELAY` in `src/classify.py` (default: 0.6 seconds)
- Reduce `MAX_ITEMS` in `src/fetch_news.py` to classify fewer articles per run (default: 40)

### Email arrives but says "No relevant AI news found today"

**Cause**: RSS feeds returned 0 items after filtering. This can happen if all feeds are unreachable or if no items were published within the fetch window.

**Fix**: Open the GitHub Actions run log and look for the per-feed lines emitted by `fetch_news.py`:

```
[fetch]   OK    "VentureBeat": 3/18 items within 48h window
[fetch]   FAIL  https://example.com/feed  (HTTP error or XML parse error)
```

- Feeds showing `FAIL` are unreachable — check whether the URL is still valid in `src/sources.py`
- Feeds showing `0/N items` fetched successfully but all items fell outside the time window — this is normal for infrequently publishing sources
- The system automatically retries with a 72-hour window if the primary 48-hour pass returns zero items; if the fallback also returns zero, the email is sent with the empty-state message

---

### No items fetched (news_items.json is empty)

- RSS feeds occasionally go down or change their URLs. Check the Actions log for `[fetch] Error parsing` lines
- Verify the feed URLs in `src/sources.py` are still valid by opening them in a browser
- Some feeds may not publish new items every day — this is normal

### classify.py errors: JSON parse failure

**Error**: `JSON parse error for '...'`

- This happens when `gpt-4o-mini` wraps its output in markdown code fences. The parser handles this automatically in most cases. If it persists, check the `extract_json` function in `classify.py`

### config.json not found

`config.json` is generated at runtime by the **Generate config.json** step in the workflow, using the `DIGEST_ROLE`, `GMAIL_USER`, and `DIGEST_RECIPIENT` secrets. It is never committed to the repository.

- **In GitHub Actions**: if this error appears, confirm all four secrets are set correctly in **Settings → Secrets and variables → Actions**
- **Locally**: run `python setup.py` to create `config.json` for local testing — the file is gitignored and will not be committed

### 401 Unauthorized in classify step — "The models permission is required"

**Cause**: The GitHub Actions workflow needs explicit permission to call the GitHub Models API.

**Fix**: Ensure `.github/workflows/daily_digest.yml` contains this top-level `permissions` block:

```yaml
permissions:
  contents: read
  models: read
```

This is already included in the latest version of the repo. If you see this error, pull the latest changes and the permission will be present:

```bash
git pull origin main
```

---

### GITHUB_TOKEN has no access to GitHub Models

Ensure the repository is owned by a GitHub account with access to GitHub Models (available to most GitHub users as of 2024). If you see `AuthenticationError`, confirm the workflow's `permissions` block includes both `contents: read` and `models: read`.
