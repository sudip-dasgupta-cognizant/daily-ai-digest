# Architecture

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      GITHUB ACTIONS RUNNER                         │
│                    (ubuntu-latest, 2:00 AM UTC)                    │
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│  │fetch_news.py│───▶│ classify.py │───▶│send_email.py│            │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘            │
│         │                  │                   │                   │
│  news_items.json  classified_items.json   Gmail SMTP               │
│                                                                     │
│  ┌─────────────────────────────────────────────────────┐           │
│  │                   INPUTS                            │           │
│  │  config.json      → role, sender, recipient         │           │
│  │  GITHUB_TOKEN     → GitHub Models API auth          │           │
│  │  GMAIL_USER       → SMTP login                      │           │
│  │  GMAIL_APP_PASSWORD → SMTP password                 │           │
│  └─────────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────────┘

External services:
  9 × RSS feeds ──────────────────────────────▶ fetch_news.py
  models.inference.ai.azure.com ─────────────▶ classify.py
  smtp.gmail.com:587 ─────────────────────────▶ send_email.py
```

## Data Flow

```
RSS feeds (9 sources)
        │
        ▼ requests.get() + xml.etree.ElementTree (browser User-Agent)
Raw feed entries (unlimited)
        │
        ▼ filter: published within last 48 hours
        │  (if 0 items pass, automatically retry with 72-hour window)
        │  per-feed log: OK "Source Name": N/M items within 48h window
Dated entries
        │
        ▼ deduplicate: SequenceMatcher ratio ≥ 0.75 on titles
Unique entries
        │
        ▼ cap at 40 items
news_items.json  [title, url, description, source]
        │
        ▼ for each item: POST to GitHub Models API (gpt-4o-mini)
           system: role-specific prompt + JSON schema instruction
           user:   title + description
        │
        ▼ parse JSON response → category: deep-read | skim | skip
        ▼ filter out "skip" items
classified_items.json  [title, url, source, category, reason, summary]
        │
        ├─▶ deep_reads (category == "deep-read")
        └─▶ skims      (category == "skim")
                │
                ▼ Jinja2 HTML template render
        HTML email body
                │
                ▼ smtplib SMTP(host, 587) + STARTTLS + login
        Gmail → recipient inbox
```

## RSS Fetching

`fetch_news.py` uses `requests` for HTTP and Python's built-in `xml.etree.ElementTree` for parsing — no third-party feed library is required. Both RSS 2.0 and Atom feed formats are supported; the format is detected from the XML root element tag.

A browser-like User-Agent header is sent with every request to avoid bot-blocking by news site CDNs and WAFs:

```
Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36
```

The fetch window is 48 hours (`CUTOFF_HOURS` in `fetch_news.py`) to accommodate feeds that publish infrequently. If all feeds return 0 items after filtering, the script automatically retries with a 72-hour window (`FALLBACK_HOURS`) before writing an empty result. Each feed produces a log line showing how many items passed the window filter vs. the total available, making it straightforward to diagnose which feeds are blocked or empty in the Actions log.

## GitHub Models API Integration

The classifier uses the OpenAI Python SDK pointed at GitHub's model inference endpoint:

```python
from openai import OpenAI

client = OpenAI(
    base_url="https://models.inference.ai.azure.com",
    api_key=os.environ["GITHUB_TOKEN"],
)
```

`GITHUB_TOKEN` is automatically injected by GitHub Actions into every workflow run — no external API key or billing account is required. The model used is `gpt-4o-mini`, which provides strong reasoning at low cost and latency.

Each item is classified with a separate API call (temperature=0.2 for consistency). With 40 items and a 0.6-second inter-call delay, the classification step takes approximately 25–35 seconds.

**Rate limits**: GitHub Models API enforces rate limits per token. If you hit limits, increase `RATE_LIMIT_DELAY` in `classify.py` or reduce `MAX_ITEMS` in `fetch_news.py`.

## Configuration vs. Secrets Separation

| Location | Contents | Committed to repo? |
|---|---|---|
| `config.json` | Role, sender email, recipient email | Yes |
| GitHub Secrets | `GMAIL_USER`, `GMAIL_APP_PASSWORD` | Never |
| GitHub Actions | `GITHUB_TOKEN` | Auto-provided |

`config.json` contains no credentials — only preference data. It is safe to commit. Credentials live exclusively in GitHub Secrets and are injected as environment variables at runtime.

## Cron Schedule and Timezone

```
Cron expression: "0 2 * * *"

UTC:  02:00 AM  (GitHub Actions uses UTC)
IST:  07:30 AM  (UTC + 5:30)
```

GitHub Actions cron schedules run in UTC. There is no native IST option, so the offset is calculated manually: 7:30 AM IST = 2:00 AM UTC.

To change the schedule, edit the `cron:` line in `.github/workflows/daily_digest.yml`. Use the UTC equivalent of your desired local time. A UTC/local time converter is available at [worldtimeserver.com](https://www.worldtimeserver.com/convert_time_in_UTC.aspx).

## Email Delivery

Email is sent via Gmail's SMTP relay on port 587 using STARTTLS (opportunistic TLS — the connection upgrades from plaintext to encrypted before credentials are sent). A Gmail App Password is required because Google blocks less-secure app access by default.

The email is sent as `text/html` (MIME multipart alternative). The HTML uses inline CSS for broad email client compatibility.
