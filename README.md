# EVA v0.24 — Autonomous Research Core

Esta versão fecha o ciclo que a v0.23 apenas preparava:

1. EVA executa um ciclo interno.
2. A curiosidade dela escolhe uma lacuna/pergunta.
3. Ela cria um pedido `internet.research`.
4. O pedido fica PENDENTE.
5. Somente o proprietário autoriza ou nega.
6. Se autorizado, o executor consulta Wikipedia + Crossref.
7. Resultados rastreáveis entram na memória persistente.
8. O aprendizado gera novas perguntas internas.
9. Novas ações externas continuam exigindo nova autorização.

## Proprietário
Em produção defina `EVA_OWNER_TOKEN` no ambiente do servidor. O cliente móvel envia esse token apenas nas decisões de permissão. Sem token configurado, o modo de desenvolvimento aceita a decisão sem autenticação.

## Persistência
`eva_state.json` guarda identidade, conversas, conhecimento, curiosidade, permissões e auditoria. Em hospedagem real, use armazenamento persistente/volume; filesystem efêmero pode apagar o estado em reinícios.

## Execução contínua
O Core possui `maybe_cycle()` e `POST /cycle`. Para atividade real mesmo sem ninguém abrir a página, a infraestrutura deve chamar `/cycle` periodicamente ou manter um scheduler/processo ativo. O arquivo sozinho não pode executar quando nenhum computador/servidor o está rodando.

## Fontes
Wikipedia fornece texto introdutório. Crossref fornece metadados bibliográficos, não o texto completo dos artigos. A EVA não trata quantidade de resultados como prova de verdade.
