<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/011-marca-sem-laranja/plan.md`
- Spec: `specs/011-marca-sem-laranja/spec.md`
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

**A feature 011 troca a cor da marca, dá tipografia própria ao nome e cria a logo. EMENDA o FR-020
da 006** ("paleta escura com destaque laranja") — revoga a segunda metade, mantém a primeira.

**A cor sai por ELIMINAÇÃO, não por gosto.** A restrição que ninguém antecipa: a marca não pode
colidir com cor de estado. `--cor-alerta` é âmbar (38°), e isso **elimina o âmbar** — o candidato
mais óbvio para um cinema — porque ele fica a 8° dela. Sobra o magenta: **`#ff2e88`**. Conceito:
das quatro luzes de um cinema (marquise, saída, projeção, fachada), três já são cores de estado;
sobrou o **neon da fachada**.

**Os NOMES dos tokens não mudam, só os valores.** O laranja vive em 4 declarações num arquivo só;
12 arquivos consomem os nomes em 28 usos. **Nenhum consumidor deve ser tocado** — se um precisar, um
valor vazou dos tokens.

**A armadilha é de classe nova: trocar cor NÃO QUEBRA NADA.** Os 197 testes de front-end continuam
verdes com o contorno de foco invisível, o texto do botão ilegível e o assento selecionado
indistinguível do tomado. Nenhum teste mede contraste. Por isso existe `tests/tokens.test.ts`, que
lê os tokens e mede: contraste WCAG, ΔE contra as cores de estado, e ausência da cor antiga.

**Dois tokens a vigiar**: `--cor-destaque-forte` é o **contorno de foco global** (`tokens.css:293`)
e é mais clara que a base de propósito; `--cor-fundo-qr` continua **branco**, exceção deliberada da
008 — harmonizá-lo com a marca faz a catraca parar de ler.

**`--cor-sobre-destaque` precisa passar em DOIS fundos**: a base (repouso) e a `-forte` (hover).

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
