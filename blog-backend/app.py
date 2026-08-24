import os
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timezone

from dotenv import load_dotenv

from werkzeug.security import check_password_hash

load_dotenv()

ADMIN_USERNAME = os.environ["ADMIN_USERNAME"]
ADMIN_PASSWORD_HASH = os.environ["ADMIN_PASSWORD_HASH"]

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
data_dir = Path(
    os.environ.get(
        "DATA_DIR",
        BASE_DIR / "instance"
    )
)
data_dir.mkdir(
    parents=True,
    exist_ok=True
)
DB_PATH = data_dir / "blog.db"

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"sqlite:///{DB_PATH.as_posix()}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db = SQLAlchemy(app)
csrf = CSRFProtect(app)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key = True)

    title = db.Column(
        db.String(200),
        nullable = False
    )

    content = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default = lambda: datetime.now(timezone.utc),
        nullable = False
    )

    published = db.Column(
        db.Boolean,
        default = False,
        nullable = False
    )

    def __repr__(self):
        return f"<Post {self.title}>"

with app.app_context():
    db.create_all()

@app.route('/')
def home():
    posts = (
        Post.query
        .filter_by(published = True)
        .order_by(Post.created_at.desc())
        .all()
    )
    return render_template("blog.html", posts = posts)

@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)

    if not post.published:
        abort(404)

    return render_template("post.html", post = post)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if (
            username == ADMIN_USERNAME
            and password
            and check_password_hash(ADMIN_PASSWORD_HASH, password)
        ):
            session.clear()
            session["admin_logged_in"] = True

            return redirect(url_for("admin_dashboard"))

        error = "Invalid username or password."

    return render_template("admin_login.html", error = error)

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    posts = (
        Post.query
        .order_by(Post.created_at.desc())
        .all()
    )

    return render_template("admin_dashboard.html", posts = posts)

@app.route("/admin/logout")
def admin_logout():
    session.clear()

    return redirect(url_for("admin_login"))

@app.route("/admin/posts/new", methods = ["GET", "POST"])
def admin_new_post():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        published = request.form.get("published") == "on"

        if not title or not content:
            error = "Title and content are required."

            return render_template("admin_new_post.html", error = error)

        post = Post(
            title = title,
            content = content,
            published = published
        )

        db.session.add(post)
        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_new_post.html")

@app.route("/admin/posts/<int:post_id>/edit", methods = ["GET", "POST"])
def admin_edit_post(post_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    post = Post.query.get_or_404(post_id)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        content = request.form.get("content", "").strip()

        published = request.form.get("published") == "on"

        if not title or not content:
            error = "Title and content are required."

            return render_template("admin_edit_post.html", post = post, error = error)

        post.title = title
        post.content = content
        post.published = published

        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    return render_template("admin_edit_post.html", post = post)

@app.route("/admin/posts/<int:post_id>/delete", methods = ["POST"])
def admin_delete_post(post_id):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin_login"))

    post = Post.query.get_or_404(post_id)

    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)