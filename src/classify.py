import json
import os
import re
import sys
import time

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
INPUT_FILE = os.path.join(REPO_ROOT, "news_items.json")
OUTPUT_FILE = os.path.join(REPO_ROOT, "classified_items.json")
CONFIG_FILE = os.path.join(REPO_ROOT, "config.json")

RATE_LIMIT_DELAY = 0.6  # seconds between API calls

try:
    from openai import OpenAI
except ImportError:
    print("[classify] ERROR: openai not installed. Run: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Role-specific system prompts
# ---------------------------------------------------------------------------

SYSTEM_PROMPTS = {
    "Architect": (
        "You are classifying AI news articles for a Software Architect specialising in enterprise AI systems. "
        "DEEP-READ: agentic AI systems, Model Context Protocol (MCP), enterprise AI architecture patterns, "
        "multi-agent orchestration frameworks, foundation/frontier model releases with architectural implications, "
        "AI infrastructure cost and performance, RAG and retrieval architectures, vector database developments, "
        "LLM deployment patterns, AI platform strategy, AI governance frameworks, system design with LLMs. "
        "SKIM: general AI tool releases with architectural implications, cloud provider AI service updates, "
        "AI product launches worth tracking, industry AI trend summaries. "
        "SKIP: consumer AI apps, celebrity/pop-culture AI, pure finance/investment stories with no architectural "
        "depth, repetitive news with no new information."
    ),

    "Software Developer": (
        "You are classifying AI news articles for a Software Developer who builds AI-powered applications. "
        "DEEP-READ: major AI framework releases or breaking changes (LangChain, LlamaIndex, Haystack, CrewAI, "
        "AutoGen, etc.), new AI coding tools and IDE integrations (GitHub Copilot, Cursor, Codeium), API "
        "changes and new capabilities, open-source model releases with benchmarks and usage examples, "
        "SDK updates, function/tool calling improvements, significant bugs or CVEs in AI libraries, "
        "local model running (Ollama, llama.cpp). "
        "SKIM: AI research with near-term practical applications, new AI-powered developer tools, "
        "general industry news affecting tooling choices, AI product launches with relevant APIs. "
        "SKIP: pure business strategy, executive commentary, consumer AI lifestyle stories, "
        "policy without technical detail."
    ),

    "Data / AI Analyst": (
        "You are classifying AI news articles for a Data/AI Analyst. "
        "DEEP-READ: new benchmark datasets and leaderboards, model evaluation methodologies and results, "
        "analytics tool releases, research papers with quantitative findings, BI and AI convergence "
        "developments, data quality and lineage tools, explainability and interpretability research, "
        "new evaluation frameworks (MMLU, HELM, etc.), statistical methodology updates, data pipeline "
        "AI integrations, feature engineering with LLMs. "
        "SKIM: general model releases (noting evaluation scores), industry AI adoption statistics, "
        "new AI-powered analytics and BI products. "
        "SKIP: pure software engineering, business strategy without data angle, consumer AI stories, "
        "infrastructure deep dives."
    ),

    "DevOps / Platform Engineer": (
        "You are classifying AI news articles for a DevOps/Platform Engineer managing AI infrastructure. "
        "DEEP-READ: AI infrastructure tooling (Ray, Kubeflow, MLflow, BentoML, etc.), MLOps platform "
        "updates, GPU/TPU availability and pricing changes, containerisation for AI workloads, Kubernetes "
        "AI operators and schedulers, model serving frameworks (vLLM, TGI, Triton Inference Server), "
        "cloud AI service changes and pricing, CI/CD for ML pipelines, observability and monitoring for "
        "AI, LLM inference cost optimisation, model quantisation and distillation for deployment. "
        "SKIM: new AI services on cloud platforms, general DevOps and AI convergence, "
        "infrastructure-relevant model releases, AI security at the platform layer. "
        "SKIP: AI research papers, business strategy, consumer AI, product management news."
    ),

    "Security Engineer": (
        "You are classifying AI news articles for a Security Engineer focused on AI systems security. "
        "DEEP-READ: prompt injection vulnerabilities and defences, jailbreak techniques, AI model data "
        "poisoning, training data extraction and privacy attacks, adversarial ML research, AI red-teaming "
        "methodologies and tools, LLM security frameworks, OWASP LLM Top 10 updates, AI supply chain "
        "risks, AI governance and compliance requirements, model backdoors, AI-assisted cyberattacks, "
        "AI bias findings with security implications. "
        "SKIM: general AI policy and regulation news, model releases with safety evaluations, "
        "enterprise AI security product launches, AI ethics discussions with security angle. "
        "SKIP: pure business/finance news, consumer AI without security angle, non-security AI research, "
        "developer tooling without security relevance."
    ),

    "QA / Test Engineer": (
        "You are classifying AI news articles for a QA/Test Engineer working with AI systems. "
        "DEEP-READ: AI testing frameworks and tools, LLM evaluation methodologies and benchmarks, "
        "quality assurance for AI outputs, test automation enhanced by AI, AI output validation "
        "techniques, regression testing for ML models, handling non-determinism in AI testing, "
        "AI-powered test generation and maintenance, evaluation datasets and leaderboards, "
        "hallucination detection tools, property-based testing for AI. "
        "SKIM: general AI tool releases relevant to testing workflows, AI research with QA implications, "
        "CI/CD improvements for ML, AI product launches with testability considerations. "
        "SKIP: business strategy, consumer AI, pure research without testing/evaluation angle, "
        "infrastructure news without QA relevance."
    ),

    "Business Analyst": (
        "You are classifying AI news articles for a Business Analyst focused on enterprise AI adoption. "
        "DEEP-READ: enterprise AI adoption case studies and lessons learned, AI ROI and business value "
        "evidence, process automation with AI, AI in specific industry verticals (finance, healthcare, "
        "retail, insurance, etc.), workforce impact and change management studies, AI governance for "
        "business decisions, use case catalogues, AI project outcome reports, regulatory compliance "
        "requirements for AI, stakeholder communication patterns for AI initiatives. "
        "SKIM: general industry AI news, new AI product launches with business use cases, AI regulation "
        "with business impact, AI vendor landscape changes. "
        "SKIP: deep technical AI research, developer tooling, infrastructure news, consumer AI lifestyle."
    ),

    "Product Manager": (
        "You are classifying AI news articles for a Product Manager building or managing AI products. "
        "DEEP-READ: new AI product launches and major feature announcements, AI UX and interaction design "
        "research, competitive AI product landscape changes, user research on AI adoption and trust, "
        "AI pricing model changes, product strategy around AI capabilities, model capability improvements "
        "that unlock new product possibilities, AI feature parity analysis, AI product metrics and KPIs. "
        "SKIM: AI industry trends affecting product roadmaps, enterprise AI adoption statistics, "
        "AI regulation affecting product decisions, technical news with product implications. "
        "SKIP: deep infrastructure news, pure academic research, implementation-level technical details, "
        "consumer AI without product strategy angle."
    ),

    "Scrum Master / Agile Coach": (
        "You are classifying AI news articles for a Scrum Master or Agile Coach. "
        "DEEP-READ: AI tools that measurably improve team velocity and delivery flow, AI in agile planning "
        "and retrospectives, DORA metrics and AI impact on delivery performance, AI-powered project and "
        "sprint management tools, AI for backlog refinement and story estimation, agile methodology "
        "evolution driven by AI, team psychological safety with AI tools, AI in ceremonies and facilitation. "
        "SKIM: general AI productivity research, enterprise AI adoption trends, new AI collaboration tools, "
        "AI impact on engineering roles and team structure. "
        "SKIP: deep technical/infrastructure news, financial/investment AI news, academic AI research, "
        "consumer AI stories."
    ),

    "Engineering Manager": (
        "You are classifying AI news articles for an Engineering Manager. "
        "DEEP-READ: AI impact on developer productivity metrics (DORA, SPACE framework), AI coding tool "
        "adoption data and measured ROI, engineering team AI tooling decisions and build vs buy analysis, "
        "AI-related hiring trends and skills market, cost analysis of AI tools for engineering teams, "
        "AI in code review and quality gates, team structure and org design changes due to AI, "
        "AI governance responsibilities for engineering managers. "
        "SKIM: general AI industry news, model releases affecting team tooling choices, AI regulation "
        "with hiring implications, AI product management insights. "
        "SKIP: deep AI research, consumer AI, infrastructure deep dives without management angle, "
        "academic papers."
    ),

    "Delivery Manager": (
        "You are classifying AI news articles for a Delivery Manager overseeing AI project delivery. "
        "DEEP-READ: AI project risk patterns and mitigation strategies, vendor AI product pricing and "
        "contractual changes, AI delivery acceleration case studies, AI project outcome reports "
        "(successes and failures), scope and estimation challenges in AI projects, client-facing AI "
        "delivery patterns, AI vendor reliability and SLA data, AI project governance frameworks, "
        "resource and skill availability for AI delivery. "
        "SKIM: general enterprise AI adoption, new AI vendor offerings, AI regulation affecting "
        "project delivery, AI productivity tools for project teams. "
        "SKIP: deep technical research, consumer AI, financial/investment news, developer tooling."
    ),

    "Practice Lead / CoE Lead": (
        "You are classifying AI news articles for a Practice Lead or Centre of Excellence (CoE) Lead. "
        "DEEP-READ: AI thought leadership publications and framework releases, AI skills and talent market "
        "trends, Centre of Excellence best practice guides, AI training and enablement programme designs, "
        "AI maturity models, industry AI adoption benchmarks for consulting, AI operating model patterns, "
        "knowledge management for AI practices, community of practice guidance, AI consultant toolkit "
        "updates, skilling pathways and certifications. "
        "SKIM: major AI product launches relevant to practice offerings, AI research with practitioner "
        "implications, AI regulation affecting consulting and advisory practices. "
        "SKIP: deeply technical infrastructure news, consumer AI, financial market AI, "
        "narrow developer tooling."
    ),

    "Senior Management / Executive": (
        "You are classifying AI news articles for a Senior Manager or C-suite Executive. "
        "DEEP-READ: AI business impact evidence and quantified ROI, investment and funding trends, "
        "AI regulation and government policy changes with business implications, competitive AI moves by "
        "major companies, AI workforce transformation studies, board-level AI risk and governance, "
        "AI strategic partnerships and M&A activity, AI market sizing and growth forecasts, "
        "analyst reports on AI maturity. "
        "SKIM: major AI product launches and capability milestones, enterprise AI adoption stories, "
        "AI ethics and public perception developments. "
        "SKIP: technical AI research, developer tooling, infrastructure details, implementation specifics, "
        "academic papers."
    ),

    "Pre-Sales / Solutions Consultant": (
        "You are classifying AI news articles for a Pre-Sales or Solutions Consultant. "
        "DEEP-READ: new AI capabilities and features relevant to client pitches, client success stories "
        "and quantified case studies, competitive AI product differentiation and positioning changes, "
        "AI pricing model changes affecting proposals, technical depth articles that strengthen solution "
        "credibility, new AI solution patterns for common client problems, proof-of-concept approaches, "
        "RFP-relevant AI capability benchmarks, AI vendor partnership announcements. "
        "SKIM: general AI industry trends useful for client conversations, AI analyst reports and market "
        "research, major vendor announcements, AI regulation affecting sales discussions. "
        "SKIP: deeply technical infrastructure news without pitch value, academic research, consumer AI "
        "stories, developer tooling."
    ),

    "Account Manager": (
        "You are classifying AI news articles for an Account Manager managing AI-related client accounts. "
        "DEEP-READ: AI news relevant to clients' specific industries (finance, healthcare, retail, etc.), "
        "AI vendor announcements that affect existing client relationships or contracts, AI regulatory "
        "changes in client sectors, AI investment trends in client verticals, capability launches "
        "creating upsell or cross-sell opportunities, AI competitor moves affecting clients, "
        "client-specific AI use case developments. "
        "SKIM: general enterprise AI adoption trends, major AI product launches, AI regulation news, "
        "AI vendor ecosystem changes. "
        "SKIP: deep technical/research content, infrastructure details, developer tooling, academic papers."
    ),
}

CLASSIFY_SUFFIX = """

Respond ONLY with a valid JSON object — no markdown, no code fences, no preamble.
Use this exact schema:
{
  "title": "<article title>",
  "url": "<article url>",
  "source": "<source name>",
  "category": "deep-read|skim|skip",
  "reason": "<one sentence explanation of why this category was chosen>",
  "summary": "<two sentence summary of the article>"
}
Use "skip" if this article has no relevance to the role.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_client() -> "OpenAI":
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("[classify] ERROR: GITHUB_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    return OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=token,
    )


def extract_json(text: str) -> dict:
    text = text.strip()
    # Strip markdown code fences if the model wraps the output
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text.strip())


def classify_item(client, item: dict, system_prompt: str) -> dict | None:
    user_content = (
        f"Title: {item['title']}\n\n"
        f"Description: {item.get('description', 'No description available.')}"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt + CLASSIFY_SUFFIX},
                {"role": "user", "content": user_content},
            ],
            temperature=0.2,
            max_tokens=350,
        )
        raw = response.choices[0].message.content
        result = extract_json(raw)
        result.setdefault("url", item["url"])
        result.setdefault("source", item["source"])
        result.setdefault("title", item["title"])
        return result
    except json.JSONDecodeError as e:
        print(f"[classify] JSON parse error for '{item['title']}': {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"[classify] API error for '{item['title']}': {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    for path, label in [(INPUT_FILE, "news_items.json"), (CONFIG_FILE, "config.json")]:
        if not os.path.exists(path):
            print(f"[classify] ERROR: {path} not found. {label} must exist before running classify.py.", file=sys.stderr)
            sys.exit(1)

    with open(INPUT_FILE, encoding="utf-8") as f:
        items: list[dict] = json.load(f)

    with open(CONFIG_FILE, encoding="utf-8") as f:
        config: dict = json.load(f)

    role = config.get("role", "Software Developer")
    system_prompt = SYSTEM_PROMPTS.get(role, SYSTEM_PROMPTS["Software Developer"])
    print(f"[classify] Role: {role} | Items to classify: {len(items)}")

    client = get_client()
    results: list[dict] = []

    for i, item in enumerate(items, 1):
        print(f"[classify] {i}/{len(items)}: {item['title'][:70]}...")
        result = classify_item(client, item, system_prompt)
        if result and result.get("category") != "skip":
            results.append(result)
        if i < len(items):
            time.sleep(RATE_LIMIT_DELAY)

    deep_reads = [r for r in results if r.get("category") == "deep-read"]
    skims = [r for r in results if r.get("category") == "skim"]
    print(f"[classify] Done — deep-read: {len(deep_reads)}, skim: {len(skims)}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[classify] Written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
