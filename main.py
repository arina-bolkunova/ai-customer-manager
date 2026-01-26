from flask import Flask, request, render_template
import google.generativeai as genai
import json
import os
import re

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

customers = {}


def calculate_lead_score(raw_input):
    """Intelligent lead scoring based on business signals"""
    score = 80  # Base score

    raw_lower = raw_input.lower()

    # HIGH VALUE TITLES (+15-25 points)
    exec_titles = ['cto', 'cfo', 'cio', 'vp', 'director', 'head', 'chief', 'president', 'founder',
                   'owner']
    senior_count = sum(1 for title in exec_titles if title in raw_lower)
    if senior_count >= 2:
        score += 25
    elif senior_count == 1:
        score += 15

    # PREMIUM DOMAINS (+10-20 points)
    premium_domains = ['enterprise', 'corp', 'inc', 'io', 'co', 'tech']
    gmail_count = raw_lower.count('@gmail')
    company_count = sum(1 for domain in premium_domains if domain in raw_lower)
    if company_count > 0:
        score += 15
    elif gmail_count == 0:
        score += 10  # Assume business email

    # BUY INTENT (+20 points)
    buy_signals = ['ready to buy', 'want to purchase', 'need now', 'urgent', 'budget', 'approved']
    intent_count = sum(1 for signal in buy_signals if signal in raw_lower)
    score += intent_count * 10

    # TIMELINE (+10-15 points)
    timeline_signals = ['q1', 'q2', 'q3', 'q4', 'next month', 'this quarter']
    if any(signal in raw_lower for signal in timeline_signals):
        score += 12

    # BUDGET MENTIONS (+15 points)
    if re.search(r'\$\s*\d+[kkm]?\b', raw_input, re.IGNORECASE):
        score += 15

    # CAP score at 100
    return min(score, 100)


def get_category(score):
    """Convert score to business category"""
    if score >= 95:
        return "Platinum"
    elif score >= 85:
        return "Gold"
    else:
        return "Lead"


def extract_key_info(raw_input):
    """Extract business-critical info"""
    try:
        extract_prompt = f"""From: "{raw_input}"
Extract ONLY most business-critical info (buy signals, budget, timeline, project).
Return short phrase or "N/A".

Examples:
"ready to buy" → "ready to buy"
"Q2 $50K CRM" → "Q2 $50K CRM"
"CTO urgent" → "urgent" """

        extract_response = model.generate_content(extract_prompt)
        key_info = extract_response.text.strip()
        if key_info.startswith('```'): key_info = key_info[3:]
        if key_info.endswith('```'): key_info = key_info[:-3:]
        key_info = key_info.strip().replace('"', '').replace('\n', ' ')
        return key_info if len(key_info) > 3 else "N/A"
    except:
        return "N/A"


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

        if action == "delete":
            deleted_email = None
            for email, customer in customers.items():
                if name.lower() in customer["name"].lower():
                    deleted_email = email
                    break
            if deleted_email:
                del customers[deleted_email]
                return f"Customer '{name}' deleted successfully."
            return f"No customer found matching '{name}'."

        else:  # add
            email = data["email"]
            if email in customers:
                return f"Customer {name} already exists."

            # CALCULATE INTELLIGENT SCORE
            score = calculate_lead_score(prompt)
            category = get_category(score)
            key_info = extract_key_info(prompt)

            customers[email] = {
                "name": name,
                "email": email,
                "raw_input": prompt,
                "key_info": key_info,
                "score": score,  # NEW: 0-100 lead score
                "category": category  # NEW: Lead/Gold/Platinum
            }
            return f"Customer {name} added (Score: {score}/{category})."

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
Return ONLY JSON: {{"action": "add|delete", "name": "...", "email": "..."}}"""

        gemini_response = model.generate_content(gemini_prompt)
        gemini_text = gemini_response.text
        print("RAW GEMINI:", repr(gemini_text))
        response_text = agent_respond(gemini_text, prompt)

    return render_template("index.html", response=response_text, customers=customers)


if __name__ == "__main__":
    app.run(debug=True)
