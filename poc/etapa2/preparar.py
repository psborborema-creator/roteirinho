import json,re,sys
from pathlib import Path
from lxml import html
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coleta_poc import slug,txt
root=Path(__file__).resolve().parents[1]
base=json.loads((root/'final-2/resultado.json').read_text())
t=html.fromstring((root/'final-2/pequenos-no-rio.html').read_bytes())
sections=[]
for h in t.xpath('//h3'):
 bits=[];urls=[]
 for e in h.itersiblings():
  if e.tag in ['h2','h3']:break
  bits.append(txt(e));urls+=e.xpath('.//a/@href')
 sections.append((slug(txt(h)),slug(' '.join(bits)),[u.split('?')[0] for u in urls if 'clubinhodeofertas.com.br/rio-de-janeiro/' in u]))
for r in base['candidatos']:
 if r['fonte']=='Pequenos no Rio':
  matches=[urls for name,body,urls in sections if name==slug(r['nome']) and slug(r['local']) in body]
  r['url_confirmacao']=matches[0][0] if matches and matches[0] else None
 else:r['url_confirmacao']=r['url'].split('#')[0]
(root/'etapa2/sementes.json').write_text(json.dumps(base,ensure_ascii=False,indent=2))
print('candidatos',len(base['candidatos']),'links distintos',len(set(r['url_confirmacao'] for r in base['candidatos'])))
print([(r['nome'],r['url_confirmacao']) for r in base['candidatos'] if not r['url_confirmacao']])
