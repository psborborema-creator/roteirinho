import json
from pathlib import Path
from processar import identity
P=Path(__file__).resolve().parent
x=json.loads((P/'lote-editorial.json').read_text());seeds=json.loads((P/'sementes.json').read_text())['candidatos']
active=x['grupos']['prontos_para_aprovacao']+x['grupos']['pendentes_de_confirmacao'];ready=x['grupos']['prontos_para_aprovacao']
assert len({identity(r) for r in active})==len(active),'Sessão duplicada'
assert {r['id'] for r in seeds}=={i for r in active for i in r['ids_anteriores']},'Linhagem incompleta'
assert all(r['data'] and r['hora'] and r['local'] and r['url'] and r['evidencias'] for r in ready),'Pronto sem confirmação'
assert all(r['status']=='pendentes_de_confirmacao' and r['motivo'] for r in x['grupos']['pendentes_de_confirmacao'])
assert x['entrada_registros']+3-1==len(active)==64
assert x['publicacao_automatica'] is False
print(json.dumps({'linhagem_62_registros_completa':True,'sessoes_unicas':len(active),'prontos_com_evidencia':len(ready),'publicacao':False}))
