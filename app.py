import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "segredo_muito_secreto"
UPLOAD_FOLDER = 'static/imagens'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    with sqlite3.connect("blog.db") as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT,
            conteudo TEXT,
            data TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS imagens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caminho TEXT,
            post_id INTEGER,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
        """)

def login_required(func):
    def wrapper(*args, **kwargs):
        if not session.get("logado"):
            flash("Você precisa estar logado.")
            return redirect(url_for("login"))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.route("/")
def home():
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        posts = cur.execute("SELECT * FROM posts ORDER BY id DESC LIMIT 5").fetchall()
        capas = {}
        for post in posts:
            img = cur.execute("SELECT caminho FROM imagens WHERE post_id = ? LIMIT 1", (post[0],)).fetchone()
            capas[post[0]] = img[0] if img else None
    return render_template("index.html", posts=posts, capas=capas, fundo="fundo.jpg")

@app.route("/sobre")
def sobre():
    return render_template("sobre.html", fundo="fundo.jpg")

@app.route("/contato")
def contato():
    return render_template("contato.html", fundo="fundo.jpg")

@app.route("/blog")
def blog():
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        posts = cur.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
        capas = {}
        for post in posts:
            img = cur.execute("SELECT caminho FROM imagens WHERE post_id = ? LIMIT 1", (post[0],)).fetchone()
            capas[post[0]] = img[0] if img else None
    return render_template("blog.html", posts=posts, capas=capas, fundo="fundo.jpg")

@app.route("/blog/<int:post_id>")
def ver_post(post_id):
    with sqlite3.connect("blog.db") as conn:
        post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        imagens = conn.execute("SELECT caminho FROM imagens WHERE post_id = ?", (post_id,)).fetchall()
    if post:
        return render_template("post.html", post=post, imagens=imagens, fundo="fundo.jpg")
    return "<h1>Post não encontrado</h1>", 404

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["usuario"] == "admin" and request.form["senha"] == "123":
            session["logado"] = True
            return redirect(url_for("admin"))
        flash("Usuário ou senha inválidos.", "danger")
    return render_template("login.html", fundo="fundo.jpg")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/novo", methods=["GET", "POST"])
@login_required
def novo_post():
    if request.method == "POST":
        titulo = request.form["titulo"]
        conteudo = request.form["conteudo"]
        data = request.form["data"]

        with sqlite3.connect("blog.db") as conn:
            cur = conn.cursor()
            cur.execute("INSERT INTO posts (titulo, conteudo, data) VALUES (?, ?, ?)",
                        (titulo, conteudo, data))
            post_id = cur.lastrowid

            imagens = request.files.getlist("imagens")
            for imagem in imagens:
                if imagem and allowed_file(imagem.filename):
                    nome_seguro = secure_filename(imagem.filename)
                    caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_seguro)
                    imagem.save(caminho)
                    cur.execute("INSERT INTO imagens (caminho, post_id) VALUES (?, ?)",
                                (f"imagens/{nome_seguro}", post_id))
            conn.commit()
        return redirect(url_for("blog"))
    return render_template("novo_post.html", fundo="fundo.jpg", editar=False)

@app.route("/admin", methods=["GET", "POST"])
@login_required
def admin():
    filtro_data = request.form.get("filtro_data") if request.method == "POST" else None
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        if filtro_data:
            posts = cur.execute("SELECT * FROM posts WHERE data = ? ORDER BY id DESC", (filtro_data,)).fetchall()
        else:
            posts = cur.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()

        capas = {}
        for post in posts:
            img = cur.execute("SELECT caminho FROM imagens WHERE post_id = ? LIMIT 1", (post[0],)).fetchone()
            capas[post[0]] = img[0] if img else None

    return render_template("admin.html", posts=posts, capas=capas, filtro_data=filtro_data, fundo="fundo.jpg")

@app.route("/editar/<int:post_id>", methods=["GET", "POST"])
@login_required
def editar_post(post_id):
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        if request.method == "POST":
            titulo = request.form["titulo"]
            conteudo = request.form["conteudo"]
            data = request.form["data"]

            cur.execute("UPDATE posts SET titulo = ?, conteudo = ?, data = ? WHERE id = ?",
                        (titulo, conteudo, data, post_id))

            novas_imagens = request.files.getlist("novas_imagens")
            for imagem in novas_imagens:
                if imagem and allowed_file(imagem.filename):
                    nome_seguro = secure_filename(imagem.filename)
                    caminho = os.path.join(app.config["UPLOAD_FOLDER"], nome_seguro)
                    imagem.save(caminho)
                    cur.execute("INSERT INTO imagens (caminho, post_id) VALUES (?, ?)",
                                (f"imagens/{nome_seguro}", post_id))

            conn.commit()
            flash("Post atualizado com sucesso!", "success")
            return redirect(url_for("admin"))

        post = cur.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        imagens = cur.execute("SELECT id, caminho FROM imagens WHERE post_id = ?", (post_id,)).fetchall()
    return render_template("editar_post.html", post=post, imagens=imagens, fundo="fundo.jpg")

@app.route("/apagar-imagem/<int:img_id>", methods=["POST"])
@login_required
def apagar_imagem(img_id):
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        imagem = cur.execute("SELECT caminho, post_id FROM imagens WHERE id = ?", (img_id,)).fetchone()
        if imagem:
            caminho_completo = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(imagem[0]))
            if os.path.exists(caminho_completo):
                os.remove(caminho_completo)
            cur.execute("DELETE FROM imagens WHERE id = ?", (img_id,))
            conn.commit()
        return redirect(url_for("editar_post", post_id=imagem[1]))

@app.route("/excluir/<int:post_id>", methods=["POST"])
@login_required
def excluir_post(post_id):
    with sqlite3.connect("blog.db") as conn:
        cur = conn.cursor()
        imagens = cur.execute("SELECT caminho FROM imagens WHERE post_id = ?", (post_id,)).fetchall()
        for img in imagens:
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(img[0]))
            if os.path.exists(caminho):
                os.remove(caminho)
        cur.execute("DELETE FROM imagens WHERE post_id = ?", (post_id,))
        cur.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    return redirect(url_for("admin"))

@app.route("/exportar-posts")
@login_required
def exportar_posts():
    with sqlite3.connect("blog.db") as conn:
        posts = conn.execute("SELECT titulo, conteudo, data FROM posts ORDER BY id DESC").fetchall()

    def gerar_csv():
        yield "Título,Conteúdo,Data\n"
        for post in posts:
            titulo = post[0].replace('"', "'")
            conteudo = post[1].replace('"', "'").replace("\n", " ")
            data = post[2]
            yield f'"{titulo}","{conteudo}","{data}"\n'

    return Response(gerar_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment;filename=posts.csv"})

if __name__ == "__main__":
    os.makedirs("static/imagens", exist_ok=True)
    init_db()
    app.run(debug=True)
