import os,random,sqlite3
from functools import wraps
from flask import Flask,flash,g,redirect,render_template,request,session,url_for
from werkzeug.security import check_password_hash,generate_password_hash
BASE_DIR=os.path.dirname(os.path.abspath(__file__));DATABASE=os.path.join(BASE_DIR,'data.db')
app=Flask(__name__);app.config['SECRET_KEY']=os.environ.get('SECRET_KEY','dev-6a7-secret-key')
SELECOES=['Brasil','Argentina','França','Alemanha','Espanha','Itália','Portugal','Inglaterra','Uruguai','Holanda','Croácia','Bélgica'];COPAS=['Copa 1950','Copa 1954','Copa 1958','Copa 1962','Copa 1970','Copa 1982','Copa 1994','Copa 2002','Copa 2006','Copa 2010','Copa 2014','Copa 2018','Copa 2022']
FORMACOES={'4-3-3':['GOL','LE','ZAG','ZAG','LD','MC','MEI','MC','PE','CA','PD'],'4-4-2':['GOL','LE','ZAG','ZAG','LD','ME','MC','MC','MD','CA','CA'],'4-2-3-1':['GOL','LE','ZAG','ZAG','LD','VOL','VOL','PE','MEI','PD','CA'],'4-2-4':['GOL','LE','ZAG','ZAG','LD','VOL','VOL','PE','CA','CA','PD'],'3-5-2':['GOL','ZAG','ZAG','ZAG','ALA','MC','MEI','MC','ALA','CA','CA'],'5-3-2':['GOL','LE','ZAG','ZAG','ZAG','LD','MC','MEI','MC','CA','CA'],'4-5-1':['GOL','LE','ZAG','ZAG','LD','ME','MC','MEI','MC','MD','CA'],'3-4-3':['GOL','ZAG','ZAG','ZAG','ME','MC','MC','MD','PE','CA','PD']}
CAMPO_LINHAS={'4-3-3':[['PE','CA','PD'],['MC','MEI','MC'],['LE','ZAG','ZAG','LD'],['GOL']],'4-4-2':[['CA','CA'],['ME','MC','MC','MD'],['LE','ZAG','ZAG','LD'],['GOL']],'4-2-3-1':[['CA'],['PE','MEI','PD'],['VOL','VOL'],['LE','ZAG','ZAG','LD'],['GOL']],'4-2-4':[['PE','CA','CA','PD'],['VOL','VOL'],['LE','ZAG','ZAG','LD'],['GOL']],'3-5-2':[['CA','CA'],['ALA','MC','MEI','MC','ALA'],['ZAG','ZAG','ZAG'],['GOL']],'5-3-2':[['CA','CA'],['MC','MEI','MC'],['LE','ZAG','ZAG','ZAG','LD'],['GOL']],'4-5-1':[['CA'],['ME','MC','MEI','MC','MD'],['LE','ZAG','ZAG','LD'],['GOL']],'3-4-3':[['PE','CA','PD'],['ME','MC','MC','MD'],['ZAG','ZAG','ZAG'],['GOL']]}
MODELO_ELENCO=[('GOL 01',['GOL']),('GOL 02',['GOL']),('GOL 03',['GOL']),('DEF 01',['ZAG','LE']),('DEF 02',['ZAG']),('DEF 03',['ZAG','LD']),('DEF 04',['ZAG']),('DEF 05',['LE','ALA']),('DEF 06',['LD','ALA']),('MEIO 01',['VOL','MC']),('MEIO 02',['VOL','MC']),('MEIO 03',['MC','MEI']),('MEIO 04',['MC','MEI']),('MEIO 05',['ME','PE']),('MEIO 06',['MD','PD']),('ATA 01',['PE','PD']),('ATA 02',['PE','CA']),('ATA 03',['PD','CA']),('ATA 04',['CA']),('ATA 05',['CA']),('ATA 06',['PD','CA']),('ATA 07',['PE','CA']),('MEIO 07',['MEI','ME','MD'])]
def get_elenco(s):return [{'id':f'{s}-{i}','nome':f'{s} — {n}','posicoes':p} for i,(n,p) in enumerate(MODELO_ELENCO,1)]
def get_db():
 if 'db' not in g:g.db=sqlite3.connect(DATABASE);g.db.row_factory=sqlite3.Row
 return g.db
@app.teardown_appcontext
def close_db(_=None):
 db=g.pop('db',None)
 if db:db.close()
def init_db():get_db().execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)');get_db().commit()
def login_required(fn):
 @wraps(fn)
 def w(**kw):return fn(**kw) if 'user_id' in session else redirect(url_for('login'))
 return w
def montar_posicoes(f,e):
 r=[];c={}
 for x in FORMACOES.get(f,FORMACOES['4-3-3']):c[x]=c.get(x,0)+1;k=f'{x}_{c[x]}';r.append({'key':k,'codigo':x,'jogador':e.get(k)})
 return r
def montar_linhas_campo(f,p):
 d={}
 for x in p:d.setdefault(x['codigo'],[]).append(x)
 return [[d[x].pop(0) for x in l if d.get(x)] for l in CAMPO_LINHAS.get(f,CAMPO_LINHAS['4-3-3'])]
def preparar_jogadores(elenco,e,p,sel=None):
 usados=set(e.values());r=[]
 for n,j in enumerate(elenco,1):
  op=[x for x in p if x['codigo'] in j['posicoes']];r.append({**j,'numero':n,'escolhido':j['id'] in usados,'selecionado':j['id']==sel,'tem_posicao_livre':any(not x['jogador'] for x in op)})
 return r
def sorteio_novo():
 a=session.get('sorteio',{});op=[x for x in SELECOES if x!=a.get('selecao')] if a.get('selecao') else SELECOES
 return {'dado':random.randint(1,6),'selecao':random.choice(op),'copa':random.choice(COPAS)}
def trocar(tipo):
 a=session['sorteio'];s=random.choice([x for x in SELECOES if x!=a['selecao']]) if tipo=='selecao' else a['selecao'];c=random.choice([x for x in COPAS if x!=a['copa']]) if tipo=='copa' else a['copa'];return {'dado':random.randint(1,6),'selecao':s,'copa':c}
@app.route('/')
def index():return redirect(url_for('dashboard' if 'user_id' in session else 'login'))
@app.route('/cadastro',methods=['GET','POST'])
def register():
 if request.method=='POST':
  u=request.form.get('username','').strip();p=request.form.get('password','');cp=request.form.get('confirm_password','')
  if not u or not p or not cp:flash('Preencha todos os campos.','error')
  elif len(u)<3:flash('O usuário precisa ter pelo menos 3 caracteres.','error')
  elif len(p)<6:flash('A senha precisa ter pelo menos 6 caracteres.','error')
  elif p!=cp:flash('As senhas não coincidem.','error')
  else:
   try:db=get_db();db.execute('INSERT INTO users (username,password_hash) VALUES (?,?)',(u,generate_password_hash(p)));db.commit();flash('Conta criada. Agora faça login.','success');return redirect(url_for('login'))
   except sqlite3.IntegrityError:flash('Esse nome de usuário já está em uso.','error')
 return render_template('cadastro.html')
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  u=request.form.get('username','').strip();p=request.form.get('password','');user=get_db().execute('SELECT * FROM users WHERE username=?',(u,)).fetchone()
  if user is None or not check_password_hash(user['password_hash'],p):flash('Usuário ou senha incorretos.','error')
  else:session.clear();session['user_id']=user['id'];session['username']=user['username'];return redirect(url_for('dashboard'))
 return render_template('login.html')
@app.route('/dashboard')
@login_required
def dashboard():return render_template('dashboard.html',username=session['username'])
@app.route('/desafio',methods=['GET','POST'])
@login_required
def desafio():
 if request.method=='POST':session['partida']={'modo':request.form.get('modo','normal'),'formacao':request.form.get('formacao','4-3-3'),'estilo':request.form.get('estilo','equilibrado')};session.pop('sorteio',None);session.pop('escolhidos',None);session.pop('jogador_selecionado',None);session['rolagens_manuais']=0;session['pode_rerolar']=False;return redirect(url_for('partida'))
 return render_template('desafio.html')
@app.route('/partida',methods=['GET','POST'])
@login_required
def partida():
 cfg=session.get('partida')
 if not cfg:return redirect(url_for('desafio'))
 if request.method=='POST':
  acao=request.form.get('acao','sortear')
  if acao=='sortear':
   tinha=bool(session.get('sorteio'))
   if not tinha or session.get('rolagens_manuais',0)<3:session['sorteio']=sorteio_novo();session['rolagens_manuais']=session.get('rolagens_manuais',0)+(1 if tinha else 0);session['pode_rerolar']=True;session.pop('jogador_selecionado',None)
  elif acao in ('outra_selecao','outra_copa') and session.get('sorteio') and session.get('rolagens_manuais',0)<3:session['sorteio']=trocar('selecao' if acao=='outra_selecao' else 'copa');session['rolagens_manuais']+=1;session['pode_rerolar']=True;session.pop('jogador_selecionado',None)
  elif acao=='selecionar_jogador' and session.get('sorteio'):
   jid=request.form.get('jogador');elenco=get_elenco(session['sorteio']['selecao']);e=dict(session.get('escolhidos',{}))
   if any(j['id']==jid for j in elenco) and jid not in e.values():session['jogador_selecionado']=jid;session['pode_rerolar']=True
  elif acao=='escolher' and session.get('sorteio'):
   e=dict(session.get('escolhidos',{}));ch=request.form.get('posicao');jid=session.get('jogador_selecionado');elenco=get_elenco(session['sorteio']['selecao']);p=montar_posicoes(cfg['formacao'],e);j=next((x for x in elenco if x['id']==jid),None);pos=next((x for x in p if x['key']==ch),None)
   if j and pos and not pos['jogador'] and jid not in e.values() and pos['codigo'] in j['posicoes']:e[ch]=jid;session['escolhidos']=e;session.pop('jogador_selecionado',None);session['pode_rerolar']=True
 sorteio=session.get('sorteio');e=session.get('escolhidos',{});sel=session.get('jogador_selecionado');p=montar_posicoes(cfg['formacao'],e) if sorteio else [];linhas=montar_linhas_campo(cfg['formacao'],p) if sorteio else [];elenco=get_elenco(sorteio['selecao']) if sorteio else [];jogadores=preparar_jogadores(elenco,e,p,sel) if sorteio else [];js=next((j for j in jogadores if j['id']==sel),None)
 html=render_template('partida.html',username=session['username'],modo=cfg['modo'],formacao=cfg['formacao'],estilo=cfg['estilo'],sorteio=sorteio,posicoes=p,linhas_campo=linhas,jogadores=jogadores,jogador_selecionado=js,completo=len(e)>=11,rolagens_manuais=session.get('rolagens_manuais',0),pode_rerolar=session.get('pode_rerolar',False))
 html=html.replace('</style>','''</style><style>.reroll-main{display:none}.reroll-grid form:nth-child(2),.reroll-grid form:nth-child(3){display:none}.phase-selection .reroll-main{display:none}.phase-selection .reroll-grid form:nth-child(2),.phase-selection .reroll-grid form:nth-child(3){display:block}.phase-reroll .reroll-main{display:block}.phase-reroll .reroll-grid form:nth-child(2),.phase-reroll .reroll-grid form:nth-child(3){display:none}</style>''')
 html=html.replace('<body class="game-page">','<body class="game-page" id="partida-page">')
 html=html.replace('</body>','''<script>(function(){const box=document.querySelector('.score-title');const selected=document.querySelector('.details-panel .selected');const controls=document.querySelector('.reroll');if(!controls)return;const m=box&&box.textContent.match(/(\\d+)\\s*\\/\\s*11/);const count=m?parseInt(m[1],10):0;document.getElementById('partida-page').classList.add(selected?'phase-selection':(count>0?'phase-reroll':'phase-selection'));})();</script></body>''')
 return html
@app.route('/logout')
def logout():session.clear();return redirect(url_for('login'))
with app.app_context():init_db()
if __name__=='__main__':app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=True)
