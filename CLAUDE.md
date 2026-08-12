<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/013-painel-do-organizador/plan.md`
- Spec: `specs/013-painel-do-organizador/spec.md`
- Research: `specs/013-painel-do-organizador/research.md`
- Data model: `specs/013-painel-do-organizador/data-model.md`
- Contracts: `specs/013-painel-do-organizador/contracts/`
- Quickstart: `specs/013-painel-do-organizador/quickstart.md`

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

- `specs/012-telas-de-compra/` — recomposição de filme, assentos e pagamento. Sessões viram grade por
  dia e sala **no cliente**; `GET /api/v1/filmes/<slug>/` ganha `trailers[]` aditivo. O horário
  disponível é o link com nome acessível `Escolher lugares —` (e2e da 007). `--cor-fundo-qr` branco.

**A feature 013 é a etapa 6 da constitution: o painel do organizador.** Ele pousa em `/programacao`,
busca filme no TMDb **pelo back-end**, persiste local, cria sala/sessão e publica. **Zero migração** —
`Movie`, `Room`, `Seat`, `Screening` já bastam; coluna nova é escopo escorregando.

**Três regras existentes não podem ganhar segunda cópia.** O mapa físico da sala sai de `seed_demo`
para `screening/services/salas.py` e é consumido pelos dois. A importação de filme usa o
`sync_movie` que já existe — não um mapeamento reduzido. "Ocupação viva" continua sendo
`Reservation.OCUPANDO`, consumida, nunca reescrita.

**Duas armadilhas.** (1) `CASA_DO_PAPEL` separa `telaUnica` em `pousa` + `telaUnica`: o organizador
pousa no painel mas **não** é confinado — o middleware nega por padrão, e `telaUnica: true` o
trancaria fora do catálogo público. `devolverParaCasa("organizer", …)` continua `null`. (2) O
conflito `(sala, horário)` é recusado pelo `IntegrityError` da constraint
`uma_sessao_por_sala_e_horario`, **nunca** por `exists()` prévio.

**Toda escrita de programação vive sob `/api/v1/programacao/` e exige `IsOrganizer`.** Cliente e
portaria recebem `403`, nunca `401`. Cancelar sessão **para de vender** e mais nada: não estorna,
não apaga ingresso, não devolve lugar pago. `seed_demo` passa a exigir `--force` quando já existe
grade. Congelados: home, carrossel, trilhas, busca, mapa, pagamento, ingresso, portaria.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
