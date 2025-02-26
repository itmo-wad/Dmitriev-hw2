from functools import wraps
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
import os
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "default-key-change-me")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.config["UPLOAD_FOLDER"] = os.path.join("static", "uploads")
# os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


mongo = PyMongo(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "username" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function

@app.route("/", methods=["GET", "POST"])
def login():
    if "username" in session:
        return redirect(url_for("profile"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = mongo.db.users.find_one({"username": username})

        if user and check_password_hash(user["password"], password):
            session["username"] = username
            return redirect(url_for("profile"))
        else:
            flash("Неверное имя пользователя или пароль", "error")

    return render_template("index.html")


@app.route("/profile")
@login_required
def profile():
    user = mongo.db.users.find_one({"username": session["username"]})
    return render_template("profile.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        existing_user = mongo.db.users.find_one({"username": username})

        if existing_user:
            flash("Пользователь с таким именем уже существует", "error")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = {
            "username": username,
            "password": hashed_password,
            "profile_pic": "default.png",
            "date_joined": datetime.now()
        }

        mongo.db.users.insert_one(new_user)

        session["username"] = username

        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))


@app.route("/update_profile", methods=["GET", "POST"])
@login_required
def update_profile():
    user = mongo.db.users.find_one({"username": session["username"]})

    if request.method == "POST":
        updates = {}

        if "name" in request.form:
            updates["name"] = request.form.get("name")

        if "bio" in request.form:
            updates["bio"] = request.form.get("bio")

        if "profile_pic" in request.files:
            file = request.files["profile_pic"]

            if file.filename != "":
                filename = f"{session['username']}_{datetime.now().strftime('%Y%m%d%H%M%S')}{os.path.splitext(file.filename)[1]}"
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                updates["profile_pic"] = filename

        if updates:
            mongo.db.users.update_one({"username": session["username"]}, {"$set": updates})

        return redirect(url_for("profile"))

    return render_template("update_profile.html", user=user)


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        user = mongo.db.users.find_one({"username": session["username"]})

        if check_password_hash(user["password"], current_password):
            hashed_password = generate_password_hash(new_password)
            mongo.db.users.update_one(
                {"username": session["username"]},
                {"$set": {"password": hashed_password}}
            )
            flash("Пароль успешно изменен", "success")
            return redirect(url_for("profile"))
        else:
            flash("Текущий пароль введен неверно", "error")

    return render_template("change_password.html")


if __name__ == "__main__":
    app.run(debug=True, host="localhost", port=5000)