import os
import requests

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///anime.db")

statuses = ["Watching", "Completed", "My_favorites"]

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


@app.route("/", methods=["POST", "GET"])
def index():
    folders = []
    animes = []
    folder_id = None
    if session.get("user_id"):
        # give user an oportunity to chose one of his/her folders
        folders = db.execute("SELECT * FROM folders WHERE user_id = ?", session["user_id"])
        folder_id = request.args.get("folder_id")
        if request.method == "POST":
            status = request.form.get("status")
            rating = request.form.get("rating")
            anime_id = request.form.get("anime_id")
            if status is not None:
                db.execute("UPDATE user_anime_infolder SET status = ? WHERE user_id = ? AND anime_id = ?", status, session["user_id"], anime_id)
            if rating is not None:
                db.execute("UPDATE user_anime_infolder SET rating = ? WHERE user_id = ? AND anime_id = ?", rating, session["user_id"], anime_id)
        if folder_id:
            animes = db.execute("SELECT Titels.id, Titels.Title, Titels.image_url, user_anime_infolder.status, user_anime_infolder.rating FROM Titels JOIN user_anime_infolder ON user_anime_infolder.anime_id = Titels.id WHERE user_anime_infolder.user_id = ? AND user_anime_infolder.folder_id = ?", session["user_id"], folder_id)
        else:
            animes = db.execute("SELECT DISTINCT Titels.id, Titels.Title, Titels.image_url, user_anime_infolder.status, user_anime_infolder.rating FROM Titels JOIN user_anime_infolder ON user_anime_infolder.anime_id = Titels.id WHERE user_anime_infolder.user_id = ?", session["user_id"])
    return render_template("index.html", folders=folders, animes = animes, selected_folder=folder_id, statuses = statuses)


@app.route("/register", methods=["POST", "GET"])
def register():
    if request.method == "POST":
        # Check that user provide all data and password and confirmation are simalar
        if not request.form.get("username"):
            flash("must provide username")
            return redirect("/register")
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/register")
        elif not request.form.get("confirmation"):
            flash("must provide confirmation")
            return redirect("/register")
        elif (request.form.get("password") != request.form.get("confirmation")):
            flash("must provide same password and confirmation")
            return redirect("/register")
        # check if username already exist
        rows = db.execute("SELECT * FROM users WHERE user_name = ? ", request.form.get("username"))
        if (len(rows) != 0):
            flash("This user already exist")
            return redirect("/register")
        # save new user data
        username = request.form.get("username")
        hashed_password = generate_password_hash(request.form.get("password"))
        user_id = db.execute("INSERT INTO users (user_name, hash) VALUES (?, ?)",
                             username, hashed_password)
        # login
        session["user_id"] = user_id
        return redirect("/")
    return render_template("register.html")


@app.route("/login", methods=["POST", "GET"])
def login():
    session.clear()
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            flash("must provide username")
            return redirect("/login")
        # Ensure password was submitted
        elif not request.form.get("password"):
            flash("must provide password")
            return redirect("/login")
        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE user_name = ?", request.form.get("username")
        )
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            flash("invalid username and/or password")
            return redirect("/login")
        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        # Redirect user to home page
        return redirect("/")
        # User reached route via GET (as by clicking a link or via redirect
    return render_template("login.html")


@app.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/search", methods=["GET", "POST"])
def search():
    if request.method == "POST":
        anime_title = request.form.get("anime_title")
        year = request.form.get("year")
        season = request.form.get("season")
        sorted_by = request.form.get("sorted_by")
        order = request.form.get("order")

        query = "SELECT * FROM titels WHERE 1=1"
        parameters = []
        # add parameters to request if them exist
        if anime_title:
            query += " AND LOWER(Title) LIKE LOWER(?)"
            parameters.append("%" + anime_title + "%")
        if year:
            query += " AND year = ?"
            parameters.append(int(year))
        if season:
            query += " AND season = ?"
            parameters.append(season)

        sort_columns = {
            "rating": "score",
            "title": "Title",
            "year": "year"
        }
        if sorted_by in sort_columns:
            column = sort_columns[sorted_by]
            # basicly sorted by desc
            if order == "asc":
                query += f" ORDER BY {column} ASC"
            else:
                query += f" ORDER BY {column} DESC"
        else:
            query += " ORDER BY score DESC" 

        query += " LIMIT 50"

        rows = db.execute(query, *parameters)
        # check if anime exist in db
        if len(rows) == 0:
            flash("Anime not found")
            return render_template("search.html", animes = [])
        return render_template("search.html", animes=rows)
    #show list of anime when user load a page
    else:
        start_rows = db.execute("SELECT * FROM Titels ORDER BY score DESC LIMIT 50")
        return render_template("search.html", animes=start_rows)


@app.route("/anime/<int:anime_id>")
def anime_page(anime_id):
    folders = None
    rows = db.execute("SELECT * FROM titels WHERE id = ?", anime_id)
    if len(rows) != 1:
        flash("Anime not found")
        return render_template("search.html", animes=[])
    # add discription from myanimelist if it isn`t in db
    if not rows[0]["Description"]:
        response = requests.get(f"https://api.jikan.moe/v4/anime/{rows[0]['mal_id']}")
        if response.status_code == 200:
            data = response.json()["data"]
            description = data["synopsis"]
            db.execute("UPDATE titels SET Description = ? WHERE id = ?", description, anime_id)
            rows[0]["Description"] = description
    if session.get("user_id"):
        folders = db.execute("SELECT * FROM folders WHERE user_id = ?", session["user_id"])
    # show anime page
    return render_template(
        "anime.html",
        anime=rows[0], folders = folders, statuses = statuses
    )

@app.route("/add_anime_in_folder", methods=["POST"])
# add anime in folder that exist 
@login_required
def add_anime_in_folder():
    user_id = session["user_id"]
    folder_id = request.form.get("folder_id")
    anime_id = request.form.get("anime_id")
    status = request.form.get("status")
    rating = request.form.get("rating")
    db.execute("INSERT INTO user_anime_infolder (user_id, anime_id, folder_id) VALUES (?, ?, ?)", user_id, anime_id, folder_id)
    db.execute("UPDATE user_anime_infolder SET status = ?, rating = ? WHERE user_id = ? AND anime_id = ?", status, rating, user_id, anime_id)
    return redirect(f"/anime/{anime_id}")

@app.route("/delete_anime_from_folder", methods=["POST"])
# delete anime from folder that exist 
@login_required
def delete_anime_from_folder():
    user_id = session["user_id"]
    folder_id = request.form.get("selected_folder")
    anime_id = request.form.get("anime_id")
    if folder_id:
        db.execute("DELETE FROM user_anime_infolder WHERE user_id = ? AND anime_id = ? AND folder_id = ?", user_id, anime_id, folder_id)
    else:
        db.execute("DELETE FROM user_anime_infolder WHERE user_id = ? AND anime_id = ?", user_id, anime_id)
    return redirect("/")

@app.route("/add_folder", methods=["POST"])
@login_required
# provide oportunity to create new folder
def add_folder():
    user_id = session["user_id"]
    folder_name = request.form.get("folder_name")
    if not folder_name:
        flash("Must provide folder name")
        return redirect("/")
    db.execute("INSERT INTO folders (user_id, name) VALUES (?, ?)", user_id, folder_name,)
    return redirect("/")

@app.route("/delete_folder", methods=["POST"])
@login_required
# provide oportunity to delete folders
def delete_folder():
    folder_id = request.form.get("folder_id")
    if not folder_id:
        flash("Must provide folder name")
        return redirect("/")
    db.execute("DELETE FROM user_anime_infolder WHERE folder_id = ? AND user_id = ?", folder_id, session["user_id"])
    db.execute("DELETE FROM folders WHERE id = ? AND user_id = ?", folder_id, session["user_id"])
    return redirect("/")

