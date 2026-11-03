"""Coleta de candidatos: nunca escreve na base pública. Python 3 + lxml."""
import argparse,datetime as dt,hashlib,json,re,unicodedata,urllib.request,concurrent.futures
from pathlib import Path
from lxml import html
SOURCES={'Clubinho de Ofertas':'https://clubinhodeofertas.com.br/rio-de-janeiro','Pequenos no Rio':'https://pequenosnorio.com.br/programacao-infantil-de-novembro-de-2026-no-rio-de-janeiro/','EcoVilla Ri Happy':'https://ecovillarihappy.com.br/programacao/'}
def norm(s):return ' '.join(s.split())
def slug(s):return re.sub(r'[^a-z0-9]+','-',unicodedata.normalize('NFKD',s.casefold()).encode('ascii','ignore').decode()).strip('-')
def txt(e):return norm(' '.join(e.itertext()))
def fetch(u):
 with urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'Roteirinho/1.2 public agenda feasibility'}),timeout=25) as r:return r.read(),r.status,r.url

def extract(name,b,url,today):
 t=html.fromstring(b); rows=[]; rejected=[]
 if name=='Clubinho de Ofertas':
  # Dates without month are incomplete: verify detail pages before admitting sessions.
  for a in t.xpath('//article[.//h3]'):
   title=txt(a.xpath('.//h3')[0]); ps=a.xpath('.//p'); texts=[txt(p) for p in ps]; link=a.xpath('.//a/@href')
   if len(texts)<3 or not link:continue
   rows.append(dict(nome=title,data_texto=texts[0],local=texts[1],preco=texts[2],idade=None,url=link[0],data=None,pendencias=['Data sem mês no cartão: confirmar na página de detalhe'],confianca='incompleto'))
 elif name=='Pequenos no Rio':
  for h in t.xpath('//h3'):
   bits=[]
   for e in h.itersiblings():
    if e.tag in ['h2','h3']:break
    bits.append(txt(e))
   s=' '.join(bits); title=txt(h)
   # Admit only explicit single/multiple November dates in theatre listings, never expand ranges as daily sessions.
   m=re.search(r'Em cartaz (?:somente dia|dias) ([\d ,e]+) de novembro (?:no|na|nos) (.+?)\. Horário: (.+?)(?: Ingressos|$)',s)
   if not m:continue
   dates=re.findall(r'\d+',m[1]);price=re.search(r'Ingressos online antecipados: (.+?)\.',s)
   for day in dates:
    date=f'2026-11-{int(day):02d}'
    if date<today:rejected.append({'nome':title,'data':date,'motivo':'expirado'});continue
    rows.append(dict(nome=title,data=date,data_texto=m[1]+' de novembro de 2026; '+m[3],local=m[2],preco=price[1] if price else None,idade=None,url=url,pendencias=['Fonte secundária; confirmar organizador','Faixa etária não informada'],confianca='secundaria',evidencia=s[:900]))
 elif name=='EcoVilla Ri Happy':
  for box in t.xpath('//div[contains(@class,"fusion-column-wrapper")]'):
   ps=box.xpath('./div[contains(@class,"fusion-title")]/p')
   if len(ps)<2:continue
   title=txt(ps[0]); date_text=txt(ps[1]);m=re.match(r'(\d{1,2}) de (novembro|dezembro)(?: de (2026))?\s*[|(]',date_text)
   if not m:continue
   date=f'2026-{11 if m[2]=="novembro" else 12:02d}-{int(m[1]):02d}'
   s=txt(box);age=re.search(r'Classificação:\s*(Livre|\d+ anos)',s,re.I)
   rows.append(dict(nome=title,data=date,data_texto=date_text,local='EcoVilla Ri Happy — Rua Jardim Botânico, 1008, Rio de Janeiro',preco='Gratuito' if 'gratuito' in s.lower() else None,idade=age[1] if age else None,url=url,confianca='primaria_ano_explicito' if m[3] else 'primaria_ano_contextual',pendencias=[] if m[3] else ['Ano contextual da agenda; confirmar antes de publicar'],evidencia=s[:900]))
 return rows,rejected

def run(out):
 out.mkdir(parents=True,exist_ok=True);today=dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat();stamp=dt.datetime.now(dt.timezone.utc).isoformat(); allrows=[];logs=[];reject=[]
 for name,url in SOURCES.items():
  log={'fonte':name,'url':url,'verificado_em':stamp}
  try:
   b,status,final=fetch(url);fn=slug(name)+'.html';(out/fn).write_bytes(b);rows,rej=extract(name,b,url,today);reject.extend(rej)
   log.update(http=status,bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),snapshot=fn,extraidos=len(rows),metodo='HTML visível; sem JSON-LD')
   if name=='Clubinho de Ofertas':
    # Bounded pilot: follow the first 12 distinct offers and parse dated Event sessions.
    urls=list(dict.fromkeys(r['url'] for r in rows))[:12]; details=[]
    def detail(u):
     try:
      body,code,final=fetch(u); fn='detail-'+hashlib.sha256(u.encode()).hexdigest()[:12]+'.html';(out/fn).write_bytes(body)
      doc=html.fromstring(body); events=[]
      def walk(o):
       if isinstance(o,list):
        for v in o:yield from walk(v)
       elif isinstance(o,dict):
        if o.get('@type')=='Event':yield o
        for v in o.values():
         if isinstance(v,(dict,list)):yield from walk(v)
      for block in doc.xpath('//script[@type="application/ld+json"]/text()'):
       for e in walk(json.loads(block)):
        start=e.get('startDate',''); loc=e.get('location',{}); offer=e.get('offers',{});offer=offer[0] if isinstance(offer,list) and offer else offer
        if start[:10]<today:continue
        events.append(dict(nome=e['name'],data=start[:10],data_texto=start,local=loc.get('name',''),preco=str(offer.get('price',offer.get('lowPrice','Não informado'))),idade=None,url=e.get('url',u),confianca='plataforma_sessao_explicita',pendencias=['Faixa etária a confirmar; preço pode variar por lote'],evidencia=json.dumps(e,ensure_ascii=False)[:1800]))
      return events,dict(url=u,http=code,sha256=hashlib.sha256(body).hexdigest(),snapshot=fn,sessoes=len(events))
     except Exception as exc:return [],dict(url=u,erro=str(exc))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
     for events,entry in pool.map(detail,urls):details.extend(events);log.setdefault('detalhes',[]).append(entry)
    rows=details;log['extraidos']=len(rows);log['metodo']='Descoberta HTML + sessões JSON-LD nas primeiras 12 ofertas distintas'
   for row in rows:row.update(fonte=name,verificado_em=stamp);allrows.append(row)
  except Exception as e:log.update(erro=str(e),alerta='FALHA DE COLETA')
  logs.append(log)
 seen={};duplicates=[]
 for r in allrows:
  key=(slug(r['nome']),r['data'],slug(r['local']))
  if key in seen:duplicates.append({'chave':list(key),'fonte':r['fonte']});continue
  r['id']=hashlib.sha256('|'.join(str(k) for k in key).encode()).hexdigest()[:12];seen[key]=r
 for l in logs:
  if l.get('extraidos')==0:l['alerta']='ZERO CANDIDATOS'
 result={'verificado_em':stamp,'publicacao_automatica':False,'fontes':logs,'candidatos':list(seen.values()),'duplicatas':duplicates,'rejeitados':reject}
 (out/'resultado.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'diretorio':str(out),'fontes':logs,'unicos':len(seen),'duplicatas':len(duplicates),'expirados':len(reject)},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);run(p.parse_args().out)
