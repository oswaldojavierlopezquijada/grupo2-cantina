from flask import Flask, redirect, render_template, request, session, url_for
from functools import wraps
from banco import conectar, criar_tabelas

app = Flask(__name__)
app.secret_key = "sushi-digital-secret-2024"  # troque por algo seguro em produção

criar_tabelas()

# ── CREDENCIAIS DO ADMIN ─────────────────────────────────────────
ADMIN_USUARIO = "admin"
ADMIN_SENHA   = "sushi123"  # troque antes de colocar no ar

# ── DECORADOR DE PROTEÇÃO ────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logado"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

# ── AUTH ─────────────────────────────────────────────────────────
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    erro = None
    if request.method == "POST":
        usuario = request.form["usuario"]
        senha   = request.form["senha"]
        if usuario == ADMIN_USUARIO and senha == ADMIN_SENHA:
            session["admin_logado"] = True
            return redirect("/produtos")
        erro = "Usuário ou senha incorretos."
    return render_template("admin_login.html", erro=erro)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin/login")

# ── ROTAS PÚBLICAS ───────────────────────────────────────────────
@app.route("/")
def index():
    con = conectar()
    cur = con.cursor()
    total_produtos = cur.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    total_pedidos  = cur.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    receita        = cur.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0
    alertas        = cur.execute("SELECT nome, estoque FROM produtos WHERE estoque < 5").fetchall()
    con.close()
    return render_template("index.html",
        total_produtos=total_produtos,
        total_pedidos=total_pedidos,
        receita=receita,
        alertas=alertas
    )

@app.route("/produtos")
def listar_produtos():
    con = conectar()
    cur = con.cursor()
    produtos = cur.execute("SELECT * FROM produtos ORDER BY nome").fetchall()
    con.close()
    return render_template("produtos.html", produtos=produtos)

@app.route("/pedidos")
def listar_pedidos():
    con = conectar()
    cur = con.cursor()
    pedidos = cur.execute("""
        SELECT p.id, pr.nome, p.quantidade, p.total, p.data_pedido
        FROM pedidos p
        JOIN produtos pr ON p.produto_id = pr.id
        ORDER BY p.id DESC
    """).fetchall()
    con.close()
    return render_template("pedidos.html", pedidos=pedidos)

@app.route("/novo-pedido", methods=["GET", "POST"])
def novo_pedido():
    if request.method == "POST":
        produto_id    = int(request.form["produto_id"])
        quantidade    = int(request.form["quantidade"])
        con = conectar()
        cur = con.cursor()
        produto = cur.execute(
            "SELECT nome, preco, estoque FROM produtos WHERE id = ?", (produto_id,)
        ).fetchone()
        if not produto:
            con.close()
            return "Produto não encontrado", 404
        nome_prod, preco, estoque_atual = produto
        if quantidade > estoque_atual:
            produtos = cur.execute("SELECT id, nome, estoque FROM produtos WHERE estoque > 0").fetchall()
            con.close()
            return render_template("novo_pedido.html",
                erro=f"Estoque insuficiente! Disponível: {estoque_atual} unidades.",
                produtos=produtos
            )
        from datetime import datetime
        cur.execute(
            "INSERT INTO pedidos (produto_id, quantidade, total, data_pedido) VALUES (?, ?, ?, ?)",
            (produto_id, quantidade, preco * quantidade, datetime.now().strftime("%d/%m/%Y %H:%M"))
        )
        cur.execute("UPDATE produtos SET estoque = estoque - ? WHERE id = ?", (quantidade, produto_id))
        con.commit()
        con.close()
        return redirect("/pedidos")
    con = conectar()
    cur = con.cursor()
    produtos = cur.execute("SELECT id, nome, estoque FROM produtos WHERE estoque > 0").fetchall()
    con.close()
    return render_template("novo_pedido.html", produtos=produtos, erro=None)

# ── ROTAS PROTEGIDAS (só admin) ──────────────────────────────────
@app.route("/cadastrar-produto", methods=["GET", "POST"])
@login_required
def cadastrar_produto():
    if request.method == "POST":
        nome      = request.form["nome"]
        preco     = float(request.form["preco"])
        estoque   = int(request.form["estoque"])
        descricao = request.form.get("descricao", "")
        con = conectar()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO produtos (nome, preco, estoque, descricao) VALUES (?, ?, ?, ?)",
            (nome, preco, estoque, descricao)
        )
        con.commit()
        con.close()
        return redirect("/produtos")
    return render_template("cadastrar_produto.html")

@app.route("/editar-produto/<int:id>", methods=["GET", "POST"])
@login_required
def editar_produto(id):
    con = conectar()
    cur = con.cursor()
    if request.method == "POST":
        nome      = request.form["nome"]
        preco     = float(request.form["preco"])
        estoque   = int(request.form["estoque"])
        descricao = request.form.get("descricao", "")
        cur.execute(
            "UPDATE produtos SET nome = ?, preco = ?, estoque = ?, descricao = ? WHERE id = ?",
            (nome, preco, estoque, descricao, id)
        )
        con.commit()
        con.close()
        return redirect("/produtos")
    produto = cur.execute(
        "SELECT id, nome, preco, estoque, descricao FROM produtos WHERE id = ?", (id,)
    ).fetchone()
    con.close()
    if not produto:
        return "Produto não encontrado", 404
    return render_template("editar_produto.html", produto=produto)

@app.route("/deletar-produto/<int:id>", methods=["POST"])
@login_required
def deletar_produto(id):
    con = conectar()
    cur = con.cursor()
    cur.execute("DELETE FROM produtos WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect("/produtos")

if __name__ == "__main__":
    app.run(debug=True)