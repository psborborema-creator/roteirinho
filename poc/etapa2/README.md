# Continuação da prova — R2-20261103

Entrada congelada em sementes.json: 62 registros da primeira prova, com URLs de confirmação extraídas dos links já presentes na matéria coletada. Nenhuma descoberta ampla ou nova pesquisa.

Não executar collector.py para esta prova: ele é o coletor legado que escreve a base pública. Os scripts desta pasta não escrevem eventos.json. Usam Python 3.12 e lxml.

Reprodução executada pelo responsável técnico, a partir da raiz do repositório:

```bash
python poc/etapa2/coletar.py --out poc/etapa2/rodada-1
python poc/etapa2/processar.py poc/etapa2/rodada-1
python poc/etapa2/coletar.py --out poc/etapa2/rodada-2
python poc/etapa2/processar.py poc/etapa2/rodada-2
python poc/etapa2/comparar.py
python poc/etapa2/gerar_relatorio.py
python -m unittest discover -s poc/etapa2 -p test_editorial.py
```

Em nova coleta, usar novas pastas para preservar estas evidências; ajustar comparar.py para os diretórios novos. Para evitar elevar a carga sobre as fontes, são 4 conexões concorrentes, apenas nas 28 URLs de candidatos e sem contorno de bloqueios.

Regras: título + data + hora + local normalizados geram o ID canônico. IDs antigos são guardados em ids_anteriores. Intervalos de dias não são convertidos em sessões diárias. Datas múltiplas usam as sementes já desdobradas; horários específicos por data são isolados antes da extração. Ano contextual da agenda oficial atual é usado apenas nos candidatos já datados, com mês/dia/semana compatíveis; não se cria uma nova temporada.

Prontos: sessão exata sustentada por organizador ou plataforma pública. Pendentes: ausência de horário, falha de acesso ou sessão exata não demonstrada. Ausência de sessão não prova cancelamento. Descartados: expirados e duplicata consolidada, com motivos.

As pastas rodada-* têm logs HTTP, URLs finais, timestamps, SHA-256 e editorial.json. Trechos estruturados relevantes estão em evidencias, sem depender de descrição copiada. Snapshots HTML completos ficam preservados no ambiente da execução; os hashes e extratos relevantes são versionados. Os seis testes e a comparação de resultados foram executados com sucesso em 03/11/2026.

Operação recorrente agendada e publicação não foram autorizadas nesta etapa. Não mesclar esta branch como forma de publicar candidatos; somente a aprovação editorial explícita pode autorizar publicação futura.
