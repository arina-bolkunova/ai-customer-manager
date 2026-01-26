from flask import Flask, request, render_template
import google.generativeai as genai
import json
import os
import re
import matplotlib.pyplot as plt
import io
import base64
from collections import Counter

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

customers = {}


def clean_name(name):
    """Remove titles from name - CTO Jo → Jo"""
    name_lower = name.lower().strip()
    title_prefixes = ['cto', 'cfo', 'cio', 'vp', 'director', 'head', 'chief', 'mr', 'mrs', 'dr',
                      'ms']

    for prefix in title_prefixes:
        if name_lower.startswith(prefix + ' '):
            return name[len(prefix) + 1:].strip().title()

    return name.title()


def calculate_lead_score(raw_input):
    """Intelligent lead scoring - FIXED for gmail"""
    score = 70

    raw_lower = raw_input.lower()

    # GMAIL = LOW PRIORITY (Lead only)
    if '@gmail.com' in raw_lower:
        return 70

    # EXECUTIVE TITLES (+10-20 points)
    exec_titles = ['cto', 'cfo', 'cio', 'vp', 'director', 'head', 'chief']
    title_count = sum(1 for title in exec_titles if title in raw_lower)
    score += title_count * 8

    # PREMIUM DOMAINS (+12 points)
    premium_signals = ['enterprise', 'corp', 'io', 'co', 'tech']
    if any(domain in raw_lower for domain in premium_signals):
        score += 12

    # BUY INTENT (+15 max)
    buy_signals = ['ready to buy', 'need now', 'urgent', 'approved']
    intent_count = sum(1 for signal in buy_signals if signal in raw_lower)
    score += intent_count * 8

    # BUDGET (+12)
    if re.search(r'\$\s*\d+[kKm]?\b', raw_input, re.IGNORECASE):
        score += 12

    # TIMELINE (+10)
    timeline = ['q1', 'q2', 'q3', 'q4', 'next month']
    if any(t in raw_lower for t in timeline):
        score += 10

    return min(score, 95)


def get_category(score):
    if score >= 90:
        return "Platinum"
    elif score >= 80:
        return "Gold"
    return "Lead"


def extract_key_info(raw_input):
    """Capture ALL critical business info - FIXED budget detection"""
    info_parts = []
    raw_lower = raw_input.lower()

    # 1. TITLES
    exec_titles = ['cto', 'cfo', 'cio', 'vp', 'director', 'head']
    for title in exec_titles:
        if title in raw_lower:
            info_parts.append(title.upper())
            break

    # 2. BUDGET - FIXED (standalone "100k budget" works)
    euro_match = re.search(r'(\d+(?:,\d+)?[kKm]?)€?', raw_input, re.I)
    dollar_match = re.search(r'\$\s*(\d+(?:,\d+)?[kKm]?)', raw_input, re.I)
    standalone_budget = re.search(r'\b(\d+(?:,\d+)?[kKm]?)\s*budget\b', raw_input, re.I)

    if euro_match:
        info_parts.append(f"{euro_match.group(1)}€")
    elif dollar_match:
        info_parts.append(f"${dollar_match.group(1)}")
    elif standalone_budget:
        info_parts.append(f"{standalone_budget.group(1)}k budget")

    # 3. YEAR TIMELINE
    year_match = re.search(r'\b(20[2-9]\d)\b', raw_input, re.I)
    if year_match:
        info_parts.append(f"{year_match.group(1)} timeline")

    # 4. QUARTER TIMELINE
    q_match = re.search(r'(q[1-4])', raw_input, re.I)
    if q_match:
        info_parts.append(q_match.group(1).upper())

    # 5. INTENT - Skip negatives
    negative_intent = 'not ready to buy' in raw_lower or 'not interested' in raw_lower or "won't " \
                                                                                          "buy" \
                      in raw_lower

    if not negative_intent:
        intent_phrases = ['ready to buy', 'need now', 'urgent', 'approved']
        for phrase in intent_phrases:
            if phrase in raw_lower:
                info_parts.append("HIGH INTENT")
                break

    return ' | '.join(info_parts) if info_parts else "N/A"


def generate_pie_chart(customers):
    """Generate category distribution pie chart"""
    if not customers:
        return None

    category_counts = Counter(c['category'] for c in customers.values())
    labels = list(category_counts.keys())
    sizes = list(category_counts.values())

    colors = ['#6B7280', '#10B981', '#F59E0B']  # Lead(gray), Gold(green), Platinum(gold)

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%',
                                      colors=colors[:len(labels)], startangle=90)

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title('Lead Categories', fontsize=16, fontweight='bold')
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    return img_base64


def agent_respond(gemini_text, prompt):
    try:
        cleaned = gemini_text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        action = data.get("action", "add")
        name = data["name"]

        clean_name_result = clean_name(name)
        print(f"Raw name: '{name}' → Clean name: '{clean_name_result}'")

        if action == "delete":
            deleted_email = None
            for email, customer in customers.items():
                if clean_name_result.lower() in customer["name"].lower():
                    deleted_email = email
                    break
            if deleted_email:
                del customers[deleted_email]
                return f"Customer '{clean_name_result}' deleted successfully."
            return f"No customer found matching '{clean_name_result}'."

        else:  # add
            email = data["email"]
            if email in customers:
                return f"Customer {clean_name_result} already exists."

            score = calculate_lead_score(prompt)
            category = get_category(score)
            key_info = extract_key_info(prompt)

            customers[email] = {
                "name": clean_name_result,
                "email": email,
                "raw_input": prompt,
                "key_info": key_info,
                "score": score,
                "category": category
            }
            return f"Customer {clean_name_result} added ({score}/{category})."

    except Exception as e:
        print("PARSE ERROR:", e)
        return "Couldn't parse the response."


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    if request.method == "POST":
        prompt = request.form["prompt"]
        gemini_prompt = f"""Analyze: "{prompt}"

CRITICAL: "name" = PERSONAL FIRST/LAST NAME ONLY
Ignore ALL titles (CTO VP Director Mr Mrs Dr).

Examples:
"CTO jo jo@gmail.com" → {{"action":"add","name":"jo","email":"jo@gmail.com"}}
"Add VP Sarah sarah@acme.com" → {{"action":"add","name":"Sarah","email":"sarah@acme.com"}}
"Delete John" → {{"action":"delete","name":"John"}}

Return ONLY JSON:
{{"action": "add|delete", "name": "PERSONAL NAME", "email": "email"}}"""

        gemini_response = model.generate_content(gemini_prompt)
        gemini_text = gemini_response.text
        print("RAW GEMINI:", repr(gemini_text))
        response_text = agent_respond(gemini_text, prompt)

    pie_chart = generate_pie_chart(customers)

    return render_template("index.html",
                           response=response_text,
                           customers=customers,
                           pie_chart=pie_chart)


if __name__ == "__main__":
    app.run(debug=True)
