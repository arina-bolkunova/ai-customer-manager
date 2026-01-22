from flask import Flask, request, render_template_string
import google.generativeai as genai
import json
import os


import sys
print(sys.executable)

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


HTML_TEMPLATE = """
<!doctype html>
<title>AI Customer Demo</title>
<h2>Enter a customer command:</h2>
<form method=post>
  <input type=text name=prompt style="width:400px">
  <input type=submit value=Send>
</form>
<p>{{ response }}</p>
<p>Current Customers: {{ customers }}</p>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    if request.method == "POST":
        prompt = request.form["prompt"]
        gemini_prompt = f"""Extract name and email from: "{prompt}"
        Return ONLY JSON: {{"name": "...", "email": "..."}}"""
        gemini_response = model.generate_content(contents=gemini_prompt)
        gemini_text = gemini_response.text
        gemini_response = model.generate_content(contents=gemini_prompt)
        gemini_text = gemini_response.text
        print("RAW GEMINI:", repr(gemini_text))  # <--- add this
        response_text = agent_respond(gemini_text)
        response_text = agent_respond(gemini_text)
    return render_template_string(HTML_TEMPLATE, response=response_text, customers=customers)

if __name__ == "__main__":
    app.run(debug=True)
