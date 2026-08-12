<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/010-gate-validation/plan.md`
- Spec: `specs/010-gate-validation/spec.md`
- Research: `specs/010-gate-validation/research.md`
- Data model: `specs/010-gate-validation/data-model.md`
- Contracts: `specs/010-gate-validation/contracts/`
- Quickstart: `specs/010-gate-validation/quickstart.md`

Features anteriores, já implementadas:

- `specs/001-movie-highlights-carousel/` — carrossel da home, catálogo TMDb, página do filme
- `specs/002-site-header-navigation/` — cabeçalho global e busca por título
- `specs/003-user-authentication/` — entrada, saída e sessão para os três papéis
- `specs/004-home-movie-rows/` — trilhas Em cartaz, Em alta e Em breve na home
- `specs/005-seed-and-carousel-tuning/` — carrossel de 3 e seed com 12 filmes à venda
- `specs/006-visual-identity/` — linguagem visual e disciplina de tokens. Nenhum valor de cor,
  espaçamento, tipografia, raio ou duração pode ficar fora dos tokens.
- `specs/007-seat-selection/` — mapa da sala e reserva com prazo de 10 minutos
- `specs/008-payment-ticket-issuance/` — pagamento simulado e emissão do ingresso, inseparáveis.
  O código do QR é assinado com `TICKET_SIGNING_KEY` — segredo próprio, distinto da
  `DJANGO_SECRET_KEY`, que nunca chega ao front-end — em `services/ingressos.py`, módulo **puro**
  que não importa modelo (é o que torna `num_queries == 0` verificável).
- `specs/009-my-tickets-sharing/` — área "Meus ingressos" e link de compartilhamento revogável.
  O token do link é distinto do código do QR e os ciclos de vida são independentes.

**A feature 010 valida o ingresso na portaria e FECHA O FLUXO PONTA A PONTA.** É a etapa 5 da ordem
obrigatória da constitution.

**A garantia muda de forma pela primeira vez.** 007, 008 e 009 fecharam invariantes com índices
(`UNIQUE` absoluta, parcial, parcial). Aqui o invariante é de **transição** — "esta coluna só sai de
nulo uma vez" —, e nenhum índice o expressa: uma `CHECK` enxerga o valor final, não a história. A
garantia é `UPDATE ... SET used_at = now() WHERE id = ? AND used_at IS NULL`, e **o número de linhas
afetadas é o desfecho**: 1 é válido, 0 é já utilizado.

**A armadilha desta feature é o `if` mais natural que existe:**

    if ingresso.used_at is not None: return JA_UTILIZADO
    ingresso.used_at = timezone.now(); ingresso.save()

É leitura seguida de escrita. Passa em todo teste de uma thread só, **lê exatamente como a regra da
spec**, e — ao contrário das três features anteriores — **o banco não reclama**, porque não há
constraint para recusar. A única coisa entre o projeto e uma portaria furada é o teste de
concorrência, que por isso vem antes do serviço. O desfecho DEVE vir do `rowcount`, nunca de um `if`
sobre o objeto lido.

**Ordem do pipeline** (só o último passo escreve): assinatura → ingresso existe → payload bate com o
banco → **sessão da porta** → `UPDATE` condicional. "Sessão errada" vem antes de "já utilizado" e
**não escreve** — o ingresso continua valendo na porta certa.

**"Sessão errada" só existe porque a portaria declara a sessão da porta.** Inferir a sessão só pelo
código torna o desfecho impossível: comparar a sessão do ingresso com ela mesma sempre dá igual.

**A armadilha da 009 volta**: `sellable()` (= `published()` E `starts_at > now()`) esconde a sessão
**em andamento**, que é exatamente a que a porta está recebendo. Regra: `sellable()` responde "dá
para comprar?", e nenhuma outra pergunta.

**O campo de uso NÃO pode entrar em `TicketSerializer` nem `MeuIngressoSerializer`** — uma linha, e
"utilizado" aparece na página compartilhada **pública** da 009.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
