import os

from groq import Groq

MODEL = "openai/gpt-oss-120b"


def generate_briefing(scored_assets: list[dict]) -> str:
    api_key = os.environ.get("GROQ_API_KEY")
    at_risk = [a for a in scored_assets if a["risk_score"] > 0][:10]

    if not at_risk:
        return "No active hazards currently intersect monitored assets. All systems nominal."

    if not api_key:
        return _fallback_briefing(at_risk)

    lines = []
    for a in at_risk:
        top_hazard = a["hazards"][0]
        lines.append(
            f"- {a['name']} ({a['type']}, {a['criticality']}): risk {a['risk_score']} "
            f"— {top_hazard['event_type']} [{top_hazard['severity']}]: {top_hazard['headline']}"
        )
    prompt = (
        "You are an operations briefing assistant for a critical infrastructure monitoring team. "
        "Given the following at-risk assets ranked by computed risk score, write a concise operational "
        "briefing (5-8 sentences) for a shift supervisor. Lead with the highest-priority items, group by "
        "hazard type where sensible, and end with 1-2 concrete recommended actions. Do not invent data "
        "beyond what is given.\n\n" + "\n".join(lines)
    )

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500,
        )
        return resp.choices[0].message.content.strip()
    except Exception as exc:  # noqa: BLE001
        return _fallback_briefing(at_risk) + f"\n\n(LLM briefing unavailable: {exc})"


def _fallback_briefing(at_risk: list[dict]) -> str:
    top = at_risk[0]
    return (
        f"{len(at_risk)} asset(s) currently show elevated risk. Highest priority: {top['name']} "
        f"(score {top['risk_score']}) affected by {top['hazards'][0]['event_type']}. "
        "Set GROQ_API_KEY to enable full narrative briefings."
    )
