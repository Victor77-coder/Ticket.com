<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/014-cartao-de-sessao-e-meia-entrada/plan.md`
- Spec: `specs/014-cartao-de-sessao-e-meia-entrada/spec.md`
- Research: `specs/014-cartao-de-sessao-e-meia-entrada/research.md`
- Data model: `specs/014-cartao-de-sessao-e-meia-entrada/data-model.md`
- Contracts: `specs/014-cartao-de-sessao-e-meia-entrada/contracts/`
- Quickstart: `specs/014-cartao-de-sessao-e-meia-entrada/quickstart.md`

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

- `specs/013-painel-do-organizador/` — o painel do organizador, etapa 6 da constitution. Pousa em
  `/programacao`, busca filme no TMDb **pelo back-end**, cria sala/sessão e publica. **Zero
  migração.** Três regras ganharam dono único: geometria da sala (`screening/services/salas.py`),
  mapeamento do TMDb (`sync_movie`) e ocupação viva (`Reservation.OCUPANDO`, consumida, nunca
  reescrita). O organizador **pousa** no painel mas **não** é confinado como a portaria. Conflito
  `(sala, horário)` vem do `IntegrityError` da constraint, nunca de `exists()` prévio.

**A feature 014 tem duas metades de custo muito diferente.** A grade vira **cartão por sala** com as
ações **Assentos** e **Preços**, que abrem sobreposições de leitura — apresentação pura, sem tocar em
regra. E a **meia-entrada vira comprável**, que é a primeira mudança no que se cobra desde a 008.

**A regra do preço estava escrita três vezes** — `pagamentos.total_da_reserva`,
`ReservationSerializer.get_total` e `SeatSelection.tsx`. A saída não é ensinar meia às três: com
`ReservedSeat.unit_price` **gravado**, o total vira **soma de coluna** e as duas cópias do back-end
somem. `backend/apps/screening/services/precos.py` é o dono; `frontend/lib/meia.ts` é espelho da
prévia, e nenhum valor dele é enviado.

**Três fronteiras que a 014 não pode cruzar.** (1) A portaria continua com **exatamente quatro
desfechos** — o tipo é exibido para o operador pedir documento, nunca é condição de entrada. (2) O
painel de assentos é **somente leitura**: seleção continua no mapa da 007, sem segundo caminho de
reserva. (3) `assentos: [int]` mantém o significado da 007 — o tipo entra pelo campo **aditivo**
`meias: [int]`, e ausente significa tudo inteira.

Congelados: home, carrossel, trilhas, busca, programação, portaria.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
