from flask import Flask, request, render_template
import google.generativeai as genai
import json
import os

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

customers = {}

def agent_respond(gemini_text, prompt):  # Added prompt parameter
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
            # Find customer by name (case-insensitive partial match)
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

        else:  # add action (default)
            email = data["email"]
            if email in customers:
                return f"Customer {name} already exists."
            # SAVE RAW INPUT with customer data
            customers[email] = {
                "name": name,
                "email": email,
                "raw_input": prompt  # NEW: Preserve full user input
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
        # Pass prompt to agent_respond
        response_text = agent_respond(gemini_text, prompt)

    return render_template("index.html", response=response_text, customers=customers)

if __name__ == "__main__":
    app.run(debug=True)
