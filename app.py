from flask import Flask, redirect, render_template, request

from banco import conectar, criar_tabelas

app = Flask(__name__)
criar_tabelas()

@app.route("/")
def index():
    con = conectar()
    cur = con.cursor()

    total_produtos = cur.execute("SELECT COUNT(*) FROM produtos").fetchone()[0]
    total_pedidos  = cur.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
    receita = cur.execute("SELECT SUM(total) FROM pedidos").fetchone()[0] or 0

    # Produtos com estoque abaixo de 5 unidades
    alertas = cur.execute(
        "SELECT nome, estoque FROM produtos WHERE estoque < 5"
    ).fetchall()

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
    produtos = cur.execute(
        "SELECT * FROM produtos ORDER BY nome"
    ).fetchall()
    con.close()
    return render_template("produtos.html", produtos=produtos)

@app.route("/novo-pedido", methods=["GET", "POST"])
def novo_pedido():
    if request.method == "POST":
        produto_id = int(request.form["produto_id"])
        quantidade = int(request.form["quantidade"])

        con = conectar()
        cur = con.cursor()

        # Busca o produto para pegar preço e verificar estoque
        produto = cur.execute(
            "SELECT nome, preco, estoque FROM produtos WHERE id = ?",
            (produto_id,)
        ).fetchone()

        if not produto:
            con.close()
            return "Produto não encontrado", 404

        nome_prod, preco, estoque_atual = produto

        # Valida se tem estoque suficiente
        if quantidade > estoque_atual:
            con.close()
            return render_template("novo_pedido.html",
                erro=f"Estoque insuficiente! Disponível: {estoque_atual} unidades.",
                produtos=cur.execute("SELECT id, nome, estoque FROM produtos WHERE estoque > 0").fetchall()
            )

        total = preco * quantidade
        from datetime import datetime
        agora = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Registra o pedido
        cur.execute(
            "INSERT INTO pedidos (produto_id, quantidade, total, data_pedido) VALUES (?, ?, ?, ?)",
            (produto_id, quantidade, total, agora)
        )
        # Desconta do estoque
        cur.execute(
            "UPDATE produtos SET estoque = estoque - ? WHERE id = ?",
            (quantidade, produto_id)
        )
        con.commit()
        con.close()
        return redirect("/pedidos")

    # GET: lista só produtos com estoque > 0
    con = conectar()
    cur = con.cursor()
    produtos = cur.execute(
        "SELECT id, nome, estoque FROM produtos WHERE estoque > 0"
    ).fetchall()
    con.close()
    return render_template("novo_pedido.html", produtos=produtos, erro=None)

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

@app.route("/cadastrar-produto", methods=["GET", "POST"])
def cadastrar_produto():
    if request.method == "POST":
        nome    = request.form["nome"]
        preco   = float(request.form["preco"])
        estoque = int(request.form["estoque"])

        con = conectar()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO produtos (nome, preco, estoque) VALUES (?, ?, ?)",
            (nome, preco, estoque)
        )
        con.commit()
        con.close()
        return redirect("/produtos")

    return render_template("cadastrar_produto.html")


@app.route("/editar-produto/<int:id>", methods=["GET", "POST"])
def editar_produto(id):
    con = conectar()
    cur = con.cursor()

    if request.method == "POST":
        nome    = request.form["nome"]
        preco   = float(request.form["preco"])
        estoque = int(request.form["estoque"])

        cur.execute(
            "UPDATE produtos SET nome = ?, preco = ?, estoque = ? WHERE id = ?",
            (nome, preco, estoque, id)
        )
        con.commit()
        con.close()
        return redirect("/produtos")

    # GET: busca o produto atual para preencher o formulário
    produto = cur.execute(
        "SELECT id, nome, preco, estoque FROM produtos WHERE id = ?", (id,)
    ).fetchone()
    con.close()

    if not produto:
        return "Produto não encontrado", 404

    return render_template("editar_produto.html", produto=produto)

if __name__ == "__main__":
    app.run(debug=True)
