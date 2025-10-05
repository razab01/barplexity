from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from dotenv import load_dotenv
import os
from google import genai  # Gemini API client

# ------------------- Setup -------------------
load_dotenv()
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
GEMINI_API_KEY = os.getenv("gemini_api_key")
GEMINI_MODEL = "gemini-2.5-flash"

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)
CORS(app)

# ------------------- Models -------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    is_banned = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag
    sessions = db.relationship(
        "ChatSession",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    summary = db.Column(db.String(200), default="New Chat")
    timestamp = db.Column(db.DateTime, default=db.func.now())

    chats = db.relationship("Chat", backref="session", lazy=True, cascade="all, delete-orphan")



class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("chat_session.id"), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.now())

with app.app_context():
    db.create_all()
    # Ensure admin user exists
    admin_user = User.query.filter_by(email="admin@barplexity.com").first()
    if not admin_user:
        admin_user = User(
            name="Admin",
            email="admin@barplexity.com",
            password="12345678",  # Change or hash in production
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()

# ------------------- Gemini API -------------------
client = genai.Client(api_key=GEMINI_API_KEY)

def query_gemini_api(prompt):
    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return response.text
    except Exception as e:
        return f"Error: {e}"

# ------------------- Routes -------------------
@app.route("/")
def home():
    return render_template("barplexity.html")

@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name")
    email = request.form.get("email")
    password = request.form.get("password")

    if not name or not email or not password:
        flash("All fields are required!", "error")
        return redirect(url_for("home"))

    if User.query.filter_by(email=email).first():
        flash("Email already registered!", "error")
        return redirect(url_for("login_page"))

    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    flash("Signup successful! Please login.", "success")
    return redirect(url_for("login_page"))

@app.route("/signin", methods=["POST"])
def signin():
    email = request.form.get("email")
    password = request.form.get("password")
    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Invalid credentials!", "error")
        return redirect(url_for("login_page"))

    if user.is_banned:
        flash("This email is banned. Contact admin.", "error")
        return redirect(url_for("home"))

    if user.is_blocked:
        flash("You are blocked. Contact admin.", "error")
        return redirect(url_for("login_page"))

    if user.password == password:
        session["user_id"] = user.id
        session["user"] = user.name
        if user.is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("chatbot"))
    else:
        flash("Invalid credentials!", "error")
        return redirect(url_for("home"))

# ------------------- Admin Routes -------------------
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        flash("Access denied!", "error")
        return redirect(url_for("home"))

    user = User.query.get(session["user_id"])
    if not user or not user.is_admin:
        flash("Access denied!", "error")
        return redirect(url_for("home"))

    users = User.query.filter(User.email != "admin@barplexity.com").all()
    return render_template("admin.html", users=users)

@app.route("/admin/block/<int:user_id>")
def block_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_blocked = not user.is_blocked
        db.session.commit()
        flash(f"{user.name} has been {'blocked' if user.is_blocked else 'unblocked'}!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/delete/<int:user_id>")
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        user.is_banned = True  # Ban future login
        db.session.delete(user)  # cascades to sessions and chats
        db.session.commit()
        flash(f"{user.name} has been deleted and banned!", "success")
    return redirect(url_for("admin_dashboard"))

# ------------------- Chatbot Routes -------------------
@app.route("/chatbot", methods=["GET", "POST"])
def chatbot():
    if "user" not in session:
        return redirect(url_for("home"))

    user = User.query.get(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("home"))

    # fetch sessions but only those which have messages
    sessions_with_msgs = (
        ChatSession.query.filter_by(user_id=user.id)
        .join(Chat)
        .group_by(ChatSession.id)
        .order_by(ChatSession.timestamp.desc())
        .all()
    )

    # summaries for sidebar
    summaries = []
    for s in sessions_with_msgs:
        first_msg = s.chats[0].question[:30] if s.chats else "New Chat"
        summaries.append({"id": s.id, "summary": first_msg})

    # current session
    session_id = request.args.get("session_id")
    if session_id:
        current_session = ChatSession.query.get(int(session_id))
    else:
        current_session = ChatSession(user_id=user.id)
        db.session.add(current_session)
        db.session.commit()

    # Handle user message
    if request.method == "POST":
        user_message = request.form.get("message")
        # Build full conversation
        previous_chats = Chat.query.filter_by(session_id=current_session.id).order_by(Chat.timestamp.asc()).all()
        prompt = ""
        for chat in previous_chats:
            prompt += f"User: {chat.question}\nBot: {chat.answer}\n"
        prompt += f"User: {user_message}\nBot:"

        bot_reply = query_gemini_api(prompt)

        chat_msg = Chat(session_id=current_session.id, question=user_message, answer=bot_reply)
        db.session.add(chat_msg)

        if current_session.summary == "New Chat":
            current_session.summary = user_message[:50]

        db.session.commit()

    messages = Chat.query.filter_by(session_id=current_session.id).order_by(Chat.timestamp.asc()).all()

    return render_template(
        "chatbot.html",
        sessions=summaries,
        selected_session=current_session.id,
        messages=messages,
        user=session["user"]
    )

@app.route("/chatbot-api", methods=["POST"])
def chatbot_api():
    if "user" not in session:
        return jsonify({"reply": "Please login first!"})

    data = request.get_json()
    user_message = data.get("message")
    session_id = data.get("session_id")

    chat_session = ChatSession.query.get(session_id)
    if not chat_session:
        return jsonify({"reply": "Chat session not found!"})

    previous_chats = Chat.query.filter_by(session_id=chat_session.id).order_by(Chat.timestamp.asc()).all()
    prompt = ""
    for chat in previous_chats:
        prompt += f"User: {chat.question}\nBot: {chat.answer}\n"
    prompt += f"User: {user_message}\nBot:"

    bot_reply = query_gemini_api(prompt)
    chat_msg = Chat(session_id=chat_session.id, question=user_message, answer=bot_reply)
    db.session.add(chat_msg)
    db.session.commit()

    return jsonify({"reply": bot_reply})

@app.route("/delete-chat/<int:session_id>", methods=["DELETE"])
def delete_chat(session_id):
    if "user" not in session:
        return {"status": "error", "msg": "Unauthorized"}, 403

    chat_session = ChatSession.query.get(session_id)
    if chat_session and chat_session.user_id == session["user_id"]:
        db.session.delete(chat_session)
        db.session.commit()
        return {"status": "success"}, 200
    return {"status": "error", "msg": "Chat not found"}, 404

# ------------------- Logout -------------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login_page"))

# ------------------- Run -------------------
if __name__ == "__main__":
    app.run(debug=True)
