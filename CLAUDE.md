<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/011-marca-sem-laranja/plan.md` — identidade entregue; a 012 ainda não tem plano
- Spec atual: `specs/012-telas-de-compra/spec.md`
- Spec anterior: `specs/011-marca-sem-laranja/spec.md`
- Research: `specs/011-marca-sem-laranja/research.md`
- Data model: `specs/011-marca-sem-laranja/data-model.md`
- Contracts: `specs/011-marca-sem-laranja/contracts/`
- Quickstart: `specs/011-marca-sem-laranja/quickstart.md`

Features anteriores, já implementadas:

- `specs/001-movie-highlights-carousel/` — carrossel da home, catálogo TMDb, página do filme
- `specs/002-site-header-navigation/` — cabeçalho global e busca por título
- `specs/003-user-authentication/` — entrada, saída e sessão para os três papéis
- `specs/004-home-movie-rows/` — trilhas Em cartaz, Em alta e Em breve na home
- `specs/005-seed-and-carousel-tuning/` — carrossel de 3 e seed com 12 filmes à venda
- `specs/006-visual-identity/` — ritmo, Archivo e disciplina de tokens. **NENHUM valor de cor,
  espaçamento, tipografia, raio ou duração pode ficar fora dos tokens** — a regra segurou por
  completo, e é o que torna a 011 barata.
- `specs/007-seat-selection/` — mapa da sala e reserva com prazo, `UNIQUE(sessão, assento)`
- `specs/008-payment-ticket-issuance/` — pagamento simulado e emissão, inseparáveis. Código do QR
  assinado com `TICKET_SIGNING_KEY` em `services/ingressos.py`, módulo **puro** sem banco.
- `specs/009-my-tickets-sharing/` — "Meus ingressos" e link revogável; token do link ≠ código do QR
- `specs/010-gate-validation/` — validação na portaria, quatro desfechos, **fluxo ponta a ponta
  fechado**. A garantia é `UPDATE ... WHERE used_at IS NULL` — sem constraint, o teste de
  concorrência é a única defesa. A portaria tem **tela única**: pousa em `/portaria` ao entrar e não
  alcança o catálogo (middleware que nega por padrão).
- `specs/011-marca-sem-laranja/` — cor, tipografia de marca e logo. EMENDA o FR-020 da 006.
  Magenta `#ff2e88` (neon de fachada). Cabinet Grotesk no nome. Logo: `t` com o ponto do `.com`.
  **A composição da home ficou de fora** — achado da checagem anti-slop, não desta feature.

**A feature 012 recomõe só três telas: filme, assentos e pagamento.** Catálogo (home, carrossel,
trilhas, busca), seed e contratos de destaque **não entram**. Sessões viram grade por dia e sala;
Sobre e Trailers usam o que o filme já persiste; o resumo da compra fica ao lado do mapa e do
formulário; o ingresso emitido nessa tela passa a ler como objeto. Nenhuma regra de negócio é
reaberta.

**A 011 permanece premissa, não entregável da 012.** Nomes de token iguais, valores iguais, marca
igual. Se a composição precisar de espaço ou raio novo, ele nasce em token — disciplina da 006.

**Dois tokens a vigiar** (herdados da 011, ainda válidos): `--cor-destaque-forte` é o contorno de
foco global; `--cor-fundo-qr` continua **branco**. Harmonizá-lo com a marca na recomposição do
ingresso faz a catraca parar de ler.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
