from __future__ import annotations

import os
import json
from functools import wraps
from typing import Any

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, abort, flash
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-change-me")


# ====== DB （環境に合わせて変更）======
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(os.environ.get("DB_PORT", "3306")),
    "user": os.environ.get("DB_USER", "rugbyapp"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "rugby_analysis"),
    "charset": "utf8mb4",
}

pool = pooling.MySQLConnectionPool(pool_name="app_pool", pool_size=5, **DB_CONFIG)


def get_conn():
    return pool.get_connection()


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapper


def current_user_id() -> int | None:
    return session.get("user_id")


# ====== Auth pages ======
@app.get("/login")
def login():
    # GET: ログイン画面
    return render_template("login.html")


@app.post("/login")
def login_post():
    # POST: ログイン処理
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT id, username, password_hash FROM users WHERE email=%s",
            (email,)
        )
        user = cur.fetchone()
        if not user or not check_password_hash(user["password_hash"], password):
            flash("メールアドレスまたはパスワードが違います。", "danger")
            return redirect(url_for("login"))

        session["user_id"] = int(user["id"])
        session["username"] = user["username"]
        return redirect(url_for("main"))
    finally:
        conn.close()


@app.get("/register")
def register():
    # GET: 新規登録画面
    return render_template("register.html")


@app.post("/register")
def register_post():
    # POST: 新規登録処理
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    repassword = request.form.get("repassword", "")
    # ※添付register.htmlは name="name" になっている
    username = request.form.get("name", "").strip()

    if not email or not password or not repassword or not username:
        flash("未入力の項目があります。", "danger")
        return redirect(url_for("register"))

    if password != repassword:
        flash("パスワード（確認用）が一致しません。", "danger")
        return redirect(url_for("register"))

    pw_hash = generate_password_hash(password)

    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        try:
            cur.execute(
                "INSERT INTO users (email, username, password_hash) VALUES (%s, %s, %s)",
                (email, username, pw_hash)
            )
            conn.commit()
        except mysql.connector.IntegrityError:
            flash("そのメールアドレス、またはユーザー名は既に使われています。", "danger")
            return redirect(url_for("register"))

        # 登録後はログイン状態にする（好みで login に戻してもOK）
        session["user_id"] = int(cur.lastrowid)
        session["username"] = username
        return redirect(url_for("main"))
    finally:
        conn.close()


@app.post("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("login"))


# ====== Pages ======
@app.get("/")
def root():
    # 未ログインならログインへ、ログイン済みならmainへ
    if "user_id" in session:
        return redirect(url_for("main"))
    return redirect(url_for("login"))


@app.get("/main")
@login_required
def main():
    # 添付 main.html を表示（投稿フォーム）
    # main.html は initial_data_json を参照しているので、無くても動くよう null を入れておく
    return render_template("main.html", initial_data_json="null")


@app.get("/restore")
@login_required
def restore():
    # 添付 restore.html を表示（保存一覧＝全投稿一覧）
    return render_template("restore.html")


# ====== API: Create post (main.htmlのform action先) ======
@app.post("/api/create_post")
@login_required
def api_create_post():
    """
    main.html から送られる想定：
      - columns_json: {"options":[...], "facts_on":[...], "facts_off":[...], "reasons":[...]}
      - reflection: 評価コメント（修正/維持/評価）
      - title: 投稿内容（一覧で見せたいメインのテキスト）
    """
    user_id = current_user_id()

    columns_json_raw = request.form.get("columns_json", "{}")
    reflection = request.form.get("reflection", "").strip()  # evaluation_comment に入れる
    title = request.form.get("title", "").strip()            # post_content に入れる

    if not reflection or not title:
        # 必須にしたいならここで弾く（要件上「自由入力」だが最低限は必要だと思うので）
        flash("投稿内容（title）と、修正/維持/評価（reflection）は必須です。", "danger")
        return redirect(url_for("main"))

    try:
        cols = json.loads(columns_json_raw) if columns_json_raw else {}
    except json.JSONDecodeError:
        cols = {}

    def norm_list(v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(x).strip() for x in v if str(x).strip()]

    options = norm_list(cols.get("options"))
    facts_on = norm_list(cols.get("facts_on"))
    facts_off = norm_list(cols.get("facts_off"))
    reasons = norm_list(cols.get("reasons"))

    conn = get_conn()
    try:
        cur = conn.cursor()

        # 1) posts 作成
        cur.execute(
            """
            INSERT INTO posts (user_id, evaluation_comment, post_content)
            VALUES (%s, %s, %s)
            """,
            (user_id, reflection, title)
        )
        post_id = cur.lastrowid

        # 2) post_entries 追加
        entries_to_insert: list[tuple[Any, ...]] = []

        def add_entries(entry_type: str, values: list[str]):
            for i, body in enumerate(values):
                entries_to_insert.append((post_id, entry_type, i, body))

        add_entries("OPTION", options)
        add_entries("ON_BALL", facts_on)
        add_entries("OFF_BALL", facts_off)
        add_entries("REASON", reasons)

        if entries_to_insert:
            cur.executemany(
                """
                INSERT INTO post_entries (post_id, entry_type, position, body)
                VALUES (%s, %s, %s, %s)
                """,
                entries_to_insert
            )

        conn.commit()

        # 投稿後の遷移先：保存一覧へ（好みで main に戻す等もOK）
        return redirect(url_for("restore"))

    finally:
        conn.close()


# ====== API: List posts (restore.htmlのJSが叩く想定) ======
@app.get("/api/posts")
@login_required
def api_posts():
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """
            SELECT
              p.id AS post_id,
              u.username,
              p.created_at,
              p.post_content
            FROM posts p
            JOIN users u ON u.id = p.user_id
            ORDER BY p.created_at DESC
            """
        )
        rows = cur.fetchall()
        return jsonify(rows)
    finally:
        conn.close()


@app.get("/posts/<int:post_id>")
@login_required
def post_detail(post_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)

        # posts + author
        cur.execute(
            """
            SELECT
              p.id AS post_id,
              p.user_id,
              u.username,
              p.created_at,
              p.updated_at,
              p.evaluation_comment,
              p.post_content
            FROM posts p
            JOIN users u ON u.id = p.user_id
            WHERE p.id=%s
            """,
            (post_id,),
        )
        post = cur.fetchone()
        if not post:
            abort(404)

        # entries
        cur.execute(
            """
            SELECT entry_type, position, body
            FROM post_entries
            WHERE post_id=%s
            ORDER BY entry_type, position
            """,
            (post_id,),
        )
        rows = cur.fetchall()

        # main.jsのキーに合わせて整形
        columns = {"options": [], "facts_on": [], "facts_off": [], "reasons": []}
        for r in rows:
            if r["entry_type"] == "OPTION":
                columns["options"].append(r["body"])
            elif r["entry_type"] == "ON_BALL":
                columns["facts_on"].append(r["body"])
            elif r["entry_type"] == "OFF_BALL":
                columns["facts_off"].append(r["body"])
            elif r["entry_type"] == "REASON":
                columns["reasons"].append(r["body"])

        # 詳細ページ表示用JSON（JSで盤面に復元する）
        detail_data = {
            "columns": columns,
            "title": post["post_content"],          # main.htmlの title と同じ意味に合わせる
            "reflection": post["evaluation_comment"] # main.htmlの reflection と同じ意味に合わせる
        }
        detail_data_json = json.dumps(detail_data, ensure_ascii=False)

        return render_template(
            "post_detail.html",
            post=post,
            detail_data_json=detail_data_json,
        )
    finally:
        conn.close()


# ====== API: Delete (自分の投稿だけ) ======
@app.post("/api/posts/<int:post_id>/delete")
@login_required
def api_post_delete(post_id: int):
    uid = current_user_id()
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("DELETE FROM posts WHERE id=%s AND user_id=%s", (post_id, uid))
        conn.commit()
        if cur.rowcount == 0:
            abort(403)
        return jsonify({"ok": True})
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True)
