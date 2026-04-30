# Customisation Guide

## Adding or Removing RSS Sources

Edit `src/sources.py`. The `RSS_FEEDS` list is the single source of truth:

```python
RSS_FEEDS = [
    "https://example.com/feed/",   # add new entries here
    # "https://remove-me.com/feed/",  # comment out to remove
]
```

Any valid RSS or Atom feed URL works. After editing, commit and push the change — the next workflow run picks it up automatically.

**Finding feed URLs**: Most blogs and news sites publish a feed at `/feed/`, `/rss/`, or `/atom.xml`. Look for the RSS icon on the site, or append `/feed` to the base URL.

**Volume note**: Each feed can return many items, but `fetch_news.py` caps the total at 40 items after deduplication. If you add many feeds, some lower-priority sources may get crowded out. Adjust `MAX_ITEMS` in `fetch_news.py` if needed.

---

## Changing the Cron Schedule

Edit `.github/workflows/daily_digest.yml`:

```yaml
on:
  schedule:
    - cron: "0 2 * * *"   # change this line
```

GitHub Actions cron uses UTC. Convert your desired local time to UTC:

| Local time | UTC equivalent | Cron expression |
|---|---|---|
| 7:30 AM IST | 2:00 AM UTC | `0 2 * * *` |
| 8:00 AM IST | 2:30 AM UTC | `30 2 * * *` |
| 9:00 AM IST | 3:30 AM UTC | `30 3 * * *` |
| 7:00 AM BST (summer) | 6:00 AM UTC | `0 6 * * *` |
| 8:00 AM EST | 1:00 PM UTC | `0 13 * * *` |

**Cron format**: `minute hour day-of-month month day-of-week`

To run Monday–Friday only: `0 2 * * 1-5`

---

## Modifying the Classification Prompt for a Role

Open `src/classify.py` and find the `SYSTEM_PROMPTS` dictionary. Each key is a role name (must match exactly what `setup.py` produces). Edit the string for the role you want to adjust:

```python
SYSTEM_PROMPTS = {
    "Software Developer": (
        "You are classifying AI news articles for a Software Developer..."
        "DEEP-READ: ..."   # edit these priority lists
        "SKIM: ..."
        "SKIP: ..."
    ),
    ...
}
```

**Prompt structure**: Each prompt has three sections — `DEEP-READ`, `SKIM`, and `SKIP` — listing the topics that qualify for each category. Be specific. Generic prompts produce generic results.

**Testing a prompt change**: Run `python src/classify.py` locally after running `python src/fetch_news.py` to see how the new prompt classifies today's items. Requires `GITHUB_TOKEN` set in your local environment:

```bash
export GITHUB_TOKEN=your_personal_access_token
python src/fetch_news.py
python src/classify.py
```

---

## Adding a New Role

**Step 1** — Add the role name to `setup.py`:

```python
ROLES = [
    ...
    "My New Role",   # add here
]
```

**Step 2** — Add a system prompt in `src/classify.py`:

```python
SYSTEM_PROMPTS = {
    ...
    "My New Role": (
        "You are classifying AI news articles for a [role description]. "
        "DEEP-READ: [list of high-priority topics for this role]. "
        "SKIM: [list of moderate-priority topics]. "
        "SKIP: [list of irrelevant topics]."
    ),
}
```

**Step 3** — Re-run `python setup.py` locally to update `config.json` with the new role, then commit and push.

---

## Changing the Email Template

The HTML template lives as a multi-line string (`HTML_TEMPLATE`) in `src/send_email.py`. It uses [Jinja2](https://jinja.palletsprojects.com/) syntax.

**Available template variables**:

| Variable | Type | Description |
|---|---|---|
| `role` | string | Role name from config.json |
| `date` | string | Formatted IST date, e.g. "Wednesday, 30 April 2026" |
| `deep_reads` | list of dict | Items with category == "deep-read" |
| `skims` | list of dict | Items with category == "skim" |

**Item dict fields**: `title`, `url`, `source`, `category`, `reason`, `summary`

**Email CSS note**: Email clients strip `<style>` blocks and external stylesheets. All CSS must be inline (`style="..."` attributes). Test your template by running `send_email.py` locally or by previewing the HTML in a browser.

**To extract the template to a separate file**: Replace the `HTML_TEMPLATE` string with a file read:

```python
TEMPLATE_FILE = os.path.join(os.path.dirname(__file__), "email_template.html")
with open(TEMPLATE_FILE, encoding="utf-8") as f:
    HTML_TEMPLATE = f.read()
```

Create `src/email_template.html` with your template content.

---

## Sending to Multiple Recipients

The current implementation sends to one recipient defined in `config.json`. To send to multiple:

**Option 1 — Comma-separated string in config.json**:

Update `config.json`:
```json
{
  "recipient_email": "alice@example.com,bob@example.com"
}
```

Update `send_email.py` to split the string:

```python
recipient = config.get("recipient_email", "")
recipient_list = [r.strip() for r in recipient.split(",") if r.strip()]

# In send_via_smtp, change:
msg["To"] = ", ".join(recipient_list)
server.sendmail(sender, recipient_list, msg.as_string())
```

**Option 2 — Multiple runs with different configs**: Create a matrix job in the GitHub Actions workflow, one per recipient, each with its own `config.json` (committed under different names, e.g. `config_alice.json`).

---

## Running Locally for Testing

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export GITHUB_TOKEN=your_personal_access_token
export GMAIL_USER=your@gmail.com
export GMAIL_APP_PASSWORD=your_app_password

# 3. Run the pipeline
python src/fetch_news.py       # produces news_items.json
python src/classify.py         # produces classified_items.json
python src/send_email.py       # sends the email
```

Intermediate JSON files (`news_items.json`, `classified_items.json`) are created in the repo root. Add them to `.gitignore` to avoid accidental commits:

```
news_items.json
classified_items.json
```
