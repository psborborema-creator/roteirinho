import json, re, urllib.request, datetime, html
from pathlib import Path
from html.parser import HTMLParser

SOURCES = [
 ("Sesc Tijuca", "https://cultura.sescrio.org.br/programacao/cade-o-sobrevento", "Tijuca"),
]
class Extract(HTMLParser):
 def __init__(self): super().__init__(); self.scripts=[]; self.capture=False
 def handle_starttag(self,tag,attrs):
  a=dict(attrs); self.capture=tag=="script" and "ld+json" in a.get("type","")
 def handle_data(self,data):
  if self.capture: self.scripts.append(data)
 def handle_endtag(self,tag):
  if tag=="script": self.capture=False

def walk(x):
 if isinstance(x,list):
  for v in x: yield from walk(v)
 elif isinstance(x,dict):
  if x.get("@type") in ("Event","ChildrensEvent","TheaterEvent") or (isinstance(x.get("@type"),list) and "Event" in x["@type"]): yield x
  for v in x.values(): yield from walk(v)

def collect():
 events=[]; errors=[]
 for organizer,url,bairro in SOURCES:
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"Roteirinho/1.0 (public event metadata; no login)"})
   with urllib.request.urlopen(req,timeout=20) as resp: page=resp.read(2000000).decode("utf-8","replace")
   p=Extract();p.feed(page)
   for s in p.scripts:
    try: objs=list(walk(json.loads(s)))
    except (ValueError,TypeError): continue
    for e in objs:
     start=e.get("startDate")
     if not start or not re.match(r"^\d{4}-\d{2}-\d{2}",str(start)):continue
     loc=e.get("location") or {}; loc=loc[0] if isinstance(loc,list) and loc else loc
     offers=e.get("offers") or {}; offers=offers[0] if isinstance(offers,list) and offers else offers
     price=offers.get("price") if isinstance(offers,dict) else None
     try: price=float(price) if price is not None else None
     except (ValueError,TypeError):price=None
     events.append({"id":url+"#"+str(start),"nome":html.unescape(str(e.get("name") or "")),"data":str(start)[:10],"hora":str(start)[11:16] if len(str(start))>=16 else None,"local":loc.get("name",organizer) if isinstance(loc,dict) else organizer,"bairro":bairro,"regiao":"Grande Tijuca","preco_min":price,"preco_texto":str(price)+" BRL" if price is not None else "Preço não informado","idade_min":None,"idade_max":None,"categoria":"Evento","descricao":re.sub("<[^>]+>","",str(e.get("description") or ""))[:500],"url":str(e.get("url") or url),"fonte_tipo":"Oficial","verificado_em":datetime.datetime.now(datetime.timezone.utc).isoformat()})
  except Exception as exc: errors.append({"url":url,"erro":str(exc)[:180]})
 return events,errors

def main():
 path=Path("eventos.json"); old=json.loads(path.read_text()) if path.exists() else {"eventos":[]}
 now=datetime.date.today().isoformat()
 new,errors=collect()
 byid={e["id"]:e for e in old.get("eventos",[]) if e.get("data","")>=now}
 for e in new:byid[e["id"]]=e
 result={"atualizado_em":datetime.datetime.now(datetime.timezone.utc).isoformat(),"eventos":sorted(byid.values(),key=lambda e:e["data"]),"erros_coleta":errors,"novos_encontrados":len(new)}
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
 print(json.dumps({"total":len(byid),"coletados":len(new),"erros":errors},ensure_ascii=False))
if __name__=="__main__":main()
