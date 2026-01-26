from flask import Flask, request, render_template, Response, redirect
import google.generativeai as genai
import json
import os
import re
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import csv
from collections import Counter
from io import StringIO

api_key = os.getenv("API_KEY")
genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-exp")

customers = {}

def clean_name(name):
    name_lower = name.lower().strip()
    title_prefixes = ['cto', 'cfo', 'cio', 'vp', 'director', 'head', 'chief', 'mr', 'mrs', 'dr', 'ms']
    for prefix in title_prefixes:
        if name_lower.startswith(prefix + ' '):
            return name[len(prefix) + 1:].strip().title()
    return name.title()

def calculate_lead_score(raw_input):
    score = 70
    raw_lower = raw_input.lower()
    if '@gmail.com' in raw_lower:
        return 70
    exec_titles = ['cto', 'cfo', 'cio', 'vp', 'director', 'head', 'chief']
    title_count = sum(1 for title in exec_titles if title in raw_lower)
    score += title_count * 8
    premium_signals = ['enterprise', 'corp', 'io', 'co', 'tech', 'ai']
    if any(domain in raw_lower for domain in premium_signals):
        score += 12
    buy_signals = ['ready to buy', 'need now', 'urgent', 'approved']
    intent_count = sum(1 for signal in buy_signals if signal in raw_lower)
    score += intent_count * 8
    if re.search(r'\$\s*\d+[kKm]?\b', raw_input, re.IGNORECASE):
        score += 12
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
    info_parts = []
    raw_lower = raw_input.lower()
    exec_titles = ['cto', 'cfo', 'cio', 'vp', 'director', 'head']
    for title in exec_titles:
        if title in raw_lower:
            info_parts.append(title.upper())
            break
    euro_match = re.search(r'(\d+(?:,\d+)?[kKm]?)€?', raw_input, re.I)
    dollar_match = re.search(r'\$\s*(\d+(?:,\d+)?[kKm]?)', raw_input, re.I)
    standalone_budget = re.search(r'\b(\d+(?:,\d+)?[kKm]?)\s*budget\b', raw_input, re.I)
    if euro_match:
        info_parts.append(f"{euro_match.group(1)}€")
    elif dollar_match:
        info_parts.append(f"${dollar_match.group(1)}")
    elif standalone_budget:
        info_parts.append(f"{standalone_budget.group(1)}k budget")
    buy_phrases = ['wants to buy', 'ready to buy', 'need now', 'urgent', 'approved', 'looking for', 'interested in']
    negative_intent = any(phrase in raw_lower for phrase in ['not ready', 'not interested', "won't buy"])
    if not negative_intent:
        for phrase in buy_phrases:
            if phrase in raw_lower:
                info_parts.append("HIGH INTENT")
                break
    year_match = re.search(r'\b(20[2-9]\d)\b', raw_input, re.I)
    if year_match:
        info_parts.append(f"{year_match.group(1)} timeline")
    q_match = re.search(r'(q[1-4])', raw_input, re.I)
    if q_match:
        info_parts.append(q_match.group(1).upper())
    return ' | '.join(info_parts) if info_parts else "N/A"

def generate_pie_chart(customers):
    if not customers:
        return None
    category_counts = Counter(c['category'] for c in customers.values())
    labels = list(category_counts.keys())
    sizes = list(category_counts.values())
    colors = {'Lead': '#6B7280', 'Gold': '#FFD700', 'Platinum': '#10D178'}
    color_list = [colors[label] for label in labels]
    fig, ax = plt.subplots(figsize=(8, 6), facecolor='#111827')
    ax.set_facecolor('#111827')
    wedges, texts, autotexts = ax.pie(sizes, autopct='%d%%', colors=color_list, startangle=90, textprops={'fontsize': 18, 'fontweight': 'bold'})
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(22)
        autotext.set_fontweight('bold')
    ax.set_title('Lead Categories', fontsize=16, fontweight='bold', pad=20, color='white')
    ax.axis('equal')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', dpi=100, facecolor='#111827', edgecolor='none')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    plt.clf()
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
        else:
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
    except json.JSONDecodeError:
        return "Invalid AI response format. Try: 'John [john@company.com] wants to buy'"
    except KeyError as e:
        return f"Missing required field: {str(e)}. Include name + email in format: 'John [john@company.com]'"
    except Exception as e:
        print("PARSE ERROR:", e)
        return "Couldn't parse the response. Use format: 'Name [email@company.com] wants to buy'"

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    response_text = ""
    if request.method == "POST":
        prompt = request.form["prompt"].strip()
        if len(prompt) < 3:
            response_text = "Please enter a name and email (e.g. 'John [john@company.com]')"
        else:
            try:
                gemini_prompt = f"""Analyze: "{prompt}"

CRITICAL RULES:
1. "name" = FIRST WORD BEFORE EMAIL (ignore brackets)
2. Extract email from mailto: links OR plain emails
3. Ignore ALL titles (CTO VP Director)

Examples:
"delona [elodna@gmail.tech] wants to buy" → {{"action":"add","name":"delona","email":"elodna@gmail.tech"}}
"CTO jo [jo@acme.com]" → {{"action":"add","name":"jo","email":"jo@acme.com"}}
"Add VP Sarah [sarah@acme.com]" → {{"action":"add","name":"Sarah","email":"sarah@acme.com"}}

Return ONLY JSON:
{{"action": "add|delete", "name": "FIRST NAME", "email": "email@gmail.com"}}"""
                gemini_response = model.generate_content(gemini_prompt)
                gemini_text = gemini_response.text
                print("RAW GEMINI:", repr(gemini_text))
                response_text = agent_respond(gemini_text, prompt)
            except Exception as e:
                print(f"AI Error: {e}")
                response_text = f"AI processing failed. Try: 'John [john@company.com] wants to buy' (Error: {str(e)[:50]})"
    pie_chart = generate_pie_chart(customers)
    gold_platinum_count = len([c for c in customers.values() if c['category'] in ['Gold', 'Platinum']])
    return render_template("index.html",
                           response=response_text,
                           customers=customers,
                           pie_chart=pie_chart,
                           gold_platinum_count=gold_platinum_count)

@app.route('/download-customers')
def download_customers():
    if not customers:
        return "No customers to export", 404
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Name', 'Email', 'Score', 'Category', 'Key Info', 'Raw Input'])
    for email, customer in customers.items():
        writer.writerow([
            customer['name'],
            customer['email'],
            customer['score'],
            customer['category'],
            customer['key_info'] or 'N/A',
            customer['raw_input'][:200]
        ])
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-disposition': 'attachment; filename=customers.csv'}
    )

@app.route('/delete_customer/<email>')
def delete_customer(email):
    global customers
    if email in customers:
        del customers[email]
    return redirect('/')

@app.route('/edit_customer/<email>', methods=['GET', 'POST'])
def edit_customer(email):
    global customers
    if request.method == 'POST':
        if email in customers:
            customers[email].update({
                'name': request.form.get('name', customers[email]['name']),
                'email': request.form.get('email', customers[email]['email']),
                'score': int(request.form.get('score', customers[email]['score'])),
                'category': request.form.get('category', customers[email]['category']),
                'key_info': request.form.get('key_info', customers[email]['key_info'])
            })
        return redirect('/')
    if email not in customers:
        return redirect('/')
    customer = customers[email]
    return render_template('edit.html', customer=customer)

if __name__ == "__main__":
    app.run(debug=True)
