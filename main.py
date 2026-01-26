from flask import Flask, request, render_template  # Changed import
import google.generativeai as genai
import json
import os

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash-lite")

customers = {}

def agent_respond(gemini_text):
    try:
        cleaned = gemini_text.strip()
        if cleaned.startswith('```json'):
            cleaned = cleaned[7:]
        if cleaned.endswith('```'):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        data = json.loads(cleaned)
        name = data["name"]
        email = data["email"]
        if email in customers:
            return f"Customer {name} already exists."
        customers[email] = {"name": name, "email": email}
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
        gemini_prompt = f"""Extract name and email from: "{prompt}"
        Return ONLY JSON: {{"name": "...", "email": "..."}}"""
        gemini_response = model.generate_content(contents=gemini_prompt)
        gemini_text = gemini_response.text
        print("RAW GEMINI:", repr(gemini_text))
        response_text = agent_respond(gemini_text)  # Fixed duplicate calls
    return render_template("index.html", response=response_text, customers=customers)

if __name__ == "__main__":
    app.run(debug=True)
