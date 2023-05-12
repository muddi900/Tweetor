from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_session import Session
import sqlite3
import hashlib

app = Flask(__name__)
app.secret_key = "super secret key"

# Set up the session object
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

DATABASE = 'tweeter.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def home():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM tweets ORDER BY timestamp DESC')
    tweets = cursor.fetchall()
    return render_template('home.html', tweets=tweets)

@app.route('/submit_tweet', methods=['POST'])
def submit_tweet():
    content = request.form['content']
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO tweets (content) VALUES (?)', (content,))
    db.commit()
    return redirect(url_for('home'))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        hashed_password = hashlib.sha256(password.encode()).hexdigest()

        conn = sqlite3.connect("tweets.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
        conn.commit()
        conn.close()

        session["username"] = username
        return redirect("/")
    else:
        return render_template("login.html")

if __name__ == '__main__':
    app.run(debug=True)