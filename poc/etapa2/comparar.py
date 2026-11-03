import json
from pathlib import Path
P=Path(__file__).resolve().parent
a=json.loads((P/'rodada-1/editorial.json').read_text());b=json.loads((P/'rodada-2/editorial.json').read_text())
def signature(x):return {s:[{k:r.get(k) for k in ['id','nome','data','hora','fim','local','preco','idade','status','ids_anteriores']} for r in rows] for s,rows in x['grupos'].items()}
result={'rodadas':2,'paginas_por_rodada':[len(x['fontes']) for x in [a,b]],'conteudo_editorial_igual':signature(a)==signature(b),'ids_novos':sorted({r['id'] for rows in b['grupos'].values() for r in rows if r.get('id')}-{r['id'] for rows in a['grupos'].values() for r in rows if r.get('id')}),'duplicatas':[len(x['duplicatas']) for x in [a,b]],'contagens':[{k:len(v) for k,v in x['grupos'].items()} for x in [a,b]],'publicacao':False}
(P/'comparacao-etapa2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
if not result['conteudo_editorial_igual']:raise SystemExit('ATENÇÃO: divergência editorial entre as rodadas; revisar antes de aprovação.')
