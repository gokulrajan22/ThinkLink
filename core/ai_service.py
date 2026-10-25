"""Optional Groq-powered problem decomposition with deterministic fallback."""
import json
import os

from .views_skill_catalog import SKILL_CATALOG, RULE_TRIGGERS


def _fallback_requirements(problem_statement):
    text = f" {problem_statement.lower()} "
    found = []
    for skill, triggers in RULE_TRIGGERS.items():
        if any(trigger in text for trigger in triggers):
            found.append(skill)
    if not found:
        found = ["python", "javascript", "research"]
    return {
        "required_skills": found,
        "roles": [],
        "problem_summary": problem_statement.strip()[:280],
        "reasoning": "Rule-based fallback: skills were mapped from keywords in the problem statement.",
        "analysis_source": "rules",
    }


def analyze_problem(problem_statement):
    """Use Groq's OpenAI-compatible Responses API when configured; never require a key to boot."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return _fallback_requirements(problem_statement), "GROQ_API_KEY is not configured; using transparent rule-based analysis."
    try:
        from openai import OpenAI

        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b").strip() or "openai/gpt-oss-20b"
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=25.0,
            max_retries=1,
        )
        catalog = [{"id": key, "label": value} for key, value in SKILL_CATALOG.items()]
        response = client.responses.create(
            model=model,
            instructions=(
                "You are ThinkLink's team planning assistant. Analyze project requirements, not people. "
                "Return ONLY a valid JSON object with keys: problem_summary (string), required_skills (array of skill IDs), "
                "roles (array of short role names), reasoning (string). Select skill IDs only from the supplied catalog. "
                "Infer only skills plausibly needed by the stated project. Keep reasoning concise and explain uncertainty. "
                "Do not predict hackathon wins or project success."
            ),
            input=json.dumps({"problem_statement": problem_statement[:8000], "allowed_skill_catalog": catalog}, ensure_ascii=False),
            max_output_tokens=900,
        )
        data = json.loads(response.output_text)
        allowed = set(SKILL_CATALOG)
        skills = []
        for item in data.get("required_skills", []):
            key = str(item).strip().lower()
            if key in allowed and key not in skills:
                skills.append(key)
        if not skills:
            return _fallback_requirements(problem_statement), "Groq returned no recognized skill IDs; using rule-based fallback."
        return {
            "required_skills": skills[:12],
            "roles": [str(x)[:80] for x in data.get("roles", [])[:6] if str(x).strip()],
            "problem_summary": str(data.get("problem_summary", ""))[:500],
            "reasoning": str(data.get("reasoning", "Groq identified likely project requirements."))[:1200],
            "analysis_source": "groq",
        }, None
    except Exception as exc:
        # Do not leak credentials or raw provider payloads into the UI/log.
        try:
            from openai import APIConnectionError, APIStatusError, RateLimitError
            provider_errors = (APIConnectionError, APIStatusError, RateLimitError)
        except ImportError:
            provider_errors = ()
        if provider_errors and isinstance(exc, provider_errors):
            reason = f"Groq request failed ({exc.__class__.__name__}); using rule-based fallback."
        elif isinstance(exc, (ValueError, KeyError, TypeError)):
            reason = "Groq response could not be parsed; using rule-based fallback."
        else:
            reason = f"Groq analysis unavailable ({exc.__class__.__name__}); using rule-based fallback."
        return _fallback_requirements(problem_statement), reason
