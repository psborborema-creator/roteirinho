# Coleta recorrente em fila — etapa 3

O workflow coleta.yml roda diariamente às 09h23 em Brasília (12h23 UTC), aceita workflow_dispatch e executa validação por push em main restrita aos arquivos de automação. O disparo por push serve aos testes de implantação; commits na branch de estado não o acionam.

- Código fica em main; estado fica exclusivamente na branch fila-candidatos, pasta automation-state.
- Restore lê a última fila dessa branch. Na primeira execução, copia seed_queue.json com as 64 sessões R2 e IDs de origem. O lote R2 original na branch da prova não é modificado.
- Novas observações são armazenadas separadamente dos dados originais. A decisão editorial nunca é modificada pelo coletor.
- Identidade canônica: título, data, hora, local normalizados e período (para programação sem sessão). Horas e locais diferentes não são fundidos.
- Registros ausentes em uma execução são preservados. Expirados ficam marcados e são retirados da contagem de pendentes ativos, sem apagar o histórico.
- Cada execução registra log por fonte, URL, HTTP, timestamp e SHA-256. HTTP 200 com tela de verificação não é sucesso de extração. Zero candidatos gera alerta. Falha total de extração falha o job, preservando a fila anterior.
- Fontes: Clubinho (18 detalhes), Pequenos no Rio (4 matérias/8 ingressos cada), EcoVilla (HTML), CCBB Educativo + descoberta na programação, Museu do Amanhã e Casa Firjan. Limites de acesso são registrados, sem contorno de bloqueios.
- Programações sem data/hora individual ficam como pendentes, sem inventar sessões futuras ou expandir intervalos em dias corridos. Casa Firjan filtra adequação infantil; cursos para educadores não são lazer infantil.
- Relatório e fila ficam em artefatos por 30 dias e em commits de estado com histórico por run ID. O resumo do job informa fontes, novos, reencontrados, duplicatas e falhas.
- A verificação compara os IDs da fila anterior, dados originais e decisão editorial. SHA-256 de eventos.json, index.html e seed_queue.json deve permanecer idêntico.
- Nenhum caminho do workflow escreve ou faz git add de eventos.json. A publicação depende de autorização editorial futura e não faz parte deste fluxo.

Dependência: Python 3.12, lxml 5.4.0. Testes locais: python -m unittest discover -s automation -p 'test_*.py'. Prova operacional exige links de runs reais do GitHub Actions e confirmação dos commits na branch de estado.
