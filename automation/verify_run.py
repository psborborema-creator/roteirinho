import sys,json
from pipeline import key
before,after=[json.load(open(p)) for p in sys.argv[1:3]]
a={r['id']:r for r in before['candidatos']};b={r['id']:r for r in after['candidatos']}
assert set(a)<=set(b),'Perda de candidatos'
assert len(b)==len(after['candidatos']),'IDs duplicados'
assert len({key(r['dados']) for r in b.values()})==len(b),'Sessões duplicadas'
for i,r in a.items():
 assert r['dados']==b[i]['dados'],'Dados originais alterados'
 assert r['status_editorial']==b[i]['status_editorial'],'Decisão editorial alterada'
 assert r.get('lote_origem')==b[i].get('lote_origem'),'Lote alterado'
assert after['publicacao_automatica'] is False
print(json.dumps({'preservados':len(a),'total':len(b),'novos':len(b)-len(a),'duplicatas':0,'originais_preservados':True,'publicacao':False}))
