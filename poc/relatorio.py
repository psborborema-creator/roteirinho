import json,html
from pathlib import Path
from coleta_poc import slug
ROOT=Path(__file__).parent
runs=[json.loads((ROOT/f'final-{i}/resultado.json').read_text()) for i in [1,2]]
def consolidate(d):
 result=[];dups=[]
 for r in d['candidatos']:
  same=next((x for x in result if slug(x['nome'])==slug(r['nome']) and x['data']==r['data'] and (slug(x['local']) in slug(r['local']) or slug(r['local']) in slug(x['local']))),None)
  if same:
   same.setdefault('corroboracao',[]).append({'fonte':r['fonte'],'url':r['url']});dups.append(r['id'])
  else:result.append(r.copy())
 return result,dups
rows,dups=consolidate(runs[1]); a={r['id'] for r in runs[0]['candidatos']};b={r['id'] for r in runs[1]['candidatos']}
comparison={'primeira':runs[0]['verificado_em'],'segunda':runs[1]['verificado_em'],'ids_iguais':a==b,'novos':sorted(b-a),'ausentes':sorted(a-b),'brutos':len(b),'consolidados':len(rows),'duplicatas_entre_fontes':dups}
(ROOT/'comparacao.json').write_text(json.dumps(comparison,ensure_ascii=False,indent=2))
intro='''# Roteirinho — prova de viabilidade — 03/11/2026

**Resultado: viável com restrições para descoberta assistida e checkpoint editorial. Nenhum candidato foi publicado.**

Duas execuções independentes do mesmo coletor consultaram novamente as três fontes, incluindo páginas sem JSON-LD. Resultado: 62 registros por execução, 61 candidatos após consolidar uma sessão presente em duas fontes; 16 sessões expiradas rejeitadas por execução. Os conjuntos de IDs foram iguais. Os hashes do HTML variaram: conteúdo dinâmico não equivale a mudança na programação.

| Fonte | Método | Registros por execução | Limitação |
|---|---|---:|---|
| Clubinho de Ofertas | Descoberta nos cartões HTML e sessões JSON-LD em 12 links distintos | 1 | 11 páginas retornaram zero sessões estruturadas; agenda dinâmica exige adaptação futura. Cartões não viraram datas inventadas. |
| Pequenos no Rio | Títulos e texto HTML da agenda de novembro | 57 | Fonte secundária; ano contextual da matéria. Só listas explícitas de dias, sem expandir intervalos em sessões diárias. |
| EcoVilla Ri Happy | Blocos HTML da programação oficial | 4 | Duas datas trazem 2026 explicitamente; duas têm ano contextual da agenda. Preço ausente permanece não informado. |

**Confiabilidade:** “primária” confirma o anúncio pelo espaço; “plataforma” confirma a sessão anunciada para venda; “secundária” exige confirmação com organizador. Não se verificou disponibilidade de cada ingresso nem cancelamentos fora das páginas. Nenhuma imagem de terceiros foi reutilizada.

**Repetibilidade testada:** executar `python coleta_poc.py --out NOVA_PASTA` com Python 3 e lxml. Os arquivos resultado.json registram HTTP, timestamp, URL, método, erros e SHA-256; os HTML preservam evidência auditável. comparacao.json compara IDs e consolida duplicidade entre fontes. test_poc.py passou 2 testes: rejeição de expirados e bloqueio de expansão indevida de intervalos.

**Limites:** piloto usa uma agenda mensal fixa e 12 ofertas; não constitui cobertura completa nem agendamento operacional. Sesc retornou 403 no teste inicial e a home do Pequenos retornou 406; a matéria mensal respondeu 200. Não houve contorno de autenticação. A deduplicação trata nome/data/local normalizados e local contido; variantes de nomes continuam exigindo revisão. O coletor legado e seu agendamento não foram alterados e seguem fora deste aceite.

**Recomendação:** seguir com coleta em fila separada, ampliar adaptadores e confirmação primária antes de automatizar recorrência. Não há custo adicional neste piloto; preço de infraestrutura futura não foi estimado. A issue permanece aberta. A aprovação editorial pode ser feita respondendo no chat “aprovar IDs … / rejeitar IDs …”; nenhuma edição técnica é necessária. Aprovação não dispensa sanar as pendências marcadas.

## Candidatos para revisão

Verificação em 03/11/2026, às 13h31 (Brasília). Valores são os anunciados na coleta e podem variar. “Não informado” não significa gratuito.

| ID | Evento | Data / horário anunciado | Local | Preço anunciado | Idade | Confiança / pendência | Fonte |
|---|---|---|---|---|---|---|---|
'''
lines=[]
for r in sorted(rows,key=lambda r:(r['data'],r['nome'])):
 vals=[r['id'],r['nome'],r['data_texto'],r['local'],r['preco'] or 'Não informado',r['idade'] or 'Não informada',r['confianca']+'; '+ '; '.join(r['pendencias']),f"[{r['fonte']}]({r['url']})"]
 lines.append('| '+' | '.join(str(v).replace('|',' / ').replace('\n',' ') for v in vals)+' |')
(ROOT/'Roteirinho-relatorio-viabilidade.md').write_text(intro+'\n'.join(lines)+'\n')
print(json.dumps(comparison))
