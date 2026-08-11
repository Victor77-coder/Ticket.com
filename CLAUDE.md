<!-- SPECKIT START -->
For additional context about technologies to be used, project structure,
shell commands, and other important information, read the current plan:

- Plan: `specs/007-seat-selection/plan.md`
- Spec: `specs/007-seat-selection/spec.md`
- Research: `specs/007-seat-selection/research.md`
- Data model: `specs/007-seat-selection/data-model.md`
- Contracts: `specs/007-seat-selection/contracts/`
- Quickstart: `specs/007-seat-selection/quickstart.md`

Features anteriores, já implementadas:

- `specs/001-movie-highlights-carousel/` — carrossel da home, catálogo TMDb, página do filme
- `specs/002-site-header-navigation/` — cabeçalho global e busca por título (44/44)
- `specs/003-user-authentication/` — entrada, saída e sessão para os três papéis (52/52)

- `specs/004-home-movie-rows/` — trilhas Em cartaz, Em alta e Em breve na home (55/55 + emenda
  de 11 tarefas). A trilha Em alta exige sessão planejada desde a emenda de 2026-08-11.

- `specs/005-seed-and-carousel-tuning/` — carrossel de 3 e seed com 12 filmes à venda (22/22)
- `specs/006-visual-identity/` — linguagem visual e disciplina de tokens (47/47). Nenhum valor de
  cor, espaçamento, tipografia, raio ou duração pode ficar fora dos tokens.

**A feature 007 atravessa a fronteira do Princípio II.** Desde a 001, `apps/screening/models.py`
avisa que escrita de ocupação de assento não entra sem a constraint `UNIQUE(sessão, assento)` que
a protege. Esta feature cria as duas coisas **na mesma migração** — separá-las é o que o princípio
proíbe. O teste de concorrência não é diferencial: é prova obrigatória, e precisa **falhar** se a
constraint for removida.

Project constitution (governa todas as features): `.specify/memory/constitution.md`
<!-- SPECKIT END -->
