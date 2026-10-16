import os

from groq import Groq


DEFAULT_MODEL = "openai/gpt-oss-120b"


def generate_budget_observations(
    metrics: dict,
    budget_rows: list[dict],
    model: str = DEFAULT_MODEL,
) -> str:
    """Ask Groq for concise budgeting observations using summary figures only."""
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise RuntimeError(
            "Groq API key is not configured. Add GROQ_API_KEY to Streamlit secrets."
        )

    safe_summary = {
        "monthly_income_pkr": round(metrics["income"]),
        "monthly_expenses_pkr": round(metrics["expenses"]),
        "estimated_monthly_surplus_pkr": round(metrics["monthly_savings"]),
        "budget_categories": budget_rows[:20],
    }

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a household budgeting assistant. Be concise, practical, "
                    "and non-judgmental. Use PKR. State that figures are estimates. "
                    "Do not promise investment returns or give investment advice."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Give 3 to 5 useful observations and one next step based on "
                    f"these monthly household figures: {safe_summary}"
                ),
            },
        ],
        temperature=0.3,
        max_tokens=500,
    )

    return response.choices[0].message.content or "No summary was returned."
