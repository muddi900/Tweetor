import sqlite3
import hashlib
import random
import filters
from flask import Flask, Response, render_template, request, redirect, url_for, session, g, jsonify
from flask_session import Session

app = Flask(__name__)
app.secret_key = "super secret key"

# Register the custom filters
app.jinja_env.filters['format_timestamp'] = filters.format_timestamp
app.jinja_env.filters['format_tweet'] = filters.format_tweet

# Set up the session object
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = "tweetor.db"

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS tweets  (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    userHandle TEXT NOT NULL,
    username TEXT NOT NULL,
    hashtag TEXT NOT NULL
)
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        turbo INTEGER,
        handle TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS interests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        hashtag TEXT NOT NULL,
        importance INT NOT NULL
    )
""")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def home() -> Response:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tweets ORDER BY timestamp DESC")
    tweets = cursor.fetchall()
    if "username" in session:
        cursor = db.cursor()
        cursor.execute("SELECT turbo FROM users WHERE handle = ?", (session["handle"], ))
        if cursor.fetchone()["turbo"]==1:
            print("turbo")
            return render_template("home.html", tweets=tweets, loggedIn=("username" in session), turbo=True)
        return render_template("home.html", tweets=tweets, loggedIn=("username" in session), turbo=False)
    return render_template("home.html", tweets=tweets, loggedIn=("username" in session), nitro=False)


@app.route("/submit_tweet", methods=["POST"])
def submit_tweet() -> Response:
    print(request.form)
    content = request.form["content"]
    if len(content) > 10000:
        return redirect("/")
    if "username" not in session:
        return redirect("/")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT turbo FROM users WHERE handle = ?", (session["handle"], ))
    if cursor.fetchone()["turbo"]==0 and (len(content)>280 or "*" in content):
        return redirect("/")
    print(session)
    hashtag = request.form["hashtag"]
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO tweets (content, userHandle, username, hashtag) VALUES (?, ?, ?, ?)",
        (
            content,
            session["handle"],
            session["username"],
            hashtag,
        ),
    )
    db.commit()
    return redirect(url_for("home"))

# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup() -> Response:
    if request.method == "POST":
        username = request.form["username"]
        handle = username
        password = request.form["password"]
        passwordConformation = request.form["passwordConformation"]

        if password != passwordConformation:
            return redirect("/signup")

        conn = get_db()

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

        if len(cursor.fetchall()) != 0:
            handle = f"{username}{len(cursor.fetchall())}"

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password, handle, turbo) VALUES (?, ?, ?, ?)",
            (username, hashed_password, handle, 0),
        )
        conn.commit()
        conn.close()

        session["handle"] = handle
        session["username"] = username
        return redirect("/")
    if "username" in session:
        return redirect("/")
    return render_template("signup.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login() -> Response:
    if request.method == "POST":
        handle = request.form["handle"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE handle = ?", (handle,))

        users = cursor.fetchall()
        if len(users) != 1:
            return redirect("/login")
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        if users[0]["password"] == hashed_password:
            session["handle"] = handle
            session["username"] = users[0]["username"]
        return redirect("/")
    if "username" in session:
        return redirect("/")
    return render_template("login.html")


@app.route('/user/<username>')
def user_profile(username: str) -> Response:
    conn = get_db()
    c = conn.cursor()

    # Get the user's information from the database
    c.execute("SELECT * FROM users WHERE handle=?", (username,))
    user = c.fetchone()

    if user:
        # Get the user's tweets from the database
        c.execute("SELECT * FROM tweets WHERE userHandle=?", (username,))
        tweets = c.fetchall()

        # Render the template with the user's information and tweets
        return render_template("user.html", user=user, tweets=tweets)

    # If the user doesn't exist, display an error message
    return "User not found"

@app.route('/tweets/<tweet_id>')
def singleTweet(tweet_id: str) -> Response:
    conn = get_db()
    c = conn.cursor()

    # Get the tweet's information from the database
    c.execute("SELECT * FROM tweets WHERE id=?", (tweet_id,))
    tweet = c.fetchone()

    if tweet:
        if "username" in session:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM interests WHERE user=? AND hashtag=?", (session["handle"], tweet["hashtag"], ))
            interests = c.fetchall()
            if len(interests) == 0:
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO interests (user, hashtag, importance) VALUES (?, ?, ?)", (
                    session["handle"],
                    tweet["hashtag"],
                    1,
                ))

                conn.commit()
                conn.close()
            else:
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE interests SET importance=? WHERE user=? AND hashtag=?", (
                    interests[0]["importance"]+1,
                    session["handle"],
                    tweet["hashtag"],
                ))
                conn.commit()
                conn.close()

        # Render the template with the tweet's information
        return render_template("tweet.html", tweet=tweet)

    # If the user doesn't exist, display an error message
    return redirect("/")

@app.route('/api/search', methods=["GET"])
def searchAPI() -> Response:
    if request.args.get("query"):
        conn = get_db()
        c = conn.cursor()
        print(request.args.get("query"))

        # Find query
        c.execute("SELECT * FROM tweets WHERE content LIKE ?", (f"%{request.args.get('query')}%", ))
        tweets = [dict(tweet) for tweet in c.fetchall()]
        return jsonify(tweets)
    return "Error Could Not Find Query"

@app.route('/logout', methods=["GET", "POST"])
def logout() -> Response:
    if "username" in session:
        session.pop('handle', None)
        session.pop('username', None)
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=False)