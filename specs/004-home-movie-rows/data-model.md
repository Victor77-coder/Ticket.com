# Phase 1 — Data Model: Trilhas de Filmes na Home

**Feature**: `004-home-movie-rows` | **Date**: 2026-08-11

Uma migração, três campos, nenhuma entidade nova.

---

## `catalog.Movie` — três campos acrescentados

| Campo | Tipo | Regras |
|---|---|---|
| `is_trending` | boolean | default `False`, indexado — o TMDb listou este filme como em alta na última sincronização |
| `is_upcoming` | boolean | default `False`, indexado — o TMDb listou este filme como estreia futura |
| `catalog_synced_at` | datetime | nulo permitido — quando a classificação foi atualizada |

Todo o restante de `Movie` permanece como está.

**Por que booleanos e não uma tabela de coleção** (R2): a cardinalidade é fixa em três trilhas e
nenhuma tem atributo próprio — não há ordem manual, curadoria nem janela de vigência. Uma tabela
de associação representaria a mesma informação ao custo de um join e de uma migração a mais.
Quando existir curadoria por organizador, a migração para `Collection` é direta.

**Por que não um campo de texto com a categoria**: impediria um filme de estar em alta **e** com
estreia futura ao mesmo tempo, combinação comum que o FR-005 exige suportar.

**Índices**: `is_trending` e `is_upcoming` isolados. São filtros de igualdade sobre booleano em
tabela pequena; índice composto não traria ganho e o PostgreSQL combina os dois quando precisa.

---

## Regras de expiração (R3)

Esta é a parte sutil do modelo — o que mantém as trilhas honestas ao longo do tempo.

### `is_trending` — zerado e remarcado

```
início da sincronização:  Movie.objects.update(is_trending=False)
para cada filme da lista: is_trending = True
```

Sem a limpeza, o primeiro sync marcaria filmes que ficariam em alta **para sempre**: nada os
tiraria da trilha. "Em alta" é estado do mundo, não atributo do filme.

### `is_upcoming` — marca **e** data

A consulta da trilha Em breve exige as duas condições:

```
is_upcoming = True  E  release_date > hoje
```

Só a marca faria um filme já estreado permanecer na trilha até a próxima sincronização — visível
como erro para quem já viu o filme em cartaz. Só a data traria todo filme futuro do catálogo,
inclusive os que o TMDb não considera lançamento próximo. As duas juntas dão o resultado certo, e
a data é a que manda.

---

## Consultas das trilhas

Todas em `apps/catalog/selectors.py`, fora das views, testáveis sem HTTP.

### Em cartaz

```
reusa a regra de elegibilidade da feature 001, sem o limite de 5:
  filmes ativos com ao menos uma sessão publicada e futura
  ordenados pela sessão mais próxima, desempate por título
```

O carrossel continua pedindo 5; a trilha pede todos. **Uma regra só, dois consumidores** — é o que
garante que as duas superfícies façam a mesma promessa (R5, SC-003).

### Em alta

```
filmes ativos com is_trending = True
ordenados por release_date decrescente, desempate por título
limitados a 9
```

O limite de 9 vem do pedido do usuário (FR-003).

### Em breve

```
filmes ativos com is_upcoming = True e release_date > hoje
ordenados por release_date crescente, desempate por título
```

Ordem ascendente: o que estreia primeiro aparece primeiro, que é o que a trilha promete.

**Desempate por título em todas**: sem ele, filmes com a mesma data alternam de posição entre
requisições e os testes ficam instáveis.

---

## Migração

`catalog.0003_movie_catalog_classification` — três `AddField` e dois `AddIndex`.

Nenhum backfill: os campos nascem `False` e a primeira execução de `sync_tmdb` os preenche. Um
catálogo já importado antes desta feature simplesmente exibe as trilhas Em alta e Em breve vazias
— que, pelo FR-006, são omitidas — até a próxima sincronização.

---

## O que NÃO é criado

| Não criado | Por quê |
|---|---|
| `Collection` / `CollectionMovie` | Cardinalidade fixa em três, sem atributo próprio (R2) |
| Pedido de aviso / "Lembre-me" | Descartado pelo usuário em 2026-08-11 — ver Escopo excluído no spec |
| Campo de ordem manual | Nenhuma trilha é curada; todas são automáticas |
| Contador de visualizações ou popularidade local | O TMDb já fornece a noção de "em alta"; um segundo critério local seria outra verdade a manter |
| `Seat`, `Reservation`, `Ticket` | Fronteira da feature de reserva — ver `001/data-model.md` |
