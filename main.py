from flask import Flask, request, render_template
import google.generativeai as genai
import json
import os

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

customers = {}


def extract_key_info(raw_input):
    try:
        extract_prompt = f"""From this raw customer input, extract the MOST BUSINESS-CRITICAL 
        information.

Look for ANY of these (in order of importance):
1. READY TO BUY signals ("ready to buy", "want to purchase", "need now")
2. Budgets ($50K, $100k, 50 thousand)
3. Timelines (Q1, Q2, next month, urgent)
4. Projects (CRM eval, migration, RFP)
5. Decision maker titles (CTO wants, VP approved)

Input: "{raw_input}"

Return ONLY the most important business detail as short phrase, or "N/A".

Examples:
"ready to buy now" → "ready to buy"
"Add CTO Sarah Q2 $50K" → "Q2 $50K"
"VP Mike needs CRM urgent" → "urgent CRM need"
"John just browsing" → "N/A"

→ """

        extract_response = model.generate_content(extract_prompt)
        key_info = extract_response.text.strip()
        if key_info.startswith('```'): key_info = key_info[3:]
        if key_info.endswith('```'): key_info = key_info[:-3:]
        key_info = key_info.strip().replace('"', '').replace('\n', ' ')

        return key_info if len(key_info) > 2 else "N/A"
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
            else:
                return f"No customer found matching '{name}'."

        else:  # add action
            email = data["email"]
            if email in customers:
                return f"Customer {name} already exists."

            # Extract key business info with Gemini
            key_info = extract_key_info(prompt)

            customers[email] = {
                "name": name,
                "email": email,
                "raw_input": prompt,
                "key_info": key_info  # NEW: AI-extracted business intel
            }
            return f"Customer {name} added successfully."

    except Exception as e:
        print("PARSE ERROR:", e)
        return "Couldn't parse the response."


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    if request.method == "POST":
        prompt = request.form["prompt"]
        gemini_prompt = f"""Analyze this command and extract info.
User said: "{prompt}"

Return ONLY JSON with this exact structure:
{{
  "action": "add" or "delete",
  "name": "customer full name",
  "email": "customer email" (only for add)
}}

Examples:
"Add John Doe john@acme.com" → {{"action": "add", "name": "John Doe", "email": "john@acme.com"}}
"Delete John Doe" → {{"action": "delete", "name": "John Doe"}}
"Remove Sarah" → {{"action": "delete", "name": "Sarah"}}"""

        gemini_response = model.generate_content(gemini_prompt)
        gemini_text = gemini_response.text
        print("RAW GEMINI:", repr(gemini_text))
        response_text = agent_respond(gemini_text, prompt)

    return render_template("index.html", response=response_text, customers=customers)


if __name__ == "__main__":
    app.run(debug=True)
