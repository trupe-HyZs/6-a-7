import os
import random
import sqlite3
from functools import wraps
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "data.db")
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-6a7-secret-key")

SELECOES = ["Brasil", "Argentina", "França", "Alemanha", "Espanha", "Itália", "Portugal", "Inglaterra", "Uruguai", "Holanda", "Croácia", "Bélgica"]
COPAS = ["Copa 1950", "Copa 1954", "Copa 1958", "Copa 1962", "Copa 1970", "Copa 1982", "Copa 1994", "Copa 2002", "Copa 2006", "Copa 2010", "Copa 2014", "Copa 2018", "Copa 2022"]

FORMACOES = {
    "4-3-3": ["GOL", "LE", "ZAG", "ZAG", "LD", "MC", "MEI", "MC", "PE", "CA", "PD"],
    "4-4-2": ["GOL", "LE", "ZAG", "ZAG", "LD", "ME", "MC", "MC", "MD", "CA", "CA"],
    "4-2-3-1": ["GOL", "LE", "ZAG", "ZAG", "LD", "VOL", "VOL", "PE", "MEI", "PD", "CA"],
    "4-2-4": ["GOL", "LE", "ZAG", "ZAG", "LD", "VOL", "VOL", "PE", "CA", "CA", "PD"],
    "3-5-2": ["GOL", "ZAG", "ZAG", "ZAG", "ALA", "MC", "MEI", "MC", "ALA", "CA", "CA"],
    "5-3-2": ["GOL", "LE", "ZAG", "ZAG", "ZAG", "LD", "MC", "MEI", "MC", "CA", "CA"],
    "4-5-1": ["GOL", "LE", "ZAG", "ZAG", "LD", "ME", "MC", "MEI", "MC", "MD", "CA"],
    "3-4-3": ["GOL", "ZAG", "ZAG", "ZAG", "ME", "MC", "MC", "MD", "PE", "CA", "PD"],
}

CAMPO_LINHAS = {
    "4-3-3": [["PE", "CA", "PD"], ["MC", "MEI", "MC"], ["LE", "ZAG", "ZAG", "LD"], ["GOL"]],
    "4-4-2": [["CA", "CA"], ["ME", "MC", "MC", "MD"], ["LE", "ZAG", "ZAG", "LD"], ["GOL"]],
    "4-2-3-1": [["CA"], ["PE", "MEI", "PD"], ["VOL", "VOL"], ["LE", "ZAG", "ZAG", "LD"], ["GOL"]],
    "4-2-4": [["PE", "CA", "CA", "PD"], ["VOL", "VOL"], ["LE", "ZAG", "ZAG", "LD"], ["GOL"]],
    "3-5-2": [["CA", "CA"], ["ALA", "MC", "MEI", "MC", "ALA"], ["ZAG", "ZAG", "ZAG"], ["GOL"]],
    "5-3-2": [["CA", "CA"], ["MC", "MEI", "MC"], ["LE", "ZAG", "ZAG", "ZAG", "LD"], ["GOL"]],
    "4-5-1": [["CA"], ["ME", "MC", "MEI", "MC", "MD"], ["LE", "ZAG", "ZAG", "LD"], ["GOL"]],
    "3-4-3": [["PE", "CA", "PD"], ["ME", "MC", "MC", "MD"], ["ZAG", "ZAG", "ZAG"], ["GOL"]],
}

POSICOES_NOMES = {
    "GOL": "Goleiro", "LE": "Lateral esquerdo", "LD": "Lateral direito", "ZAG": "Zagueiro",
    "VOL": "Volante", "MC": "Meio-campista", "MEI": "Meia", "ME": "Meia esquerdo",
    "MD": "Meia direito", "ALA": "Ala", "PE": "Ponta esquerda", "PD": "Ponta direita", "CA": "Centroavante"
}

MODELO_ELENCO = [
    ("GOL 01", ["GOL"]), ("GOL 02", ["GOL"]), ("GOL 03", ["GOL"]),
    ("DEF 01", ["ZAG", "LE"]), ("DEF 02", ["ZAG"]), ("DEF 03", ["ZAG", "LD"]),
    ("DEF 04", ["ZAG"]), ("DEF 05", ["LE", "ALA"]), ("DEF 06", ["LD", "ALA"]),
    ("MEIO 01", ["VOL", "MC"]), ("MEIO 02", ["VOL", "MC"]), ("MEIO 03", ["MC", "MEI"]),
    ("MEIO 04", ["MC", "MEI"]), ("MEIO 05", ["ME", "PE"]), ("MEIO 06", ["MD", "PD"]),
    ("ATA 01", ["PE", "PD"]), ("ATA 02", ["PE", "CA"]), ("ATA 03", ["PD", "CA"]),
    ("ATA 04", ["CA"]), ("ATA 05", ["CA"]), ("ATA 06", ["PD", "CA"]),
    ("ATA 07", ["PE", "CA"]), ("MEIO 07", ["MEI", "ME", "MD"]),
]


def get_elenco(selecao):
    return [
        {"id": f"{selecao}-{i}", "nome": f"{selecao} — {nome}", "posicoes": posicoes}
        for i, (nome, posicoes) in enumerate(MODELO_ELENCO, start=1)
    ]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    db.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(**kwargs)
    return wrapped_view


def montar_posicoes(formacao, escolhidos):
    resultado, contagem = [], {}
    for posicao in FORMACOES.get(formacao, FORMACOES["4-3-3"]):
        contagem[posicao] = contagem.get(posicao, 0) + 1
        chave = f"{posicao}_{contagem[posicao]}"
        resultado.append({
            "key": chave,
            "codigo": posicao,
            "nome": POSICOES_NOMES.get(posicao, posicao),
            "jogador": escolhidos.get(chave),
        })
    return resultado


def montar_linhas_campo(formacao, posicoes):
    por_codigo = {}
    for item in posicoes:
        por_codigo.setdefault(item["codigo"], []).append(item)
    linhas = []
    for linha in CAMPO_LINHAS.get(formacao, CAMPO_LINHAS["4-3-3"]):
        atual = []
        for codigo in linha:
            if por_codigo.get(codigo):
                atual.append(por_codigo[codigo].pop(0))
        linhas.append(atual)
    return linhas


def proxima_posicao(formacao, escolhidos):
    for posicao in FORMACOES.get(formacao, FORMACOES["4-3-3"]):
        total = FORMACOES.get(formacao, []).count(posicao)
        usados = sum(1 for chave in escolhidos if chave.startswith(f"{posicao}_"))
        if usados < total:
            return posicao
    return None


def preparar_jogadores(elenco, escolhidos, posicoes, selecionado_id=None):
    usados = set(escolhidos.values())
    resultado = []
    for jogador in elenco:
        opcoes = []
        for pos in posicoes:
            if pos["codigo"] in jogador["posicoes"]:
                opcoes.append({
                    "key": pos["key"],
                    "codigo": pos["codigo"],
                    "label": pos["codigo"],
                    "ocupada": bool(pos["jogador"]),
                })
        resultado.append({
            **jogador,
            "escolhido": jogador["id"] in usados,
            "selecionado": jogador["id"] == selecionado_id,
            "opcoes": opcoes,
            "tem_posicao_livre": any(not opcao["ocupada"] for opcao in opcoes),
        })
    return resultado


def sortear_proxima_selecao():
    selecao_anterior = session.get("sorteio", {}).get("selecao")
    opcoes_selecao = [s for s in SELECOES if s != selecao_anterior] if selecao_anterior else SELECOES
    return {
        "dado": random.randint(1, 6),
        "selecao": random.choice(opcoes_selecao),
        "copa": random.choice(COPAS),
    }


@app.route("/")
def index():
    return redirect(url_for("dashboard" if "user_id" in session else "login"))


@app.route("/cadastro", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        if not username or not password or not confirm_password: flash("Preencha todos os campos.", "error")
        elif len(username) < 3: flash("O usuário precisa ter pelo menos 3 caracteres.", "error")
        elif len(password) < 6: flash("A senha precisa ter pelo menos 6 caracteres.", "error")
        elif password != confirm_password: flash("As senhas não coincidem.", "error")
        else:
            try:
                db = get_db(); db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, generate_password_hash(password))); db.commit()
                flash("Conta criada. Agora faça login.", "success"); return redirect(url_for("login"))
            except sqlite3.IntegrityError: flash("Esse nome de usuário já está em uso.", "error")
    return render_template("cadastro.html")


@app.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip(); password = request.form.get("password", "")
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user is None or not check_password_hash(user["password_hash"], password): flash("Usuário ou senha incorretos.", "error")
        else:
            session.clear(); session["user_id"] = user["id"]; session["username"] = user["username"]; return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session["username"])


@app.route("/desafio", methods=("GET", "POST"))
@login_required
def desafio():
    if request.method == "POST":
        session["partida"] = {
            "modo": request.form.get("modo", "normal"),
            "formacao": request.form.get("formacao", "4-3-3"),
            "estilo": request.form.get("estilo", "equilibrado"),
        }
        session.pop("sorteio", None)
        session.pop("escolhidos", None)
        session.pop("jogador_selecionado", None)
        session["rolagens_manuais"] = 0
        return redirect(url_for("partida"))
    return render_template("desafio.html")


@app.route("/partida", methods=("GET", "POST"))
@login_required
def partida():
    partida_config = session.get("partida")
    if not partida_config:
        return redirect(url_for("desafio"))

    if request.method == "POST":
        acao = request.form.get("acao", "sortear")

        if acao == "sortear":
            tinha_sorteio = bool(session.get("sorteio"))
            if not tinha_sorteio or session.get("rolagens_manuais", 0) < 3:
                session["sorteio"] = sortear_proxima_selecao()
                if tinha_sorteio:
                    session["rolagens_manuais"] = session.get("rolagens_manuais", 0) + 1
                session.pop("jogador_selecionado", None)

        elif acao == "selecionar_jogador" and session.get("sorteio"):
            jogador_id = request.form.get("jogador")
            sorteio = session["sorteio"]
            elenco = get_elenco(sorteio["selecao"])
            if any(j["id"] == jogador_id for j in elenco):
                escolhidos = dict(session.get("escolhidos", {}))
                if jogador_id not in escolhidos.values():
                    session["jogador_selecionado"] = jogador_id

        elif acao == "escolher" and session.get("sorteio"):
            escolhidos = dict(session.get("escolhidos", {}))
            chave = request.form.get("posicao")
            jogador_id = session.get("jogador_selecionado")
            sorteio = session["sorteio"]
            elenco = get_elenco(sorteio["selecao"])
            posicoes = montar_posicoes(partida_config["formacao"], escolhidos)
            jogador = next((item for item in elenco if item["id"] == jogador_id), None)
            posicao = next((item for item in posicoes if item["key"] == chave), None)
            jogador_ja_escolhido = jogador_id in escolhidos.values() if jogador_id else True

            if jogador and posicao and not posicao["jogador"] and not jogador_ja_escolhido and posicao["codigo"] in jogador["posicoes"]:
                escolhidos[chave] = jogador_id
                session["escolhidos"] = escolhidos
                session.pop("jogador_selecionado", None)

                # Sorteio automático após cada jogador colocado.
                # Não altera rolagens_manuais.
                if len(escolhidos) < 11:
                    session["sorteio"] = sortear_proxima_selecao()

    sorteio = session.get("sorteio")
    escolhidos = session.get("escolhidos", {})
    selecionado_id = session.get("jogador_selecionado")
    posicoes = montar_posicoes(partida_config["formacao"], escolhidos) if sorteio else []
    linhas_campo = montar_linhas_campo(partida_config["formacao"], posicoes) if sorteio else []
    proxima = proxima_posicao(partida_config["formacao"], escolhidos) if sorteio else None
    completo = sorteio is not None and proxima is None
    elenco = get_elenco(sorteio["selecao"]) if sorteio else []
    jogadores = preparar_jogadores(elenco, escolhidos, posicoes, selecionado_id) if sorteio else []
    jogador_selecionado = next((j for j in jogadores if j["id"] == selecionado_id), None)

    return render_template(
        "partida.html",
        username=session["username"],
        modo=partida_config["modo"],
        formacao=partida_config["formacao"],
        estilo=partida_config["estilo"],
        sorteio=sorteio,
        posicoes=posicoes,
        linhas_campo=linhas_campo,
        jogadores=jogadores,
        jogador_selecionado=jogador_selecionado,
        proxima=proxima,
        proxima_nome=POSICOES_NOMES.get(proxima, proxima) if proxima else None,
        completo=completo,
        rolagens_manuais=session.get("rolagens_manuais", 0),
    )


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)