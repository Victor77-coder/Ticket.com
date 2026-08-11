# Phase 1 — Data Model: Ajuste da Vitrine

**Feature**: `005-seed-and-carousel-tuning` | **Date**: 2026-08-11

## Nenhuma mudança de modelo

Não há campo novo, tabela nova nem migração. Este documento existe para registrar **por quê** —
a ausência de mudança aqui é uma decisão, não um esquecimento.

---

## O que mudaria num desenho ingênuo

A leitura direta do pedido — "estes três filmes no carrossel" — sugere um campo de destaque:

```
Movie.is_featured = BooleanField(default=False)
Movie.featured_order = IntegerField(null=True)
```

Isso custaria uma migração, dois campos a manter em sincronia com o TMDb, e uma segunda regra de
ordenação no seletor do carrossel. E colocaria dados de demonstração dentro do modelo de produto.

## Por que não é necessário

Os dois mecanismos que resolvem já existem e já se encaixam:

| Mecanismo | Onde vive | O que faz |
|---|---|---|
| Agendamento por índice | `seed_demo._seed_screenings` | `starts_at = agora + offset + 30min × índice` |
| Ordenação do carrossel | `selectors.get_sellable_movies` | ordena por `next_screening_at` ascendente |

Quem está primeiro na lista do seed tem a sessão mais próxima, e o carrossel mostra os mais
próximos. **Ordenar a lista é a curadoria.**

A consequência de desenho importa: o carrossel continua sem saber que existe curadoria. Ele
aplica a mesma regra de sempre — "os N com sessão mais próxima" — e a escolha vive inteiramente
no cenário de demonstração, que é onde dados de demonstração devem viver.

---

## O que muda, e onde

| O quê | Onde | Natureza |
|---|---|---|
| Limite do carrossel: 5 → 3 | `selectors.HIGHLIGHTS_LIMIT` | constante |
| Filmes nomeados no início da lista | `seed_demo._pick_movies` | ordem de uma lista |
| Volume de filmes com sessão: 5 → 12 | `seed_demo.MIN_HIGHLIGHTED_MOVIES` | constante |

Nenhum dos três toca o esquema.

---

## Entidades usadas, sem alteração

- **`catalog.Movie`** — lido para encontrar os filmes nomeados por título. Nenhum campo novo.
- **`screening.Screening`** — criado pelo seed. A constraint `UNIQUE(sala, horário)` continua
  protegendo, e o deslocamento de 30 minutos por índice garante horários distintos mesmo com 12
  filmes em 2 salas.
- **`screening.Room`** — as mesmas duas salas.
- **`accounts.User`** — os mesmos quatro usuários semeados.

---

## Fronteira preservada

Continua valendo o que a feature 001 registrou: o seed cria **sessões**, nunca ocupação de
assento. `Seat`, `Reservation` e `Ticket` pertencem à feature de reserva, junto com a constraint
`UNIQUE(sessão, assento)` que os protege.

Aumentar o volume do seed não altera essa fronteira — são mais sessões, não mais estados.
