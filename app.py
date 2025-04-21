from flask import Flask, request, jsonify, render_template
from groq import Groq

app = Flask(__name__)

# Initialize Groq client
client = Groq(api_key="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")

# Set the bot's name
BOT_NAME = "Tabib"

# Store user session data
user_sessions = {}

# Medical questioning pattern
MEDICAL_QUESTIONS = [
    "Where exactly is the problem located? (e.g., left temple, lower back)",
    "How would you describe it? (e.g., throbbing pain, sharp pain, dull ache)",
    "How long have you had this symptom?",
    "Are you experiencing any other symptoms along with this?"
]

# List of common symptom keywords
SYMPTOM_KEYWORDS = [
    'fever', 'headache', 'pain', 'ache', 'nausea', 'dizziness', 
    'cough', 'sore throat', 'rash', 'fatigue', 'vomiting', 
    'diarrhea', 'shortness of breath', 'chest pain'
]

def query_groq(prompt, context=None):
    """Query the Groq API with medical context"""
    try:
        messages = [
            {
                "role": "system",
                "content": f"""You are {BOT_NAME}, a medical assistant. Follow these rules:
1. Provide general medical information about symptoms only
2. Always recommend consulting a doctor
3. Use simple language a patient can understand"""
            }
        ]
        
        if context:
            messages.append({"role": "assistant", "content": context})
            
        messages.append({"role": "user", "content": prompt})
        
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama3-8b-8192",
            temperature=0.3,
            max_tokens=1024
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        return f"Sorry, I encountered an error: {str(e)}"

def contains_symptom(text):
    """Check if the text contains any symptom keywords"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in SYMPTOM_KEYWORDS)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_response", methods=["POST"])
def get_response():
    user_message = request.form.get("user_message")
    session_id = request.remote_addr
    
    # Initialize session if not exists
    if session_id not in user_sessions:
        user_sessions[session_id] = {
            "in_question_flow": False,
            "current_question": 0,
            "answers": []
        }

    session = user_sessions[session_id]

    # Handle greetings ("hi" or "hello")
    if user_message.lower() in ["hi", "hello"]:
        # Reset session
        user_sessions[session_id] = {
            "in_question_flow": False,
            "current_question": 0,
            "answers": []
        }
        welcome_msg = f"🩺 Hello! I'm {BOT_NAME}, your medical assistant. Please describe your symptoms (e.g., 'I have a fever')."
        return jsonify({
            "user_message": user_message,  # Show user's input
            "bot_reply": welcome_msg,
            "clear_chat": False
        })

    # Start medical flow only if symptom is mentioned
    if not session["in_question_flow"] and contains_symptom(user_message):
        # Reset session
        user_sessions[session_id] = {
            "in_question_flow": True,
            "current_question": 0,
            "answers": [user_message]
        }
        # Start with first medical question
        return jsonify({
            "user_message": user_message,  # Show user's input
            "bot_reply": MEDICAL_QUESTIONS[0],
            "clear_chat": False
        })

    # If in questioning flow
    if session["in_question_flow"]:
        # Store the answer
        session["answers"].append(user_message)
        
        # If more questions remain
        if session["current_question"] < len(MEDICAL_QUESTIONS) - 1:
            session["current_question"] += 1
            next_question = MEDICAL_QUESTIONS[session["current_question"]]
            return jsonify({
                "user_message": user_message,  # Show user's input
                "bot_reply": next_question,
                "clear_chat": False
            })
        else:
            # All questions answered - generate summary
            context = f"Patient reported:\n" \
                     f"- Main symptom: {session['answers'][0]}\n" \
                     f"- Location: {session['answers'][1]}\n" \
                     f"- Description: {session['answers'][2]}\n" \
                     f"- Duration: {session['answers'][3]}\n" \
                     f"- Other symptoms: {session['answers'][4] if len(session['answers']) > 4 else 'None'}"
            
            # Get medical information
            response = query_groq("Based on these symptoms, what could this indicate?", context)
            
            # Reset session
            session["in_question_flow"] = False
            session["current_question"] = 0
            session["answers"] = []
            
            return jsonify({
                "user_message": user_message,  # Show user's input
                "bot_reply": response,
                "clear_chat": False
            })

    # Default response for all other inputs
    return jsonify({
        "user_message": user_message,  # Show user's input
        "bot_reply": "Please describe your symptoms (e.g., 'I have a fever') or type 'hi' to begin.",
        "clear_chat": False
    })

if __name__ == "__main__":
    app.run(debug=True)
