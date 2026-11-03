import json,collections,datetime as dt
from pathlib import Path
P=Path(__file__).resolve().parent
x=json.loads((P/'rodada-2/editorial.json').read_text());comp=json.loads((P/'comparacao-etapa2.json').read_text());ready=x['grupos']['prontos_para_aprovacao'];pending=x['grupos']['pendentes_de_confirmacao']
for i,r in enumerate(ready,1):r['codigo_editorial']=f'A{i:02d}'
for i,r in enumerate(pending,1):r['codigo_editorial']=f'P{i:02d}'
# Short codes are bound to this immutable batch; canonical IDs remain authoritative.
batch='R2-20261103';out={'lote':batch,**x};(P/'lote-editorial.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
def cell(s):return str(s or 'Não informado').replace('|',' / ').replace('\n',' ')
def table(rows,pend=False):
 lines=['| ID | Evento | Data | Horário | Local | Preço anunciado | Idade | Link'+(' / impedimento' if pend else '')+' |','|---|---|---|---|---|---|---|---|']
 for r in rows:
  h=r['hora'] or 'Não confirmado';h+=('–'+r['fim']) if r.get('fim') else ''
  price=r['preco'] or ('Referência secundária: '+r.get('preco_referencia_secundaria','') if r.get('preco_referencia_secundaria') else 'Não divulgado')
  vals=[r['codigo_editorial'],r['nome'],dt.date.fromisoformat(r['data']).strftime('%d/%m/%Y'),h,r['local'],price,r['idade'] or 'Não informada',f"[Fonte]({r['url']})"+('; '+r['motivo'] if pend else '')]
  lines.append('| '+' | '.join(cell(v) for v in vals)+' |')
 return '\n'.join(lines)
report=f'''# Roteirinho — lote editorial {batch}

**45 sessões prontas para aprovação · 19 pendentes · 17 registros descartados. Nenhuma publicação.**

Continuação dos 62 registros anteriores, sem nova pesquisa de eventos. As sessões foram separadas por data, hora e local. Após expansão: 65 sessões; uma duplicidade consolidada resulta em 64 sessões únicas. Descartados: 16 expirados já identificados e uma duplicata — não são 17 atrações canceladas.

Confirmação: 28 páginas dos links já descobertos, consultadas duas vezes em 03/11/2026. Fontes de confirmação: programação oficial da EcoVilla e páginas de sessão do Clubinho de Ofertas. “Pronto” significa data, horário e local sustentados pela fonte oficial/plataforma; campos não divulgados permanecem vazios. Preços são valores mínimos anunciados na coleta, sujeitos a taxas/lotes. Disponibilidade final e inscrição devem ser consultadas no link.

## Prontos para aprovação — A01 a A45

Uma linha por sessão. Todos os horários são de Brasília. Para aprovar em lote, basta responder **“aprovar lote {batch}, A01–A45”**, com eventuais exceções. Os códigos abaixo são exclusivos deste lote; a planilha de dados preserva IDs canônicos e anteriores.

'''+table(ready)+'''

## Pendentes de confirmação — não incluídos no lote aprovável

A ausência de uma sessão na página não prova cancelamento. As 19 sessões abaixo continuam pendentes; nenhuma foi promovida com base apenas na agenda secundária. Nas páginas sem sessões extraíveis, o catálogo público foi acessado, mas o HTML/dado estruturado não permitiu comprovar a sessão exata.

'''+table(pending,True)+'''

## Correções e evidências

- **Brinquedos em Ação, 20/11 às 16h:** os IDs antigos `0af2541ca12a` e `609acc74c449` foram consolidados em uma sessão. Ambos continuam no histórico.
- **Escola do Rock, seis datas de novembro:** horário corrigido de 19h30 para **15h**, conforme plataforma e organizador; horários de dezembro não foram importados.
- **EcoVilla 4 anos, 07/11:** turnos individuais **11h–13h** e **13h30–15h30**; a agenda oficial oferece link de inscrição. Gratuidade não garante vaga.
- **Chapeuzinho e Cinderela:** 15h e 17h viraram sessões distintas. Somente as sessões das 15h foram confirmadas; 17h permanece pendente.
- **Natal da Frozen:** mantidos os locais distintos. Na Barra Square, a referência de 22/11 às 15h não foi aplicada a 29/11, cuja referência é 16h. Ambas aguardam confirmação.
- **Natal Mágico na Casa da Gabby:** o extrator anterior capturou texto de venda como horário. Agora o horário é nulo e o candidato permanece pendente.
- Não foram inventadas classificações indicativas. Regras de meia-entrada ou gratuidade infantil não foram tratadas como faixa etária.

**Repetibilidade:** duas rodadas de 28 páginas, todas com HTTP 200; conteúdo editorial igual nos dois resultados, sem IDs novos. Os hashes dos documentos podem mudar por elementos dinâmicos. Seis testes passaram: IDs diferentes para a mesma sessão, preservação de locais/horas distintos, hora específica por data, turnos e múltiplas sessões, ausência de horário e idempotência.

**Reconciliação:** 62 registros anteriores + 3 sessões adicionais por desdobramento − 1 duplicata = 64 sessões únicas = 45 prontas + 19 pendentes. Os 16 expirados já estavam fora dos 62 e ficam no histórico de descartados.

**Limite operacional:** repetição manual pelo executor foi comprovada; agendamento recorrente ainda não foi implantado ou validado. O código não escreve em eventos.json. Publicação continua condicionada à aprovação editorial explícita.

Os arquivos lote-editorial.json, comparacao-etapa2.json e as duas pastas de rodada contêm dados, fontes, horários de consulta, hashes e extratos de evidência. Os candidatos pendentes têm IDs individuais e justificativa. Os descartados permanecem no JSON para auditoria.
'''
(P/'Roteirinho-lote-editorial-R2.md').write_text(report)
print('relatorio',len(report),'lote',batch)
