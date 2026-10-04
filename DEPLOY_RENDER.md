# Colocar EVA online no Render

## O que este pacote já faz
- `render.yaml` cria um Web Service Python.
- Render fornece `PORT` automaticamente.
- `EVA_OWNER_TOKEN` é gerado como segredo.
- `/health` permite ao Render verificar o Core.
- `/state` mostra a memória/estado atual.
- `/` confirma que o Core está online.

## Passos no celular
1. Coloque estes arquivos em um repositório GitHub.
2. No Render, escolha **New > Blueprint** (ou Web Service) e conecte o repositório.
3. O `render.yaml` será detectado.
4. Faça o deploy.
5. Copie a URL `https://...onrender.com`.
6. Abra `EVA_MOBILE_CLIENT.html`, toque **Conectar Core** e cole a URL.
7. No painel do Render, copie o valor de `EVA_OWNER_TOKEN` e coloque no campo OWNER TOKEN do cliente.

## Limitação do plano gratuito
O Web Service gratuito do Render entra em suspensão após 15 minutos sem tráfego. O filesystem local também é efêmero; portanto `eva_state.json` NÃO é memória durável em produção. Para memória realmente persistente, a próxima etapa é mover o estado para um banco persistente. O Core não deve alegar estar continuamente ativo enquanto estiver no plano gratuito suspenso.

## Segurança
Nunca coloque `EVA_OWNER_TOKEN` dentro do repositório. Ele deve existir somente como variável secreta no Render e no dispositivo do proprietário.
