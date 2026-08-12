<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/012-telas-de-compra/plan.md`
- Spec: `specs/012-telas-de-compra/spec.md`
- Research: `specs/012-telas-de-compra/research.md`
- Data model: `specs/012-telas-de-compra/data-model.md`
- Contracts: `specs/012-telas-de-compra/contracts/`
- Quickstart: `specs/012-telas-de-compra/quickstart.md`

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
  **A composição da home ficou de fora** — achado da checagem anti-slop, não da 012.

**A feature 012 recomõe só três telas: filme, assentos e pagamento.** Catálogo (home, carrossel,
trilhas, busca), seed e contratos de destaque **não entram**. Sessões viram grade por dia e sala
**no cliente**; Sobre e Trailers usam o que o filme já persiste; `GET /api/v1/filmes/<slug>/` ganha
`trailers[]` aditivo — highlights **não**. O resumo fica ao lado do mapa em tela larga; o ingresso
emitido no pagamento ganha variante `objeto`. Nenhuma regra de negócio é reaberta.

**A armadilha é o clique, não a cor.** O horário disponível continua o link com nome acessível
`Escolher lugares —` (e2e da 007). `--cor-fundo-qr` continua **branco** na variante nova.
Arquivos congelados: `components/highlights/` (importar `TrailerFrame` a partir dele, não editá-lo),
`components/rows/`, `components/header/`, `app/page.tsx`, sync e seed.

**A 011 permanece premissa, não entregável.** Nomes de token iguais, valores iguais, marca igual.
Se a composição precisar de espaço novo, ele nasce em token — disciplina da 006.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
