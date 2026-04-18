import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from groq import Groq
from supabase import create_client

# ------------------ CONFIG ------------------

app = Flask(__name__)
CORS(app, origins=["https://codedevora.vercel.app/"])  # You can restrict later to your Vercel URL

# Environment variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase credentials missing")

# Clients
groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ------------------ ROUTES ------------------

@app.route("/")
def home():
    return jsonify({"message": "AI Rescue Backend Running 🚀"})


# 🔹 PROCESS INPUT (AI + STORE)
@app.route("/process", methods=["POST"])
def process():
    try:
        data = request.get_json()
        user_input = data.get("message")

        if not user_input:
            return jsonify({"error": "Message is required"}), 400

        # AI Prompt
        prompt = f"""
        You are an API. Convert the message into STRICT JSON.
        
        Format:
        {{
          "type": "Need or Resource",
          "category": "",
          "urgency": "Low/Medium/High",
          "summary": "",
          "location": "",
          "contact": ""
        }}
        
        ONLY return JSON. No explanation.
        
        Message:
        {user_input}
        """

        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
        )

        ai_output = response.choices[0].message.content.strip()

        try:
            parsed = json.loads(ai_output)
        except json.JSONDecodeError:
            return jsonify({
                "error": "AI returned invalid JSON",
                "raw": ai_output
            }), 500

        # Store in DB
        insert_data = {
            "type": parsed.get("type"),
            "category": parsed.get("category"),
            "urgency": parsed.get("urgency"),
            "summary": parsed.get("summary"),
            "location": parsed.get("location"),
            "contact": parsed.get("contact"),
        }

        db_response = supabase.table("requests").insert(insert_data).execute()

        return jsonify({
            "ai_data": parsed,
            "db_data": db_response.data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🔹 GET MATCHES
@app.route("/match/<category>", methods=["GET"])
def match(category):
    try:
        result = supabase.table("requests") \
            .select("*") \
            .eq("type", "Resource") \
            .eq("category", category) \
            .execute()

        return jsonify({
            "matches": result.data
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 🔹 GET ALL REQUESTS (DEBUG)
@app.route("/requests", methods=["GET"])
def get_requests():
    try:
        result = supabase.table("requests").select("*").execute()
        return jsonify(result.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------ RUN ------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
