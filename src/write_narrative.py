"""
write_narrative.py — generates the daily Substack post in Sudip's voice.

Reads classified_items.json and produces:
  - narrative.json         → {title, subtitle, body_markdown} for the Substack draft
  - narrative_for_tts.txt  → cleaned plain text for the TTS / podcast pipeline
"""
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass  # No corporate SSL inspection (e.g. GitHub Actions runner)


import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

try:
    from openai import OpenAI
except ImportError:
    print("[narrative] ERROR: openai not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_FILE = os.path.join(REPO_ROOT, "classified_items.json")
OUTPUT_FILE_JSON = os.path.join(REPO_ROOT, "narrative.json")
OUTPUT_FILE_TTS = os.path.join(REPO_ROOT, "narrative_for_tts.txt")

# Voice fidelity needs a smarter model. If you hit GitHub Models rate limits,
# fall back to "gpt-4o-mini" — but the voice will get noticeably more generic.
WRITE_MODEL = "gpt-4o"
IST = timezone(timedelta(hours=5, minutes=30))


# ---------------------------------------------------------------------------
# Voice system prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You write the daily AI news post for the "Soup for Soul" Substack, in the voice of Sudip Dasgupta — a Chief Architect from Kolkata who explains AI to "normal humans who hate mathematics".

# THE VOICE — non-negotiable

Sudip's writing has these traits. Mirror them closely:

- **Conversational Indian English** with light cultural texture: cricket, Bollywood, family weddings, aunties/uncles, Diwali sales, autos, chai, samosas, golgappas, biryani, "jugaad". Use these ONLY when they fit naturally — never forced, never piled up. Maximum ONE cultural reference per story section.
- **Self-deprecating, hype-skeptical humor**. Roast vendors, roast Twitter AI bros, roast yourself for taking the bait. Never roast the reader.
- **Plain-language demystification**. When something needs explaining, use a relatable analogy — like Sudip's "hyperparameter tuning is chai without sugar" line.
- **Sentence rhythm**: short punchy sentences mixed with longer ones. Lots of em-dashes. Occasional parenthetical asides. Italics for emphasis.
- **Emoji used sparingly for punctuation**, not decoration. ONE emoji per section header. Almost none in body prose.
- **Smart but not pompous**. Quote a real number or benchmark when you have it. Never to flex — always to anchor a point.

# VOICE ANCHORS — paragraphs from Sudip's actual writing

Mirror the rhythm, register, and humor of these. Do NOT copy the topics — they're just voice samples.

Anchor 1 (frustration with overcomplicated AI teaching):
"When I first started with ML, people started attacking me with big scary words: linear algebra, calculus, probability — basically the stuff that gives nightmares before every math exam. It felt like those tuition teachers who hand you a 10-page calculus derivative and say, 'Son, finish this first, then we'll practice 2 + 2.' I mean, come on, I just wanted to teach a computer how to be smart, not prepare for engineering entrance exams all over again."

Anchor 2 (analogies for technical concepts):
"Hyperparameter Tuning — this is when you've picked your favorite model, but it's still like chai without sugar — needs adjustment. GridSearchCV = 'let's try all combinations,' like an aunty trying on every saree before picking one. RandomizedSearchCV = 'let's try some random combos,' like dad randomly pressing TV remote buttons until cricket finally shows up."

Anchor 3 (the bottom-line voice):
"Bottom line: supervised learning is how robots stop embarrassing themselves — and you."

# THE STRUCTURE — daily news post

Output JSON with exactly these three keys:

{
  "title": "Your Daily AI News: <30-45 char curiosity hook, lowercase after colon>",
  "subtitle": "<one line, 80-120 chars, in Sudip's voice>",
  "body_markdown": "<the post body in Markdown>"
}

The body_markdown must follow THIS structure exactly:

---OPENING---
1 paragraph, 80-120 words. Start with a vivid scene, observation, or hype-roast. Set up the day's main thread. NO emoji in this paragraph.

---SECTION: "## 🔥 Today's Big Stories"---
For each deep-read story (3-5 of them), a subsection:

### {Sudip-voice headline — NOT the original article title, your reworded version}

2-3 paragraphs covering: what concretely happened (with the exact numbers/names from the source), one Sudip-voice analogy or aside, and the "so what" for the reader. ~150 words per story.

End each subsection with: **Source:** [{source}]({url})

---SECTION: "## 📰 Worth Knowing" (if there are skims)---
A bulleted list — one item per skim, one sentence each, in voice. Format:
- **{source}**: {one-sentence take in voice} — [link]({url})

Max 5 bullets. If there are more skims, pick the 5 most interesting and drop the rest.

---SECTION: "## 🧠 Bottom Line"---
ONE italic paragraph, 50-80 words. Synthesis: what does the day add up to? End with a sharp one-liner.

---FOOTER---
*Subscribe to my YouTube channel: [https://www.youtube.com/@sudipdasgupta](https://www.youtube.com/@sudipdasgupta)*

*🎧 Prefer to listen? The audio version is embedded above.*

# HARD RULES

- Total body length: 800-1200 words.
- ZERO clickbait phrases: "game-changer", "groundbreaking", "could revolutionize", "the future of", "watershed moment", "paradigm shift", "this changes everything".
- ZERO LLM giveaway phrases: "in today's fast-moving AI landscape", "buckle up", "let's dive in", "as we navigate", "the AI world is on fire".
- ZERO emoji in body paragraphs. Section headers and the final 🎧 line are the only allowed emojis.
- Use EXACT numbers, names, prices, dates from the source items. Never invent specifics.
- Use the EXACT URL from each source item — never fabricate links.
- Don't open with "Folks," "Hey there," "Welcome back," "So,". Start with something specific to today.
- If a story is too technical (vector DB, MLOps tooling, niche research), skip it from the deep-reads even if it's marked deep-read in input — your readers don't care about it.
- Output ONLY the JSON object. No markdown code fences around it, no preamble, no commentary."""


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def build_user_prompt(deep_reads: list[dict], skims: list[dict], date_str: str) -> str:
    def format_item(item: dict, include_analysis: bool = True) -> str:
        lines = [f"- Title: {item.get('title', '')}"]
        lines.append(f"  Source: {item.get('source', '')}")
        lines.append(f"  URL: {item.get('url', '')}")
        if include_analysis:
            if item.get("summary"):
                lines.append(f"  Summary: {item['summary']}")
            if item.get("reason"):
                lines.append(f"  Why-it-matters: {item['reason']}")
        return "\n".join(lines)

    deep_block = "\n\n".join(format_item(i) for i in deep_reads) if deep_reads else "(none today)"
    skim_block = "\n\n".join(format_item(i, include_analysis=False) for i in skims) if skims else "(none today)"

    return (
        f"# TODAY'S NEWS — {date_str}\n\n"
        f"## DEEP-READS ({len(deep_reads)} items — cover each in 'Today's Big Stories')\n\n"
        f"{deep_block}\n\n"
        f"## SKIMS ({len(skims)} items — pick top 5 for 'Worth Knowing')\n\n"
        f"{skim_block}\n\n"
        f"# YOUR TASK\n\n"
        f"Write today's Daily AI News post following the structure and voice rules. "
        f"Return ONLY the JSON object — no code fences, no commentary."
    )


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def get_client() -> "OpenAI":
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("[narrative] ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    # Strip ```json or ``` fences if the model wraps the output
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def write_narrative(deep_reads: list[dict], skims: list[dict], date_str: str) -> dict:
    client = get_client()
    user_prompt = build_user_prompt(deep_reads, skims, date_str)

    print(f"[narrative] Calling {WRITE_MODEL} (deep-reads: {len(deep_reads)}, skims: {len(skims)})...")
    response = client.chat.completions.create(
        model=WRITE_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,   # higher temp — voice and humor need room
        max_tokens=2500,   # 1200 words ≈ ~1800 tokens plus title/subtitle
    )
    raw = response.choices[0].message.content
    return extract_json(raw)


# ---------------------------------------------------------------------------
# Markdown → TTS plain text
# ---------------------------------------------------------------------------

_EMOJI_RE = re.compile(
    "["                                # broad emoji ranges
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F900-\U0001F9FF"
    "\U0001F000-\U0001F02F"
    "]+",
    flags=re.UNICODE,
)


def markdown_to_tts(md: str) -> str:
    """Convert Substack-bound Markdown into plain text the TTS engine reads naturally.

    - Strips emojis (TTS reads them as awkward names)
    - Strips Markdown link syntax — keeps the visible text, drops the URL
    - Strips heading markers (# ## ###) but keeps the text
    - Strips bold/italic markers
    - Strips horizontal rules
    - Collapses multiple blank lines
    """
    text = md

    # Drop Markdown links: [text](url) -> text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Drop heading hashes
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)

    # Drop emphasis markers
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)

    # Drop horizontal rules
    text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)

    # Drop "Source: ..." labels (TTS doesn't need to read them aloud)
    text = re.sub(r"^\s*\*?\*?Source:\*?\*?.*$", "", text, flags=re.MULTILINE | re.IGNORECASE)

    # Convert bullet dashes to natural pause
    text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)

    # Strip emojis
    text = _EMOJI_RE.sub("", text)

    # Collapse blank lines, trim
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[narrative] ERROR: {INPUT_FILE} not found. Run classify.py first.", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    deep_reads = [i for i in items if i.get("category") == "deep-read"]
    skims = [i for i in items if i.get("category") == "skim"]

    if not deep_reads and not skims:
        print("[narrative] No deep-reads or skims to write about. Aborting.", file=sys.stderr)
        sys.exit(1)

    date_str = datetime.now(IST).strftime("%A, %d %B %Y")
    print(f"[narrative] Writing post for {date_str}")

    result = write_narrative(deep_reads, skims, date_str)

    # Validate
    for required in ("title", "subtitle", "body_markdown"):
        if required not in result:
            print(f"[narrative] ERROR: model output missing required field {required!r}", file=sys.stderr)
            print(f"[narrative] Got keys: {list(result.keys())}", file=sys.stderr)
            sys.exit(1)

    word_count = len(result["body_markdown"].split())
    print(f"[narrative] Title:    {result['title']}")
    print(f"[narrative] Subtitle: {result['subtitle']}")
    print(f"[narrative] Body:     {word_count} words")

    # Persist Markdown JSON for the Substack publisher
    with open(OUTPUT_FILE_JSON, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"[narrative] Written:  {OUTPUT_FILE_JSON}")

    # Persist TTS-friendly plain text for the podcast generator
    tts_text = (
        f"{result['title']}.\n\n"
        f"{result['subtitle']}.\n\n"
        f"{markdown_to_tts(result['body_markdown'])}"
    )
    with open(OUTPUT_FILE_TTS, "w", encoding="utf-8") as f:
        f.write(tts_text)
    print(f"[narrative] Written:  {OUTPUT_FILE_TTS} ({len(tts_text.split())} words for TTS)")


if __name__ == "__main__":
    main()