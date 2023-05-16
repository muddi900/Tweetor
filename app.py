import sqlite3
import hashlib
import random
from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_session import Session

app = Flask(__name__)
app.secret_key = "super secret key"

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
    user TEXT NOT NULL,
    hashtag TEXT NOT NULL
)
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL
    )
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS interests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL UNIQUE,
        hashtag TEXT NOT NULL,
        importance INT NOT NULL
    )
""")

# Generate a verification code
def generate_code():
    return str(random.randint(100000, 999999))


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
def home():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tweets ORDER BY timestamp DESC")
    tweets = cursor.fetchall()
    return render_template("home.html", tweets=tweets, loggedIn=("username" in session))


@app.route("/submit_tweet", methods=["POST"])
def submit_tweet():
    content = request.form["content"]
    hashtag = request.form["hashtag"]
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO tweets (content, user, hashtag) VALUES (?, ?, ?)",
        (
            content,
            session["username"],
            hashtag,
        ),
    )
    db.commit()
    return redirect(url_for("home"))

# Signup route
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        passwordConformation = request.form["passwordConformation"]

        if password != passwordConformation:
            return redirect("/signup")

        conn = get_db()

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

        if len(cursor.fetchall()) != 0:
            return redirect("/signup")

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        c = conn.cursor()
        c.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password),
        )
        conn.commit()
        conn.close()

        session["username"] = username
        return redirect("/")
    if "username" in session:
        return redirect("/")
    return render_template("signup.html")

# Login route
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))

        passwords = cursor.fetchall()
        if len(passwords) == 0:
            return redirect("/login")
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        # print((passwords[0][0]) == (hashed_password))
        if passwords[0][0] == hashed_password:
            session["username"] = username
            print("logged in")
        return redirect("/")
    if "username" in session:
        return redirect("/")
    return render_template("login.html")


@app.route('/user/<username>')
def user_profile(username):
    conn = get_db()
    c = conn.cursor()

    # Get the user's information from the database
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    user = c.fetchone()

    if user:
        # Get the user's tweets from the database
        c.execute("SELECT * FROM tweets WHERE user=?", (username,))
        tweets = c.fetchall()
        print(tweets[0])

        # Render the template with the user's information and tweets
        return render_template("user.html", user=user, tweets=tweets)

    # If the user doesn't exist, display an error message
    return "User not found"

@app.route('/tweets/<tweetId>')
def singleTweet(tweetId):
    conn = get_db()
    c = conn.cursor()

    # Get the tweet's information from the database
    c.execute("SELECT hashtag FROM tweets WHERE id=?", (tweetId,))
    tweet = c.fetchone()

    if tweet:
        if "username" in session:
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM interests WHERE user=? AND hashtag=?", (session["username"], tweet, ))
            interests = c.fetchall()
            if len(interests) == 0:
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO interests (user, hashtag, importance) VALUES (?, ?, ?)", (
                    session["username"],
                    tweet,
                    1,
                ))
                
                conn.commit()
                conn.close()
            else:
                conn = get_db()
                c = conn.cursor()
                c.execute("UPDATE interests SET importance=? WHERE user=? AND hashtag=?", (
                    interests[0].importance+1,
                    session["username"],
                    tweet,
                ))
                conn.commit()
                conn.close()
                
        # Render the template with the tweet's information
        return render_template("tweet.html", tweet=tweet)

    # If the user doesn't exist, display an error message
    return "Tweet not found"

@app.route('/logout', methods=["GET", "POST"])
def logout():
    if "username" in session:
        del session["username"]
    return redirect("/")

if __name__ == "__main__":
    app.run(debug=False)
