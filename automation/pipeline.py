"""Daily public discovery -> durable editorial queue; never writes published events."""
import argparse,copy,datetime as dt,hashlib,json,re,unicodedata,urllib.request,concurrent.futures,os
from pathlib import Path
from urllib.parse import urljoin,urlparse
from lxml import html
TZ=dt.timezone(dt.timedelta(hours=-3))
SOURCES=[
 {'id':'clubinho','url':'https://clubinhodeofertas.com.br/rio-de-janeiro','place':None},
 {'id':'pequenos','url':'https://pequenosnorio.com.br/','place':None},
 {'id':'eco','url':'https://ecovillarihappy.com.br/programacao/','place':'EcoVilla Ri Happy'},
 {'id':'ccbb','url':'https://ccbb.com.br/rio-de-janeiro/ccbb-educativo/','place':'CCBB Rio — Rua Primeiro de Março, 66'},
 {'id':'amanha','url':'https://museudoamanha.org.br/pt/programacao','place':'Museu do Amanhã — Praça Mauá, 1'},
 {'id':'firjan','url':'https://casafirjan.com.br/agenda','place':'Casa Firjan — Rua Guilhermina Guinle, 211'},
]

def norm(s):return re.sub('[^a-z0-9]+','-',unicodedata.normalize('NFKD',s.lower()).encode('ascii','ignore').decode()).strip('-')
def titlekey(s):
 k=norm(s)
 return 'escola-do-rock' if k.startswith('escola-do-rock') else k

def venuekey(s):
 k=norm(s)
 if 'ecovilla' in k:return 'ecovilla-ri-happy'
 for v in ['teatro-dos-quatro','teatro-das-artes','teatro-henriqueta-brieba','teatro-dos-grandes-atores','teatros-da-barra','teatro-fashion-mall','teatro-brigitte-blair','teatro-clara-nunes','teatro-miguel-falabella','palquinho-ipanema','cine-teatro-joia']:
  if v in k:return v
 return k

def key(r):return '|'.join([titlekey(r['nome']),r.get('data') or '?',r.get('hora') or '?',venuekey(r.get('local') or ''),r.get('periodo') or ''])
def uid(r):return 'Q-'+hashlib.sha256(key(r).encode()).hexdigest()[:16]
def text(e):return ' '.join(' '.join(e.itertext()).split())
def visible(doc):
 d=copy.deepcopy(doc)
 for e in d.xpath('//script|//style|//nav|//footer'):e.drop_tree()
 return text(d)

def fetch(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Roteirinho/3.0 (+public children cultural agenda; bounded daily discovery)','Accept':'text/html'})
 with urllib.request.urlopen(req,timeout=18) as r:
  b=r.read(2500000);return b,r.status,r.url

def walk(x):
 if isinstance(x,list):
  for v in x:yield from walk(v)
 elif isinstance(x,dict):
  yield x
  for v in x.values():
   if isinstance(v,(list,dict)):yield from walk(v)

def structured(doc,url,place):
 rows=[]
 for s in doc.xpath('//script[contains(@type,"ld+json")]/text()'):
  try:objs=list(walk(json.loads(s)))
  except ValueError:continue
  for e in objs:
   typ=e.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
   if not any(str(t).endswith('Event') for t in typ):continue
   start=str(e.get('startDate') or '');end=str(e.get('endDate') or '');name=e.get('name')
   if not name or not re.match(r'^\d{4}-\d\d-\d\d',start):continue
   try:dt.date.fromisoformat(start[:10])
   except ValueError:continue
   loc=e.get('location') or {};loc=loc[0] if isinstance(loc,list) and loc else loc
   if not isinstance(loc,dict):loc={}
   locname=loc.get('name') or place
   # A Rio-specific source is required; do not infer another city from a generic title.
   addr=loc.get('address') or {};city=addr.get('addressLocality','') if isinstance(addr,dict) else ''
   if city and 'rio de janeiro' not in norm(city).replace('-',' '):continue
   age=e.get('typicalAgeRange');offer=e.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
   if not isinstance(offer,dict):offer={}
   price=offer.get('lowPrice',offer.get('price'))
   rows.append(dict(nome=str(name),data=start[:10],hora=start[11:16] if 'T' in start else None,local=locname or 'Local não informado',preco=str(price) if price is not None else None,idade=age,url=e.get('url') or url,validacao='sessao_plataforma',evidencia={'inicio':start,'fim':end,'local':locname,'preco':price},periodo='',cancelado='Cancelled' in str(e.get('eventStatus',''))))
 return rows

def candidates_html(source,doc,url,today):
 rows=[];s=visible(doc)
 if source['id']=='eco':
  for box in doc.xpath('//div[contains(@class,"fusion-column-wrapper")]'):
   ps=box.xpath('./div[contains(@class,"fusion-title")]/p')
   if len(ps)<2:continue
   title=text(ps[0]);dates=text(ps[1]);raw=text(box)
   if re.search(r'Classificação:\s*(16|18) anos',raw,re.I):continue
   # Exact dated items only. Ranges remain discovery links, never invented daily sessions.
   m=re.match(r'(\d{1,2}) de (novembro|dezembro)(?: de (\d{4}))?\s*(?:[|(]|às)',dates)
   if not m:continue
   month={'novembro':11,'dezembro':12}[m[2]];year=int(m[3] or today[:4])
   if not m[3] and ('de '+str(year)) not in s:continue
   date=f'{year}-{month:02d}-{int(m[1]):02d}'
   clocks=re.findall(r'(?<!\d)(\d{1,2})h(\d{2})?',dates);clocks=[f'{int(a):02d}:{b or "00"}' for a,b in clocks]
   clocks=clocks[::2] if 'Turno:' in dates else clocks[:1]
   for clock in clocks or [None]:
    age=re.search(r'Classificação:\s*(Livre|\d+ anos)',raw,re.I)
    rows.append(dict(nome=title,data=date,hora=clock,local=source['place'],preco='0' if 'gratuito' in raw.lower() else None,idade=age[1] if age else None,url=url,validacao='ano_explicito' if m[3] else 'ano_contextual_confirmar',periodo='',evidencia={'data_texto':dates}))
 elif source['id']=='ccbb':
  # Preserve program descriptions and schedules as pending program records when dates aren't fully specified.
  for term in ['Encontros na Cena','PEQUENOS EXPLORADORES','Ateliê Aberto','LABORATÓRIO DE MÚSICA']:
   headers=[h for h in doc.xpath('//h2') if text(h)==term]
   for h in headers[:1]:
    container=h
    for parent in h.iterancestors():
     raw=text(parent)
     if len(raw)>200 and len(raw)<6000:container=parent;break
    raw=text(container)
    rows.append(dict(nome=term+' — CCBB Educativo',data=None,hora=None,local=source['place'],preco='0',idade=None,url=url,validacao='programacao_sem_sessao_confirmada',periodo='',evidencia={'trecho':raw[:450]},pendencia='Confirmar calendário e sessão individual na programação oficial; não expandir recorrência sem período explícito'))
 elif source['id']=='firjan':
  for title,url2,start in re.findall(r'title:\s*"([^"]+)"\s*,\s*url:\s*"([^"]+)"\s*,\s*start:\s*"([^"]+)"',html.tostring(doc,encoding='unicode')):
   if not re.search(r'infant|crianç|família|brinc|bebê',title,re.I):continue
   rows.append(dict(nome=title.split('|',1)[-1].strip(),data=start[:10],hora=None,local=source['place'],preco=None,idade=None,url=url2,validacao='calendario_confirmar_hora',periodo='',evidencia={'rotulo':title,'start_calendario':start},pendencia='Horário do calendário difere do rótulo; confirmar página do evento'))
 return rows

def discover(source,out,today):
 log={'fonte':source['id'],'url':source['url'],'paginas':[],'tentativas':[],'erros':[]};rows=[];visited=set()
 def read(url):
  b,status,final=fetch(url);doc=html.fromstring(b);v=visible(doc)
  meta={'url':url,'url_final':final,'http':status,'sha256':hashlib.sha256(b).hexdigest(),'verificado_em':dt.datetime.now(dt.timezone.utc).isoformat()}
  log['tentativas'].append(meta)
  if len(v)<100 or ('/public/shiro/' in b.decode('utf-8','ignore') and len(v)<500):raise ValueError('Tela de verificação ou HTML sem agenda legível (mesmo que HTTP 200)')
  log['paginas'].append(meta);visited.add(url);return doc
 try:
  doc=read(source['url']);rows+=structured(doc,source['url'],source['place']);rows+=candidates_html(source,doc,source['url'],today)
  links=[]
  if source['id']=='clubinho':
   for a in doc.xpath('//article[.//h3]//a[@href]'):
    u=urljoin(source['url'],a.get('href')).split('?')[0]
    label=text(a.getparent())
    if re.search(r'/rio-de-janeiro/[^/]+-\d+$',u) and re.search(r'porquinh|princes|galinha|brinquedo|frozen|matilda|sonhos|saltimbancos|micaela|escola do rock|gatinhos|bento|natal|spidey|patrulh|cinderela|chapeuzinho|brilho|quitapena|menina|batuca|papa vento',label,re.I):links.append(u)
  elif source['id']=='pequenos':
   for a in doc.xpath('//a[@href]'):
    u=a.get('href');label=(u+' '+text(a)).lower()
    if 'programacao-infantil' in label and today[:4] in label:links.append(urljoin(source['url'],u))
  elif source['id']=='eco':
   # Direct ticket links are already offered by the organizer; homepage itself is the HTML adapter.
   pass
  if source['id']=='ccbb':
   # Add official programming entry, discover family-specific pages by card context.
   try:
    entry='https://ccbb.com.br/rio-de-janeiro/programacao/';catalog=read(entry)
    for a in catalog.xpath('//a[@href]'):
     u=a.get('href');ctx=text(a.getparent())
     if '/rio-de-janeiro/programacao/' in u and re.search(r'infant|crianç|todas as idades|família',ctx+' '+u,re.I):links.append(u)
   except Exception as e:log['erros'].append({'url':entry,'erro':str(e)[:240]})
  if source['id']=='pequenos':
   month=['janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'][int(today[5:7])-1]
   links.sort(key=lambda u:0 if (month+'-de-'+today[:4]) in u else 1)
  limit=18 if source['id']=='clubinho' else 2
  for u in list(dict.fromkeys(links))[:limit]:
   if urlparse(u).hostname!=urlparse(source['url']).hostname or u in visited:continue
   try:
    d=read(u);rows+=structured(d,u,source['place'])
    if source['id']=='pequenos':
     # Discover direct ticket URLs from dated articles; bound to 8 per article.
     tickets=list(dict.fromkeys(d.xpath('//a[contains(@href,"clubinhodeofertas.com.br/rio-de-janeiro/")]/@href')))[:8]
     for ticket in tickets:
      ticket=ticket.split('?')[0]
      if ticket in visited:continue
      try:dd=read(ticket);rows+=structured(dd,ticket,None)
      except Exception as e:log['erros'].append({'url':ticket,'erro':str(e)[:240]})
   except Exception as e:log['erros'].append({'url':u,'erro':str(e)[:240]})
 except Exception as e:log['erros'].append({'url':source['url'],'erro':str(e)[:240]})
 # Adult-specific offers are not children's candidates.
 rows=[r for r in rows if not re.search(r'confiss[oõ]es de adolescente|síndromes|além da vida',r['nome'],re.I)]
 for r in rows:r['fonte']=source['id']
 log.update(extraidos=len(rows),status='falha' if not log['paginas'] else 'parcial' if log['erros'] else 'ok')
 if not rows:log['alerta']='ZERO CANDIDATOS: revisar acesso, adequação infantil ou adaptador'
 return rows,log

def merge(queue,observed,stamp,today):
 existing={key(r['dados']):r for r in queue['candidatos']};stats={'novos':0,'reencontrados':0,'duplicatas_na_coleta':0,'expirados_novos':0};seen=set()
 before={r['id'] for r in existing.values()}
 for data in observed:
  k=key(data)
  if k in seen:stats['duplicatas_na_coleta']+=1;continue
  seen.add(k)
  if k in existing:
   r=existing[k];stats['reencontrados']+=1
  else:
   r={'id':uid(data),'dados':copy.deepcopy(data),'primeira_deteccao':stamp,'status_editorial':'aguardando_aprovacao','lote_origem':None};existing[k]=r;stats['novos']+=1
  r['ultima_deteccao']=stamp;r['observacao_atual']=data
 for r in existing.values():
  date=r['dados'].get('data')
  if date and date<today:
   if not r.get('expirado'):stats['expirados_novos']+=1
   r['expirado']=True
  else:r['expirado']=False
 assert before.issubset({r['id'] for r in existing.values()}),'Candidato anterior perdido'
 queue['candidatos']=sorted(existing.values(),key=lambda r:(r['dados'].get('data') or '9999',r['id']))
 stats.update(total=len(existing),preservados=len(before),pendentes_aprovacao=sum(r['status_editorial']=='aguardando_aprovacao' and not r['expirado'] for r in existing.values()),expirados_total=sum(r['expirado'] for r in existing.values()))
 queue.update(versao=3,atualizado_em=stamp,publicacao_automatica=False)
 return queue,stats

def run(queuefile,out):
 out.mkdir(parents=True,exist_ok=True);stamp=dt.datetime.now(dt.timezone.utc).isoformat();today=dt.datetime.now(TZ).date().isoformat()
 queue=json.loads(queuefile.read_text());records=[];logs=[]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
  for rows,log in pool.map(lambda s:discover(s,out,today),SOURCES):records+=rows;logs.append(log)
 queue,stats=merge(queue,records,stamp,today)
 report={'executado_em':stamp,'github_run_id':os.getenv('GITHUB_RUN_ID'),'fontes':logs,'metricas':stats,'publicacao':False,'lote_R2_alterado':False}
 queuefile.write_text(json.dumps(queue,ensure_ascii=False,indent=2)+'\n');(out/'relatorio.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 md='# Coleta recorrente — '+stamp+'\n\nNenhum evento publicado. Lote R2 preservado.\n\n'+str(stats)+'\n\n| Fonte | Páginas legíveis | Extraídos | Falhas | Estado |\n|---|---:|---:|---:|---|\n'
 for log in logs:
  md+=f"| {log['fonte']} | {len(log['paginas'])} | {log['extraidos']} | {len(log['erros'])} | {log['status']} |\n"
  if log.get('alerta'):print('::warning::'+log['fonte']+': '+log['alerta'])
 for log in logs:
  for e in log['erros']:md+='\n- '+log['fonte']+': '+e['url']+' — '+e['erro']
 (out/'relatorio.md').write_text(md+'\n');print(json.dumps(report,ensure_ascii=False))
 if not records:raise SystemExit('Falha útil: nenhuma fonte forneceu candidatos; fila anterior preservada.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--queue',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.queue,a.out)
