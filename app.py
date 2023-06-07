import sqlite3
import hashlib
import random
import string
import filters
from flask import Flask, Response, render_template, request, redirect, url_for, session, g, jsonify
from flask_cors import CORS, cross_origin
from flask_session import Session

app = Flask(__name__)
app.secret_key = "super secret key"
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

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
        turbo INTEGER DEFAULT 0,
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

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        origin TEXT NOT NULL,
        content TEXT NOT NULL,
        viewed INTEGER DEFAULT 0
    )
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        userHandle TEXT NOT NULL,
        tweetId INTEGER NOT NULL
    )
""")

sqlite3.connect(DATABASE).cursor().execute(
    """
    CREATE TABLE IF NOT EXISTS follows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        followerHandle TEXT NOT NULL,
        followingHandle TEXT NOT NULL
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
            return render_template("home.html", tweets=tweets, loggedIn=("username" in session), turbo=True)
        return render_template("home.html", tweets=tweets, loggedIn=("username" in session), turbo=False)
    return render_template("home.html", tweets=tweets, loggedIn=("username" in session), nitro=False)


@app.route("/submit_tweet", methods=["POST"])
def submit_tweet() -> Response:
    print(request.form)
    content = request.form["content"]
    if len(content) > 10000:
        return render_template("error.html", error="Message was too long.")
    if "username" not in session:
        return render_template("error.html", error="You are not logged in.")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT turbo FROM users WHERE handle = ?", (session["handle"], ))
    if cursor.fetchone()["turbo"]==0 and (len(content)>280 or "*" in content or "_" in content):
        return render_template("error.html", error="You do not have tweetor turbo.")
    print(session)
    hashtag = request.form["hashtag"]
    if "username" not in session:
        return redirect("/signup")

    tweet_content = request.form["content"]

    if is_profanity(tweet_content+hashtag) != []:
        for word in is_profanity(tweet_content+hashtag):
            print(word)
            tweet_content = tweet_content.replace(word[0], word[1])
            hashtag = hashtag.replace(word[0], word[1])

    if "ur mom" in tweet_content:
        return render_template("error.html", error="Message contained ur mom tweetor servers were overloaded. Could not handle tweet.")

    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO tweets (username, content, userHandle, hashtag) VALUES (?, ?, ?, ?)", (session["username"], tweet_content, session["handle"], hashtag, ))
    db.commit()
    return redirect(url_for("home"))

#signup route
@app.route("/signup", methods=["GET", "POST"])
def signup() -> Response:
    error = None
    correct_captcha = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.digits, k=5))
    if request.method == "POST":
        username = request.form["username"]
        handle = username
        password = request.form["password"]
        passwordConformation = request.form["passwordConformation"]
        user_captcha_input = request.form["input"]
        correct_captcha = request.form["correct_captcha"]

        if user_captcha_input != correct_captcha:
            return redirect("/signup")

        if password != passwordConformation:
            return redirect("/signup")

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

        if len(cursor.fetchall()) != 0:
            handle = f"{username}{len(cursor.fetchall())}"

        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        cursor.execute(
            "INSERT INTO users (username, password, handle, turbo) VALUES (?, ?, ?, ?)",
            (username, hashed_password, handle, 0),
        )
        db.commit()
        db.close()

        session["handle"] = handle
        session["username"] = username
        return redirect("/")

    if "username" in session:
        return redirect("/")
    return render_template("signup.html", error=error, correct_captcha=correct_captcha)


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

@app.route('/notifications')
def notifications() -> Response:
    # Check if user is logged in
    if "username" not in session:
        return render_template("error.html", error="You were not logged in.")
    conn = get_db()
    c = conn.cursor()

    # Get the notifications
    c.execute("SELECT * FROM notifications WHERE user=?", (session["userHandle"], ))
    notices = c.fetchall()

    return render_template("notifications.html", notices=notices)


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
        return render_template("tweet.html", tweet=tweet, loggedIn=("username" in session))

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
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM tweets ORDER BY timestamp DESC")
    return jsonify([dict(tweet) for tweet in cursor.fetchall()])

@app.route('/search', methods=["GET"])
def search() -> Response:
    if request.args.get("query"):
        conn = get_db()
        c = conn.cursor()
        print(request.args.get("query"))

        # Find query
        c.execute("SELECT * FROM tweets WHERE content LIKE ? OR hashtag LIKE ?", (f"%{request.args.get('query')}%", f"%{request.args.get('query')}%", ))
        tweets = [dict(tweet) for tweet in c.fetchall()]
        return render_template("search.html", tweets=tweets, loggedIn=("username" in session))
    return render_template("search.html", tweets=False, loggedIn=("username" in session))

@app.route('/logout', methods=["GET", "POST"])
def logout() -> Response:
    if "username" in session:
        session.pop('handle', None)
        session.pop('username', None)
    return redirect("/")

# Profanity filter
profanity_words = [("arse", "butt"), ("arsehead", "butt"), ("arsehole", "butt"), ("ass", "butt"), ("asshole", "butt"), ("bastard", "******"), ("bitch", "******"), ("bloody", "******"), ("bollocks", "******"), ("bugger", "bug"), ("bullshit", "cow poop"), ("bs", "cow poop"), ("crap", "treasure"), ("cunt", "******"), ("damn", "aadam nason"), ("dick", "detective"), ("dyke", "********"), ("frigger", "69"), ("frick", "69"), ("fuck", "69"), ("hell", "heaven"), ("kike", "******"), ("nigra", "******"), ("nigga", "******"), ("piss", "******"), ("prick", "******"), ("shit", "poo"), ("slut", "******"), ("son of a", "******"), ("spastic", "poo"), ("turd", "poop"), ("twat", "nonoword"), ("wanker", "that's illegal")]

def is_profanity(text: str):
    words = []
    for word in profanity_words:
        if word[0] in text.lower():
            print(word)
            words.append((word[0], word[1]))
    return words

@app.route("/user/<username>")
def user_profile(username: str) -> Response:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        return redirect("/home")

    cursor.execute("SELECT * FROM tweets WHERE userHandle = ?", (username, ))
    tweets = cursor.fetchall()

    is_following = False
    if "username" in session:
        logged_in_username = session["username"]
        cursor.execute("SELECT * FROM follows WHERE followerHandle = ? AND followingHandle = ?", (logged_in_username, user["handle"]))
        is_following = cursor.fetchone() is not None

    return render_template("user.html", user=user, loggedIn=("username" in session), tweets=tweets, is_following=is_following)


@app.route("/like_tweet", methods=["POST"])
def like_tweet():
    tweet_id = request.form["tweetId"]
    user_handle = session["handle"]

    db = get_db()
    cursor = db.cursor()

    # Check if the like already exists
    cursor.execute("SELECT * FROM likes WHERE userHandle = ? AND tweetId = ?", (user_handle, tweet_id))
    existing_like = cursor.fetchone()

    if existing_like:
        # Unlike the tweet
        cursor.execute("DELETE FROM likes WHERE id = ?", (existing_like["id"],))
    else:
        # Like the tweet
        cursor.execute("INSERT INTO likes (userHandle, tweetId) VALUES (?, ?)", (user_handle, tweet_id))

    db.commit()

    return jsonify({"status": "success"})

@app.route("/follow_user", methods=["POST"])
def follow_user():
    try:
        if "followingUsername" not in request.form or "username" not in session:
            return render_template("error.html", error="You are not logged in.")
        following_username = request.form["followingUsername"]
        follower_username = session["username"]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("SELECT * FROM users WHERE handle=?", (following_username, ))

        if cursor.fetchone() is None:
            return render_template("error.html", error="That user doesn't exist.")

        # Check if the user is already following
        cursor.execute("SELECT * FROM follows WHERE followerHandle = ? AND followingHandle = ?", (follower_username, following_username))
        existing_follow = cursor.fetchone()

        if existing_follow:
            # Unfollow the user
            cursor.execute("DELETE FROM follows WHERE id = ?", (existing_follow["id"],))
        else:
            # Follow the user
            cursor.execute("INSERT INTO follows (followerHandle, followingHandle) VALUES (?, ?)", (follower_username, following_username))

        db.commit()

        return redirect(f'/user/{following_username}')
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_like_count(tweet_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM likes WHERE tweetId = ?", (tweet_id,))
    return cursor.fetchone()["count"]

def get_follower_count(user_handle):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM follows WHERE followingHandle = ?", (user_handle,))
    return cursor.fetchone()["count"]


if __name__ == "__main__":
    app.run(debug=False)