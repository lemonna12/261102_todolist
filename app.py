import os
import sqlite3
from datetime import date

from flask import Flask, g, redirect, render_template, request, url_for, flash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "todo.db")

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

PRIORITIES = {"high": "높음", "medium": "보통", "low": "낮음"}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DATABASE) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                memo TEXT DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'medium',
                due_date TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            )
            """
        )


@app.route("/")
def index():
    status = request.args.get("status", "all")
    keyword = request.args.get("q", "").strip()

    sql = "SELECT * FROM todos WHERE 1=1"
    params = []
    if status == "active":
        sql += " AND done = 0"
    elif status == "done":
        sql += " AND done = 1"
    if keyword:
        sql += " AND (title LIKE ? OR memo LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += """
        ORDER BY done ASC,
                 CASE priority WHEN 'high' THEN 0 WHEN 'medium' THEN 1 ELSE 2 END,
                 CASE WHEN due_date IS NULL OR due_date = '' THEN 1 ELSE 0 END,
                 due_date ASC,
                 id DESC
    """

    db = get_db()
    todos = db.execute(sql, params).fetchall()
    counts = db.execute(
        "SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done FROM todos"
    ).fetchone()

    return render_template(
        "index.html",
        todos=todos,
        status=status,
        keyword=keyword,
        total=counts["total"],
        done_count=counts["done"],
        priorities=PRIORITIES,
        today=date.today().isoformat(),
    )


@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    if not title:
        flash("할일 제목을 입력하세요.")
        return redirect(url_for("index"))

    priority = request.form.get("priority", "medium")
    if priority not in PRIORITIES:
        priority = "medium"

    db = get_db()
    db.execute(
        "INSERT INTO todos (title, memo, priority, due_date) VALUES (?, ?, ?, ?)",
        (
            title,
            request.form.get("memo", "").strip(),
            priority,
            request.form.get("due_date") or None,
        ),
    )
    db.commit()
    flash("할일이 추가되었습니다.")
    return redirect(url_for("index"))


@app.route("/toggle/<int:todo_id>", methods=["POST"])
def toggle(todo_id):
    db = get_db()
    db.execute("UPDATE todos SET done = 1 - done WHERE id = ?", (todo_id,))
    db.commit()
    return redirect(request.referrer or url_for("index"))


@app.route("/edit/<int:todo_id>", methods=["GET", "POST"])
def edit(todo_id):
    db = get_db()
    todo = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
    if todo is None:
        flash("해당 할일을 찾을 수 없습니다.")
        return redirect(url_for("index"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("할일 제목을 입력하세요.")
            return redirect(url_for("edit", todo_id=todo_id))

        priority = request.form.get("priority", "medium")
        if priority not in PRIORITIES:
            priority = "medium"

        db.execute(
            "UPDATE todos SET title = ?, memo = ?, priority = ?, due_date = ? WHERE id = ?",
            (
                title,
                request.form.get("memo", "").strip(),
                priority,
                request.form.get("due_date") or None,
                todo_id,
            ),
        )
        db.commit()
        flash("할일이 수정되었습니다.")
        return redirect(url_for("index"))

    return render_template("edit.html", todo=todo, priorities=PRIORITIES)


@app.route("/delete/<int:todo_id>", methods=["POST"])
def delete(todo_id):
    db = get_db()
    db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
    db.commit()
    flash("할일이 삭제되었습니다.")
    return redirect(request.referrer or url_for("index"))


@app.route("/clear-done", methods=["POST"])
def clear_done():
    db = get_db()
    db.execute("DELETE FROM todos WHERE done = 1")
    db.commit()
    flash("완료된 할일을 모두 삭제했습니다.")
    return redirect(url_for("index"))


init_db()

if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5050)))
