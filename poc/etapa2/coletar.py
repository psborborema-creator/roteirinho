"""Revalida exclusivamente as URLs dos candidatos da primeira prova; não publica."""
import sys,json,re,hashlib,datetime as dt,concurrent.futures,argparse
from pathlib import Path
from lxml import html
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from coleta_poc import fetch
ROOT=Path(__file__).resolve().parent

def collect(out):
 seeds=json.loads((ROOT/'sementes.json').read_text());out.mkdir(parents=True,exist_ok=True)
 urls=sorted(set(r['url_confirmacao'] for r in seeds['candidatos'] if r.get('url_confirmacao')))
 def get(u):
  stamp=dt.datetime.now(dt.timezone.utc).isoformat();entry={'url':u,'verificado_em':stamp}
  try:
   b,status,final=fetch(u);name=hashlib.sha256(u.encode()).hexdigest()[:16]+'.html';(out/name).write_bytes(b)
   entry.update(http=status,url_final=final,snapshot=name,sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
  except Exception as exc:entry.update(erro=str(exc),alerta='FALHA')
  return entry
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:logs=list(p.map(get,urls))
 (out/'coleta.json').write_text(json.dumps({'fontes':logs,'publicacao_automatica':False},ensure_ascii=False,indent=2));print(json.dumps({'out':str(out),'paginas':len(logs),'sucessos':sum('http' in x for x in logs),'falhas':[x for x in logs if 'erro' in x]},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);collect(p.parse_args().out)
