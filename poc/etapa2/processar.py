import sys,json,re,hashlib,datetime as dt,argparse,copy
from pathlib import Path
from lxml import html
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coleta_poc import slug,txt
ROOT=Path(__file__).resolve().parent

def titlekey(s):
 s=slug(s)
 if s.startswith('escola-do-rock'):return 'escola-do-rock'
 return s

def venuekey(s):
 s=slug(s).replace('tenis-clube','tenis-club')
 if 'ecovilla' in s:return 'ecovilla-ri-happy'
 # Theater names identify the venue; shopping and neighborhood suffixes are aliases.
 for k in ['teatro-dos-quatro','teatro-das-artes','teatro-henriqueta-brieba','teatro-dos-grandes-atores','teatros-da-barra','teatro-fashion-mall','teatro-brigitte-blair','teatro-clara-nunes','teatro-miguel-falabella','palquinho-ipanema','cine-teatro-joia']:
  if k in s:return k
 return s

def times(s,date):
 # First isolate a date-specific clause before extracting clocks.
 if re.search(r'\d{1,2}/\d{2}\s*[–-]',s):
  token=f'{int(date[8:]):02d}/{date[5:7]}'
  m=re.search(re.escape(token)+r'\s*[–-]\s*(.*?)(?=\s+e\s+\d{1,2}/\d{2}|$)',s)
  if not m:return []
  s=m[1]
 elif ';' in s:s=s.split(';',1)[1]
 found=re.findall(r'(?<!\d)(\d{1,2})h(\d{2})?(?!\d)',s)
 clocks=[f'{int(h):02d}:{m or "00"}' for h,m in found if int(h)<24]
 if 'Turno:' in s:return clocks[::2]
 if re.search(r'\bdas?\s+\d{1,2}h',s) and ' às ' in s:return clocks[:1]
 return list(dict.fromkeys(clocks))

def walk(o):
 if isinstance(o,list):
  for v in o:yield from walk(v)
 elif isinstance(o,dict):
  yield o
  for v in o.values():
   if isinstance(v,(dict,list)):yield from walk(v)

def official_events(folder,logs,seeds):
 events=[]
 for log in logs:
  log['sessoes_extraidas']=0
  if 'snapshot' not in log:continue
  doc=html.fromstring((folder/log['snapshot']).read_bytes())
  if 'clubinhodeofertas.com.br' in log['url']:
   for block in doc.xpath('//script[@type="application/ld+json"]/text()'):
    try:objects=walk(json.loads(block))
    except ValueError:continue
    for e in objects:
     typ=e.get('@type',[]);typ=[typ] if isinstance(typ,str) else typ
     if not any(str(x).endswith('Event') for x in typ):continue
     start=e.get('startDate','')
     if not re.match(r'\d{4}-\d\d-\d\dT\d\d:\d\d',start):continue
     loc=e.get('location') or {};offer=e.get('offers') or {};offer=offer[0] if isinstance(offer,list) and offer else offer
     addr=loc.get('address') or {};price=offer.get('lowPrice',offer.get('price'))
     events.append(dict(nome=e.get('name'),data=start[:10],hora=start[11:16],fim=str(e.get('endDate',''))[11:16] or None,local=loc.get('name'),endereco=addr.get('streetAddress'),cidade=addr.get('addressLocality'),preco=('A partir de R$ '+str(price).replace('.',',')) if price is not None else None,idade=e.get('typicalAgeRange'),url=e.get('url') or log['url'],tipo='plataforma',timestamp=log['verificado_em'],evidencia={'url':log['url'],'snapshot':log['snapshot'],'sha256':log['sha256'],'trecho':{k:e.get(k) for k in ['name','startDate','endDate','location','offers']}},status_evento=e.get('eventStatus','')))
     log['sessoes_extraidas']+=1
  else:
   for box in doc.xpath('//div[contains(@class,"fusion-column-wrapper")]'):
    ps=box.xpath('./div[contains(@class,"fusion-title")]/p')
    if len(ps)<2:continue
    title=txt(ps[0]); dates=txt(ps[1]);s=txt(box);age=re.search(r'Classificação:\s*(Livre|\d+ anos)',s,re.I)
    selected=[r for r in seeds if titlekey(r['nome'])==titlekey(title)]
    for date in sorted(set(r['data'] for r in selected)):
     # Calendar bounds are explicit in this existing official agenda. Never create days not in the seed set.
     day=int(date[8:]);month=int(date[5:7]);m=re.match(r'(\d{1,2}) de (novembro|dezembro)(?: de 2026)?\s*[|(]',dates)
     if m:
      if day!=int(m[1]) or month!={'novembro':11,'dezembro':12}[m[2]]:continue
     elif titlekey(title)=='sai-da-tela-micaela':
      if not ('17 de outubro a 08 de novembro' in dates and date<='2026-11-08' and dt.date.fromisoformat(date).weekday() in [5,6]):continue
     elif titlekey(title)=='escola-do-rock':
      if not ('14 de novembro a 13 de dezembro' in dates and '2026-11-14'<=date<='2026-12-13' and dt.date.fromisoformat(date).weekday() in [5,6]):continue
     else:continue
     hs=['15:00'] if titlekey(title)=='escola-do-rock' else times(dates,date)
     for h in hs:
      clocks=re.findall(r'(?<!\d)(\d{1,2})h(\d{2})?(?!\d)',dates)
      clocks=[f'{int(a):02d}:{b or "00"}' for a,b in clocks]
      end=None
      if 'Turno:' in dates and h in clocks and clocks.index(h)+1<len(clocks):end=clocks[clocks.index(h)+1]
      elif re.search(r'\bdas?\s+\d{1,2}h',dates) and len(clocks)==2:end=clocks[1]
      events.append(dict(nome=title,data=date,hora=h,fim=end,local='EcoVilla Ri Happy',endereco='Rua Jardim Botânico, 1008',cidade='Rio de Janeiro',preco='Gratuito' if 'gratuito' in s.lower() else None,idade=age[1] if age else None,url=log['url'],tipo='organizador',timestamp=log['verificado_em'],evidencia={'url':log['url'],'snapshot':log['snapshot'],'sha256':log['sha256'],'trecho':{'titulo':title,'data_hora':dates,'idade':age[1] if age else None,'gratuito':'gratuito' in s.lower()}},status_evento=''))
      log['sessoes_extraidas']+=1
  if not log['sessoes_extraidas']:log['alerta']='ZERO SESSÕES ESTRUTURADAS / SEM CONFIRMAÇÃO'
 return events

def identity(r):return '|'.join([titlekey(r['nome']),r['data'],r.get('hora') or '?',venuekey(r['local'])])
def dedup(rows):
 seen={};removed=[]
 for r in rows:
  k=identity(r)
  if k in seen:
   target=seen[k];target['ids_anteriores']=sorted(set(target['ids_anteriores']+r['ids_anteriores']));target['fontes']=sorted(set(target['fontes']+r['fontes']));removed.append({'id_descartado':r['id_anterior'],'id_canonico':target['id'],'motivo':'mesmo título, data, hora e local normalizados'})
  else:r['id']='S-'+hashlib.sha256(k.encode()).hexdigest()[:10];seen[k]=r
 return sorted(seen.values(),key=lambda r:(r['data'],r.get('hora') or '',r['nome'])),removed

def process(folder):
 base=json.loads((ROOT/'sementes.json').read_text());seeds=base['candidatos'];logs=json.loads((folder/'coleta.json').read_text())['fontes'];evs=official_events(folder,logs,seeds);rows=[];corrections=[]
 for r in seeds:
  local=venuekey(r['local']);matches=[e for e in evs if titlekey(e['nome'])==titlekey(r['nome']) and e['data']==r['data'] and venuekey(e['local'])==local]
  if r['fonte']=='Clubinho de Ofertas':oldtimes=[r['data_texto'][11:16]]
  else:oldtimes=times(r['data_texto'],r['data'])
  officialtimes=sorted(set(e['hora'] for e in matches));effective=oldtimes or officialtimes or [None]
  if len(oldtimes)==1 and len(officialtimes)==1 and oldtimes!=officialtimes:
   corrections.append({'id_anterior':r['id'],'nome':r['nome'],'data':r['data'],'antes':oldtimes,'depois':officialtimes,'motivo':'Horário da fonte oficial prevalece sobre agenda secundária'});effective=officialtimes
  for h in effective:
   confirmed=[e for e in matches if e['hora']==h];confirmed.sort(key=lambda e:0 if e['tipo']=='organizador' else 1)
   chosen=confirmed[0] if confirmed else None
   row=dict(nome=r['nome'],data=r['data'],hora=h,fim=None,local=r['local'],preco=None,idade=None,url=r.get('url_confirmacao') or r['url'],ids_anteriores=[r['id']],id_anterior=r['id'],fontes=[r['fonte']],evidencias=[],motivo='',status='pendentes_de_confirmacao')
   if chosen:
    for field in ['nome','local','endereco','fim','url']:row[field]=chosen.get(field)
    for field in ['preco','idade']:
     row[field]=next((e[field] for e in confirmed if e.get(field) is not None),None)
    row['evidencias']=[e['evidencia'] for e in confirmed];row['verificado_em']=max(e['timestamp'] for e in confirmed);row['status']='prontos_para_aprovacao';row['motivo']='Data, horário e local confirmados em '+chosen['tipo'];row['fontes']+=sorted(set(e['tipo'] for e in confirmed))
    if any('Cancelled' in e['status_evento'] for e in confirmed):row['status']='descartados';row['motivo']='Cancelamento explícito na plataforma'
   else:
    log=next((l for l in logs if l['url']==r.get('url_confirmacao')),None)
    row['preco_referencia_secundaria']=r['preco'];row['motivo']='Horário ausente na agenda secundária' if h is None else 'Sessão exata não confirmada na página oficial/plataforma'
    if log and 'erro' in log:row['motivo']+='; '+log['erro']
    elif log and not log.get('sessoes_extraidas'):row['motivo']+='; página acessível sem sessões extraíveis'
   if r['data']<dt.datetime.now(dt.timezone(dt.timedelta(hours=-3))).date().isoformat():row['status']='descartados';row['motivo']='Sessão expirada'
   rows.append(row)
 unique,dups=dedup(rows)
 # Review near matches without merging them: same title/date, different venue/time are distinct sessions.
 groups={s:[r for r in unique if r['status']==s] for s in ['prontos_para_aprovacao','pendentes_de_confirmacao','descartados']}
 for item in base['rejeitados']:groups['descartados'].append(dict(item,status='descartados',tipo='expirado_na_primeira_coleta'))
 for d in dups:groups['descartados'].append(dict(d,status='descartados',tipo='duplicata_consolidada'))
 result={'publicacao_automatica':False,'entrada_registros':len(seeds),'sessoes_antes_dedup':len(rows),'sessoes_unicas':len(unique),'duplicatas':dups,'correcoes':corrections,'fontes':logs,'grupos':groups}
 (folder/'editorial.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({'rodada':str(folder),'grupos':{k:len(v) for k,v in groups.items()},'correcoes':len(corrections),'duplicatas':len(dups)},ensure_ascii=False));return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('folder',type=Path);process(p.parse_args().folder)
