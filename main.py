import os, random, sqlite3, secrets, json
from functools import wraps
from datetime import date
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'data.db')
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-6a7-secret-key')

SELECOES = ['Brasil','Argentina','França','Alemanha','Espanha','Itália','Portugal','Inglaterra','Uruguai','Holanda','Croácia','Bélgica','México','Japão','Marrocos','Colômbia']
COPAS = [f'Copa {x}' for x in [1950,1954,1958,1962,1966,1970,1974,1978,1982,1986,1990,1994,1998,2002,2006,2010,2014,2018,2022,2026]]
FORMACOES = {'4-3-3':['GOL','LE','ZAG','ZAG','LD','MC','MEI','MC','PE','CA','PD'],'4-4-2':['GOL','LE','ZAG','ZAG','LD','ME','MC','MC','MD','CA','CA'],'4-2-3-1':['GOL','LE','ZAG','ZAG','LD','VOL','VOL','PE','MEI','PD','CA'],'4-2-4':['GOL','LE','ZAG','ZAG','LD','VOL','VOL','PE','CA','CA','PD'],'3-5-2':['GOL','ZAG','ZAG','ZAG','ALA','MC','MEI','MC','ALA','CA','CA'],'5-3-2':['GOL','LE','ZAG','ZAG','ZAG','LD','MC','MEI','MC','CA','CA'],'4-5-1':['GOL','LE','ZAG','ZAG','LD','ME','MC','MEI','MC','MD','CA'],'3-4-3':['GOL','ZAG','ZAG','ZAG','ME','MC','MC','MD','PE','CA','PD']}
CAMPO_LINHAS = {'4-3-3':[['PE','CA','PD'],['MC','MEI','MC'],['LE','ZAG','ZAG','LD'],['GOL']],'4-4-2':[['CA','CA'],['ME','MC','MC','MD'],['LE','ZAG','ZAG','LD'],['GOL']],'4-2-3-1':[['CA'],['PE','MEI','PD'],['VOL','VOL'],['LE','ZAG','ZAG','LD'],['GOL']],'4-2-4':[['PE','CA','CA','PD'],['VOL','VOL'],['LE','ZAG','ZAG','LD'],['GOL']],'3-5-2':[['CA','CA'],['ALA','MC','MEI','MC','ALA'],['ZAG','ZAG','ZAG'],['GOL']],'5-3-2':[['CA','CA'],['MC','MEI','MC'],['LE','ZAG','ZAG','ZAG','LD'],['GOL']],'4-5-1':[['CA'],['ME','MC','MEI','MC','MD'],['LE','ZAG','ZAG','LD'],['GOL']],'3-4-3':[['PE','CA','PD'],['ME','MC','MC','MD'],['ZAG','ZAG','ZAG'],['GOL']]}
MODELO_ELENCO=[('GOL 01',['GOL']),('GOL 02',['GOL']),('GOL 03',['GOL']),('DEF 01',['ZAG','LE']),('DEF 02',['ZAG']),('DEF 03',['ZAG','LD']),('DEF 04',['ZAG']),('DEF 05',['LE','ALA']),('DEF 06',['LD','ALA']),('MEIO 01',['VOL','MC']),('MEIO 02',['VOL','MC']),('MEIO 03',['MC','MEI']),('MEIO 04',['MC','MEI']),('MEIO 05',['ME','PE']),('MEIO 06',['MD','PD']),('MEIO 07',['MEI','ME','MD']),('ATA 01',['PE','PD']),('ATA 02',['PE','CA']),('ATA 03',['PD','CA']),('ATA 04',['CA']),('ATA 05',['CA']),('ATA 06',['PD','CA']),('ATA 07',['PE','CA'])]
ACHIEVEMENTS=[('primeiro_jogo','Estreia','Jogue sua primeira partida.'),('sete_a_zero','Sete a Zero','Vença uma partida por 7 a 0.'),('campeao','Campeão','Conquiste um título.'),('colecionador','Colecionador','Monte 10 escalações.'),('online','Online','Jogue uma partida multiplayer.'),('artilheiro','Artilheiro','Marque 10 gols no seu histórico.')]

def get_elenco(selecao):
    return [{'id':f'{selecao}-{i}','nome':nome,'posicoes':posicoes,'numero':i} for i,(nome,posicoes) in enumerate(MODELO_ELENCO,1)]

def get_db():
    if 'db' not in g:
        g.db=sqlite3.connect(DATABASE);g.db.row_factory=sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(_=None):
    db=g.pop('db',None)
    if db:db.close()

def init_db():
    db=get_db()
    db.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS games (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,mode TEXT,score_for INTEGER DEFAULT 0,score_against INTEGER DEFAULT 0,champion INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    db.execute('CREATE TABLE IF NOT EXISTS achievements (user_id INTEGER,code TEXT,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,PRIMARY KEY(user_id,code))')
    db.execute('CREATE TABLE IF NOT EXISTS friends (user_id INTEGER,friend_id INTEGER,status TEXT DEFAULT "pending",PRIMARY KEY(user_id,friend_id))')
    db.execute('CREATE TABLE IF NOT EXISTS rooms (code TEXT PRIMARY KEY,owner_id INTEGER,mode TEXT,players TEXT,started INTEGER DEFAULT 0,created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)')
    db.commit()

def login_required(fn):
    @wraps(fn)
    def wrapper(**kwargs):return fn(**kwargs) if 'user_id' in session else redirect(url_for('login'))
    return wrapper

def grant(code):
    if 'user_id' not in session:return
    db=get_db();db.execute('INSERT OR IGNORE INTO achievements(user_id,code) VALUES(?,?)',(session['user_id'],code));db.commit()

def save_game(mode,score_for,score_against,champion=False):
    if 'user_id' not in session:return
    db=get_db();db.execute('INSERT INTO games(user_id,mode,score_for,score_against,champion) VALUES(?,?,?,?,?)',(session['user_id'],mode,score_for,score_against,int(champion)));db.commit();grant('primeiro_jogo')
    if score_for>=7 and score_against==0:grant('sete_a_zero')
    if champion:grant('campeao')
    if mode=='online':grant('online')
    if db.execute('SELECT COUNT(*) c FROM games WHERE user_id=?',(session['user_id'],)).fetchone()['c']>=10:grant('colecionador')
    if db.execute('SELECT COALESCE(SUM(score_for),0) g FROM games WHERE user_id=?',(session['user_id'],)).fetchone()['g']>=10:grant('artilheiro')

def montar_posicoes(formacao,escalacao):
    usados={};resultado=[]
    for codigo in FORMACOES.get(formacao,FORMACOES['4-3-3']):
        usados[codigo]=usados.get(codigo,0)+1;key=f'{codigo}_{usados[codigo]}'
        resultado.append({'key':key,'codigo':codigo,'jogador':escalacao.get(key)})
    return resultado

def montar_linhas_campo(formacao,posicoes):
    por_codigo={}
    for pos in posicoes:por_codigo.setdefault(pos['codigo'],[]).append(pos)
    linhas=[]
    for linha in CAMPO_LINHAS.get(formacao,CAMPO_LINHAS['4-3-3']):
        atual=[]
        for codigo in linha:
            if por_codigo.get(codigo):atual.append(por_codigo[codigo].pop(0))
        linhas.append(atual)
    return linhas

def jogadores_da_selecao(selecao,escalacao):
    usados={p.get('id') for p in escalacao.values() if p}
    return [{**j,'escolhido':j['id'] in usados} for j in get_elenco(selecao)]

def selecoes_usadas():return list(session.get('selecoes_usadas',[]))

def novo_sorteio():
    usadas=set(selecoes_usadas());disponiveis=[s for s in SELECOES if s not in usadas]
    if not disponiveis:disponiveis=SELECOES[:]
    return {'dado':random.randint(1,6),'selecao':random.choice(disponiveis),'copa':random.choice(COPAS)}

def trocar(tipo):
    atual=session.get('sorteio') or novo_sorteio();usadas=set(selecoes_usadas())
    if tipo=='selecao':
        disponiveis=[s for s in SELECOES if s not in usadas and s!=atual['selecao']];selecao=random.choice(disponiveis or [s for s in SELECOES if s!=atual['selecao']])
        return {'dado':random.randint(1,6),'selecao':selecao,'copa':atual['copa']}
    return {'dado':random.randint(1,6),'selecao':atual['selecao'],'copa':random.choice([c for c in COPAS if c!=atual['copa']])}

@app.route('/')
def index():return redirect(url_for('dashboard' if 'user_id' in session else 'login'))

@app.route('/cadastro',methods=['GET','POST'])
def register():
    if request.method=='POST':
        username=request.form.get('username','').strip();password=request.form.get('password','');confirm=request.form.get('confirm_password','')
        if not username or not password or not confirm:flash('Preencha todos os campos.','error')
        elif len(username)<3:flash('O usuário precisa ter pelo menos 3 caracteres.','error')
        elif len(password)<6:flash('A senha precisa ter pelo menos 6 caracteres.','error')
        elif password!=confirm:flash('As senhas não coincidem.','error')
        else:
            try:
                db=get_db();db.execute('INSERT INTO users(username,password_hash) VALUES(?,?)',(username,generate_password_hash(password)));db.commit();flash('Conta criada.','success');return redirect(url_for('login'))
            except sqlite3.IntegrityError:flash('Esse nome de usuário já está em uso.','error')
    return render_template('cadastro.html')

@app.route('/login',methods=['GET','POST'])
def login():
    if request.method=='POST':
        username=request.form.get('username','').strip();password=request.form.get('password','');user=get_db().execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        if user is None or not check_password_hash(user['password_hash'],password):flash('Usuário ou senha incorretos.','error')
        else:session.clear();session['user_id']=user['id'];session['username']=user['username'];return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/dashboard')
@login_required
def dashboard():
    db=get_db();stats=db.execute('SELECT COUNT(*) games,COALESCE(SUM(score_for),0) goals,COALESCE(SUM(champion),0) titles FROM games WHERE user_id=?',(session['user_id'],)).fetchone();ach=db.execute('SELECT COUNT(*) c FROM achievements WHERE user_id=?',(session['user_id'],)).fetchone()['c']
    return render_template('dashboard.html',username=session['username'],stats=stats,ach=ach)

@app.route('/desafio',methods=['GET','POST'])
@login_required
def desafio():
    if request.method=='POST':
        session['partida']={'modo':request.form.get('modo','normal'),'formacao':request.form.get('formacao','4-3-3'),'estilo':request.form.get('estilo','equilibrado')}
        for key in ('sorteio','escalacao','jogador_selecionado','resultado'):session.pop(key,None)
        session['selecoes_usadas']=[];return redirect(url_for('partida'))
    return render_template('desafio.html')

@app.route('/partida',methods=['GET','POST'])
@login_required
def partida():
    cfg=session.get('partida')
    if not cfg:return redirect(url_for('desafio'))
    if request.method=='POST':
        acao=request.form.get('acao','sortear');escalacao=dict(session.get('escalacao',{}))
        if acao=='sortear':
            if len(escalacao)<11:session['sorteio']=novo_sorteio();session.pop('jogador_selecionado',None)
        elif acao=='selecionar_jogador' and session.get('sorteio'):
            jogador_id=request.form.get('jogador');jogadores=get_elenco(session['sorteio']['selecao']);escolhido=next((j for j in jogadores if j['id']==jogador_id),None)
            if escolhido and escolhido['id'] not in {p.get('id') for p in escalacao.values() if p}:session['jogador_selecionado']=escolhido
        elif acao=='escolher' and session.get('sorteio') and session.get('jogador_selecionado'):
            posicao=request.form.get('posicao');jogador=session['jogador_selecionado'];posicoes=montar_posicoes(cfg['formacao'],escalacao);alvo=next((p for p in posicoes if p['key']==posicao),None)
            if alvo and alvo['jogador'] is None and alvo['codigo'] in jogador.get('posicoes',[]):
                jogador={**jogador,'selecao':session['sorteio']['selecao'],'copa':session['sorteio']['copa'],'posicao':alvo['key']};escalacao[posicao]=jogador;session['escalacao']=escalacao
                usadas=selecoes_usadas()
                if jogador['selecao'] not in usadas:usadas.append(jogador['selecao'])
                session['selecoes_usadas']=usadas;session.pop('jogador_selecionado',None);session['sorteio']=None
        elif acao=='simular' and len(escalacao)>=11:
            base={'defensivo':(2,1),'equilibrado':(3,1),'ofensivo':(4,2)}.get(cfg['estilo'],(3,1));qualidade=sum(96-((p['numero']*3)%13) for p in escalacao.values() if p);media=qualidade/11;gf=max(0,random.randint(base[0],base[0]+4)+round((media-90)/3));ga=max(0,random.randint(0,3)-round((media-90)/8));champion=gf>ga;save_game(cfg['modo'],gf,ga,champion);session['resultado']={'gf':gf,'ga':ga,'champion':champion,'formacao':cfg['formacao'],'escalacao':escalacao};return redirect(url_for('resultado'))
    escalacao=dict(session.get('escalacao',{}));sorteio=session.get('sorteio');jogador_selecionado=session.get('jogador_selecionado');posicoes=montar_posicoes(cfg['formacao'],escalacao);linhas=montar_linhas_campo(cfg['formacao'],posicoes);jogadores=jogadores_da_selecao(sorteio['selecao'],escalacao) if sorteio else [];completo=len(escalacao)>=11;ultimo_jogador=next(reversed(escalacao.values()),None) if escalacao else None
    return render_template('partida.html',username=session['username'],modo=cfg['modo'],formacao=cfg['formacao'],estilo=cfg['estilo'],sorteio=sorteio,posicoes=posicoes,linhas_campo=linhas,jogadores=jogadores,jogador_selecionado=jogador_selecionado,completo=completo,selecoes_usadas=selecoes_usadas(),ultimo_jogador=ultimo_jogador)

@app.route('/resultado')
@login_required
def resultado():
    resultado=session.get('resultado')
    if not resultado:return redirect(url_for('dashboard'))
    return render_template('resultado.html',r=resultado)

@app.route('/desafio-do-dia',methods=['GET','POST'])
@login_required
def daily():
    today=date.today().isoformat();db=get_db();played=db.execute('SELECT id FROM games WHERE user_id=? AND mode=? AND date(created_at)=?',(session['user_id'],'daily',today)).fetchone()
    if request.method=='POST' and not played:
        gf=random.randint(0,9);ga=random.randint(0,4);save_game('daily',gf,ga,gf>ga);return redirect(url_for('daily'))
    board=db.execute('SELECT u.username,MAX(g.score_for-g.score_against) saldo,MAX(g.score_for) gols FROM games g JOIN users u ON u.id=g.user_id WHERE g.mode="daily" AND date(g.created_at)=? GROUP BY g.user_id ORDER BY saldo DESC,gols DESC LIMIT 20',(today,)).fetchall();return render_template('daily.html',played=played,board=board)

@app.route('/perfil',methods=['GET','POST'])
@login_required
def perfil():
    db=get_db()
    if request.method=='POST':
        username=request.form.get('username','').strip()
        if username and username!=session['username']:
            try:db.execute('UPDATE users SET username=? WHERE id=?',(username,session['user_id']));db.commit();session['username']=username
            except sqlite3.IntegrityError:flash('Apelido já existe.','error')
    stats=db.execute('SELECT COUNT(*) games,COALESCE(SUM(score_for),0) goals,COALESCE(SUM(champion),0) titles,COALESCE(SUM(score_for>=score_against),0) wins FROM games WHERE user_id=?',(session['user_id'],)).fetchone();achievements=db.execute('SELECT code FROM achievements WHERE user_id=?',(session['user_id'],)).fetchall();return render_template('perfil.html',stats=stats,achievements=achievements,all_ach=ACHIEVEMENTS)

@app.route('/conquistas')
@login_required
def conquistas():return redirect(url_for('perfil'))

@app.route('/artilharia')
@login_required
def artilharia():
    goals=get_db().execute('SELECT COALESCE(SUM(score_for),0) g FROM games WHERE user_id=?',(session['user_id'],)).fetchone()['g'];return render_template('artilharia.html',goals=goals)

@app.route('/livre',methods=['GET','POST'])
@login_required
def livre():
    selected=list(session.get('livre',[]))
    if request.method=='POST':
        if request.form.get('clear'):selected=[]
        else:
            value=request.form.get('item')
            if value and value in SELECOES+COPAS and value not in selected:selected.append(value)
        session['livre']=selected
    return render_template('livre.html',items=SELECOES+COPAS,selected=selected,ready=len(selected)>=11)

@app.route('/multiplayer',methods=['GET','POST'])
@login_required
def multiplayer():
    db=get_db()
    if request.method=='POST':
        action=request.form.get('action')
        if action=='create':
            code=secrets.token_hex(3).upper();players=[{'id':session['user_id'],'name':session['username']}];db.execute('INSERT INTO rooms(code,owner_id,mode,players) VALUES(?,?,?,?)',(code,session['user_id'],request.form.get('mode','final'),json.dumps(players)));db.commit();return redirect(url_for('room',code=code))
        if action=='join':
            code=request.form.get('code','').upper();room_row=db.execute('SELECT * FROM rooms WHERE code=?',(code,)).fetchone()
            if room_row:
                players=json.loads(room_row['players'])
                if not any(x['id']==session['user_id'] for x in players):players.append({'id':session['user_id'],'name':session['username']});db.execute('UPDATE rooms SET players=? WHERE code=?',(json.dumps(players),code));db.commit()
                return redirect(url_for('room',code=code))
            flash('Sala não encontrada.','error')
    rooms=db.execute('SELECT code,mode,players FROM rooms WHERE started=0 ORDER BY created_at DESC LIMIT 20').fetchall();return render_template('multiplayer.html',rooms=rooms)

@app.route('/sala/<code>',methods=['GET','POST'])
@login_required
def room(code):
    db=get_db();room_row=db.execute('SELECT * FROM rooms WHERE code=?',(code.upper(),)).fetchone()
    if not room_row:return redirect(url_for('multiplayer'))
    players=json.loads(room_row['players'])
    if request.method=='POST' and request.form.get('action')=='start' and room_row['owner_id']==session['user_id']:
        db.execute('UPDATE rooms SET started=1 WHERE code=?',(code.upper(),));db.commit();return redirect(url_for('room',code=code))
    return render_template('room.html',room=room_row,players=players,is_owner=room_row['owner_id']==session['user_id'])

@app.route('/logout')
def logout():session.clear();return redirect(url_for('login'))

with app.app_context():init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
