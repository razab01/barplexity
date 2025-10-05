# Barplexity Chatbot Project

## Overview

This project is a web-based AI chatbot application using Flask, SQLite, and Google Gemini API. It includes user authentication, admin controls, chat sessions, and conversation management.

Users can sign up, login, and interact with a chatbot powered by the Gemini API. Admins can manage users, block/unblock, and delete accounts.

---

## Tech Stack

* **Backend:** Python, Flask, Flask-SQLAlchemy
* **Database:** SQLite
* **API:** Google Gemini API (genai client)
* **Frontend:** HTML, CSS, Bootstrap (basic), templates with Jinja2
* **Other:** Flask-CORS, dotenv

---

## Project Steps & Notes

### Step 1: Project Setup

* Installed Python packages: `Flask`, `Flask-SQLAlchemy`, `Flask-CORS`, `python-dotenv`, `genai`.

* Initialized Flask app and database.

* Loaded environment variables for API keys and secret keys.

* ✅ **Achievement:** Basic Flask app runs successfully.

---

### Step 2: Database Models

* Created `User`, `ChatSession`, and `Chat` models.

* Initial relationship:

  * `User` ↔ `ChatSession`
  * `ChatSession` ↔ `Chat`

* ❌ **Problem:**

  * Initially had duplicate relationships and nullable foreign keys issues.
  * Deleting a user caused `IntegrityError: NOT NULL constraint failed: chat_session.user_id`.

* **Fix:**

  * Added `cascade="all, delete-orphan"` in `User.sessions` and `ChatSession.chats`.
  * Removed conflicting relationships.

* ✅ **Achievement:**

  * Now deleting a user deletes their sessions and all chats automatically.

---

### Step 3: User Authentication

* Implemented signup and login pages.

* Validated user input for empty fields and duplicate emails.

* Session management via `Flask.session`.

* ❌ **Problem:**

  * Initial versions did not handle banned or blocked users properly.

* **Fix:**

  * Added `is_blocked` and `is_banned` flags.
  * Updated login route to check these flags before allowing login.

* ✅ **Achievement:**

  * Users can now be blocked/banned safely, and login reflects that.

---

### Step 4: Admin Dashboard

* Added an admin-only dashboard.

* Features:

  * View all users (excluding admin)
  * Block/Unblock users
  * Delete users (with cascading delete)

* ✅ **Achievement:**

  * Admin can now manage users fully.
  * Cascading deletes prevent database errors.

---

### Step 5: Chatbot & Chat Sessions

* Users can start chat sessions and chat with the Gemini API.

* Each session stores all messages in `Chat` table.

* Session summaries update automatically based on first message.

* ❌ **Problem:**

  * Initially creating a new session caused `user_id=None` for sessions → `IntegrityError`.

* **Fix:**

  * Ensure `ChatSession` always created with `user_id=user.id`.
  * Removed unnecessary relationship that conflicted with cascading delete.

* ✅ **Achievement:**

  * Users can create multiple chat sessions, and sessions persist correctly.

---

### Step 6: Chatbot API & Real-time Messaging

* Implemented `/chatbot-api` route for AJAX messaging.

* Conversations are constructed from previous messages and sent to Gemini API.

* ✅ **Achievement:**

  * Chatbot can respond to messages in both web interface and API calls.

---

### Step 7: Logout & Session Management

* Added logout route to clear session variables.
* Ensures unauthorized access is prevented for both users and admins.

---

### Step 8: Testing & Debugging

* Tested user signup/login, chat session creation, admin actions, cascading deletes.
* Fixed multiple `IntegrityError` issues caused by incorrect relationships.

---

## Key Learnings

1. Proper **database relationships** and `cascade="all, delete-orphan"` prevent integrity errors.
2. Session and authentication management are crucial for security.
3. Always check for nullable fields before committing to the database.
4. Admin and user functionalities need proper route access checks.

---

### Future Improvements

* Implement **password hashing** for secure login.
* Add **frontend improvements** with Bootstrap/JS.
* Add **chat history export** for users.
* Deploy the app on **Heroku or a cloud server**.

---

## How to Run

1. Clone the repository

```bash
git clone <repo-url>
cd <repo-folder>
```

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Create `.env` file:

```
FLASK_SECRET_KEY=your_secret_key
GEMINI_API_KEY=your_gemini_api_key
```

4. Run the app

```bash
python main.py
```

5. Open browser: `http://127.0.0.1:5000/`

---

This README documents all challenges faced, how they were fixed, and the key features implemented.
