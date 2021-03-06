import requests

from decouple import config
from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from password import Password
from utils import bad_cred, check_password, set_password
app = Flask(__name__)

# Check for environment variable
if not config("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = config("SECRET_KEY")

# Set up database
engine = create_engine(config("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
def index():
    if session.get("username"):
        return redirect(url_for('search'))
    return redirect(url_for('login'))


@app.route("/signup", methods=['GET', 'POST'])
def signup(message=""):
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # return an error message if either username or password isn't long enough
        if bad_cred(username, password):
            message = "Username and password can't match and must be longer than 3 characters"
            return render_template("signup.html", destination="signup", message=message, other="login")

        if db.execute("SELECT username from users WHERE username = :username", {'username': username}).rowcount > 0:
            message = "Username is already taken. If it's yours please go to login page"

        if message:
            return render_template("signup.html", destination="signup", message=message, other="login")
        # Hash and salt password for database
        password_object = Password(password)
        password = password_object.secret_password
        db.execute("INSERT into users (username, password) VALUES (:username, :password)", {
                   "username": username, "password": password})
        db.commit()
        message = "Registration Successful! Login Below."
        return render_template("login.html", destination="login", link=url_for("signup"), message=message)

    return render_template("signup.html", destination="signup", link="login")


@app.route("/login", methods=['GET', 'POST'])
def login(message=""):
    if request.method == "POST":
        # Verify user exists
        username = request.form.get("username")
        password = set_password(request.form.get("password"))
        # MAKE SURE USERNAME IS IN DATABASE
        if db.execute("SELECT * FROM users WHERE username = :username", {"username": username}).rowcount > 0:
            # MAKE SURE PASSWORD MATCHES
            user = db.execute(
                "SELECT * FROM users WHERE username = :username", {"username": username}).fetchone()
            password_object = Password(user.password)
            if password_object.check_password(user.password):
                session["username"] = username
                return redirect(url_for('index'))
        message = "Invalid credentials"
    return render_template("login.html", destination="login", link=url_for("signup"), guest=url_for("guest_login"), message=message)

@app.route("/guest", methods=['GET','POST'])
def guest_login():
    session["username"] = "Guest"
    return redirect(url_for('index'))

@app.route("/logout", methods=['GET'])
def logout():
    session['username'] = ''
    return render_template("logout.html")


@app.route("/search", methods=['GET'])
def search(results=[], num_results=None):
    # Check logged in
    if not session.get("username"):
        return redirect(url_for('login'))
    # if a search was performed
    if request.args.get("type") and request.args.get("q"):
        stype = request.args.get("type")
        q = request.args.get("q")
        query = f"%{q}%"

        # if any results are found, store them in the results variable
        if db.execute(f"SELECT * FROM books LEFT JOIN reviews ON books.isbn = reviews.book_isbn WHERE {stype} iLIKE :q", {"q": query}).rowcount > 0:
            results = db.execute(
                f"SELECT * FROM books LEFT JOIN reviews ON books.isbn = reviews.book_isbn  WHERE {stype} iLIKE :q", {"q": query}).fetchall()
            if (len(results)) == 1:
                num_results = f"{len(results)} book found with {stype} similar to '{q}'"
            else:
                num_results = f"{len(results)} book found with {stype} similar to '{q}'"
        else:
            num_results = f"No books found with {stype} similar to {q}"
    return render_template("search.html", num_results=num_results, results=results)


@app.route("/search/<string:isbn>", methods=["GET", "POST"])
def result(isbn):
    # Check logged in
    if not session.get("username"):
        return redirect(url_for('login'))

    if request.method == "POST":
        # if user hasn't reviewed book yet
        if db.execute("SELECT * FROM reviews WHERE book_isbn = :isbn AND user_id IN (SELECT id FROM users WHERE username = :username)", {"isbn": isbn, "username": session['username']}).rowcount == 0:
            rating = request.form.get("rating")
            comment = request.form.get("comment")

            user = db.execute("SELECT * from users WHERE username = :username",
                              {"username": session['username']}).fetchone()
            user_id = user.id

            db.execute("INSERT INTO reviews (book_isbn, rating, comment, user_id) VALUES (:isbn, :rating, :comment, :user_id)",
                       {"isbn": isbn, "rating": rating, "comment": comment, "user_id": user_id})
            db.commit()

    if db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount == 0:
        return render_template("search.html")

    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                      {"isbn": isbn}).fetchone()
    # Get all the reviews for the book. Join the users table as well so we can stick names on each review.
    reviews = db.execute(
        "SELECT * FROM reviews LEFT JOIN users ON users.id = reviews.user_id WHERE book_isbn = :isbn AND comment IS NOT NULL ", {"isbn": isbn}).fetchall()

    # Get reviews from good reads
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": config("GOODREADS_APIKEY"), "isbns": isbn})
    goodreads = res.json()
    gr_count = goodreads['books'][0]['work_ratings_count']
    gr_score = goodreads['books'][0]['average_rating']

    # Get summary from google books
    res = requests.get(
        f"https://www.googleapis.com/books/v1/volumes?q=title={book.title}&author={book.author}key={config('GOOGLE_APIKEY')}")
    google = res.json()

    description = "No description found"
    image = ""
    # check at most 5 items to find the correct book
    for item in range(5):
        if(google['items'][item]['volumeInfo']['title'] == book.title and book.author in google['items'][item]['volumeInfo']['authors']):
            try:
                description = google['items'][item]['volumeInfo']['description']
            except:
                description = f"No description provided for {book.title}"
            image = google['items'][item]['volumeInfo']['imageLinks']['thumbnail']
            break

    # show reviewed page if user alerady reaviewed the book
    if db.execute("SELECT * FROM reviews WHERE book_isbn = :isbn AND user_id IN (SELECT id FROM users WHERE username = :username)", {"isbn": isbn, "username": session['username']}).rowcount == 0:
        reviewed = False
    else:
        reviewed = True
    return render_template("book.html", book=book, reviews=reviews, reviewed=reviewed, gr_count=gr_count, gr_score=gr_score,
                           description=description, image=image)


@app.route("/api/<string:isbn>", methods=["GET"])
def api(isbn):
    if db.execute("SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}).rowcount == 0:
        return render_template("404.html")
    book = db.execute("SELECT * FROM books WHERE isbn = :isbn",
                      {"isbn": isbn}).fetchone()

    # Get reviews from good reads
    res = requests.get("https://www.goodreads.com/book/review_counts.json",
                       params={"key": config("GOODREADS_APIKEY"), "isbns": isbn})
    goodreads = res.json()
    gr_count = goodreads['books'][0]['work_ratings_count']
    gr_score = goodreads['books'][0]['average_rating']

    json = {
        "title": book.title,
        "author": book.author,
        "year": book.year,
        "isbn": book.isbn,
        "review_count": gr_count,
        "average_score": gr_score
    }
    return jsonify(json)


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404
