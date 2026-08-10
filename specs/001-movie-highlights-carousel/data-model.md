# Phase 1 — Data Model: Carrossel de Highlights de Filmes

**Feature**: `001-movie-highlights-carousel` | **Date**: 2026-08-10

Modelos necessários para o carrossel. `Room` e `Screening` entram no escopo mínimo porque a
elegibilidade ao destaque (FR-002) depende de sessão publicada e futura — a justificativa está
no Complexity Tracking do [plan.md](./plan.md).

---

## Fronteira com a feature de reserva

Este documento define **apenas leitura**. Nada aqui cria caminho de escrita de ocupação de
assento.

Pertencem à feature de reserva e **NÃO** devem ser criados agora:

- `Seat`, `Reservation`, `Ticket`
- a constraint `UNIQUE(screening, seat)` exigida pelo Princípio II
- qualquer campo em `Screening` que registre assento ocupado

Adicionar ocupação de assento aqui violaria o Princípio II, porque criaria escrita de assento
sem a constraint que a protege. `Screening.seats_sold` existe como **valor derivado por
consulta** (hoje sempre 0, por não haver reserva), nunca como coluna materializada.

---

## `catalog.Genre`

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `tmdb_id` | integer | único, obrigatório |
| `name` | varchar(80) | obrigatório, em pt-BR |

Sincronizado do TMDb com `language=pt-BR`.

---

## `catalog.Movie`

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `tmdb_id` | integer | **único**, obrigatório — chave de idempotência do sync |
| `slug` | slug(200) | **único**, obrigatório — usado na URL `/filmes/{slug}` |
| `title` | varchar(200) | obrigatório, em pt-BR |
| `original_title` | varchar(200) | pode ser vazio |
| `synopsis` | text | pode ser vazio |
| `backdrop_path` | varchar(200) | caminho relativo do TMDb; pode ser vazio |
| `poster_path` | varchar(200) | caminho relativo do TMDb; pode ser vazio |
| `runtime_minutes` | integer | nulo permitido; se presente, > 0 |
| `certification_br` | varchar(10) | nulo permitido — sem entrada BR, fica nulo (R3) |
| `release_date` | date | nulo permitido |
| `genres` | M2M → `Genre` | pode ser vazio |
| `is_active` | boolean | default `true`; permite tirar do catálogo sem apagar |
| `synced_at` | datetime | atualizado a cada sync bem-sucedido |
| `created_at` / `updated_at` | datetime | auto |

**Regras de validação**

- `slug` é derivado de `title` na criação e **não muda** em syncs posteriores — a URL não pode
  quebrar porque o TMDb ajustou um título.
- Colisão de slug resolve com sufixo do ano de lançamento, depois com sufixo numérico.
- `backdrop_path` e `poster_path` guardam o caminho (`/abc123.jpg`), não a URL completa. A URL é
  montada na serialização, para que trocar o tamanho da imagem não exija migração de dados.

**Índices**: `tmdb_id` (único), `slug` (único), `is_active`.

**Propriedades derivadas** (não são colunas)

- `backdrop_url` → `https://image.tmdb.org/t/p/w1280{backdrop_path}`, nulo se vazio
- `poster_url` → `https://image.tmdb.org/t/p/w500{poster_path}`
- `synopsis_short` → `synopsis` truncada em ~180 caracteres na fronteira de palavra

---

## `catalog.Trailer`

Modelo próprio em vez de campo em `Movie`: o TMDb devolve vários vídeos por filme, e guardar
todos permite trocar o escolhido sem novo sync.

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `movie` | FK → `Movie` | `related_name="trailers"`, `on_delete=CASCADE` |
| `provider` | varchar(20) | `"youtube"` — apenas YouTube é suportado (R4) |
| `external_key` | varchar(60) | obrigatório — id do vídeo no provedor |
| `name` | varchar(200) | título do vídeo |
| `language` | varchar(10) | `iso_639_1` do TMDb |
| `kind` | varchar(20) | `"trailer"` ou `"teaser"` |
| `is_official` | boolean | |
| `is_primary` | boolean | o escolhido para exibição |
| `published_at` | datetime | nulo permitido |

**Constraints**

- `UNIQUE(movie, provider, external_key)` — o sync é idempotente.
- No máximo um `is_primary=true` por filme, garantido por
  `UniqueConstraint(fields=["movie"], condition=Q(is_primary=True))`.

**Regra de seleção do primário**: aplicada no sync conforme a ordem de preferência de R4
(oficial pt → oficial en → qualquer trailer → teaser). Sem candidato, o filme fica sem trailer
primário e o botão não é renderizado (FR-015).

---

## `screening.Room`

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `name` | varchar(60) | obrigatório — ex.: "Sala 1" |
| `capacity` | integer | obrigatório, > 0 |

Mínimo para dar capacidade à sessão. O mapa de assentos pertence à feature de reserva.

---

## `screening.Screening`

| Campo | Tipo | Regras |
|---|---|---|
| `id` | PK | |
| `movie` | FK → `Movie` | `related_name="screenings"`, `on_delete=PROTECT` |
| `room` | FK → `Room` | `on_delete=PROTECT` |
| `starts_at` | datetime | obrigatório, com fuso |
| `price` | decimal(8,2) | obrigatório, ≥ 0 — preço ao público |
| `status` | varchar(12) | `draft` \| `published` \| `cancelled`; default `draft` |
| `created_at` / `updated_at` | datetime | auto |

**Constraints e índices**

- `UNIQUE(room, starts_at)` — uma sala não exibe dois filmes ao mesmo tempo.
- Índice composto `(status, starts_at)` — é exatamente o filtro da consulta de elegibilidade.
- `PROTECT` no filme: apagar um filme com sessão agendada deve falhar, não cascatear.

**Campo deliberadamente ausente**: não existe `cost_price` nem qualquer dado de gestão neste
modelo por ora. Se for adicionado depois, o serializer público precisa continuar sem ele — é o
gate do Princípio IV.

---

## Consulta de elegibilidade (FR-002)

Vive em `apps/catalog/selectors.py`, fora da view, para ser testável sem HTTP.

```
filmes ativos
  que possuem ao menos uma sessão com status="published" e starts_at > agora
  anotados com next_screening_at = MIN(starts_at) dessas sessões
  ordenados por next_screening_at ascendente, desempate por título
  limitados a 5
```

Com `select_related`/`prefetch_related` para gêneros e trailer primário, para que a serialização
dos 5 painéis não gere consulta em cascata.

**Disponibilidade (FR-020)**: `has_available_seats` é derivado — capacidade da sala menos os
ingressos confirmados da sessão. Enquanto a feature de reserva não existir, não há ingresso e o
valor é sempre `true`. O campo entra no contrato agora para que o painel já trate o caso de
esgotado e o front-end não precise mudar quando a reserva chegar.

---

## Ordem das migrações

1. `catalog.0001` — `Genre`, `Movie`, `Trailer` e a M2M
2. `screening.0001` — `Room`, `Screening` (depende de `catalog.Movie`)

---

## Dados de seed

`seed_demo` cria o cenário exigido pelo desafio e pelo Princípio IV da constitution:

- 1 organizador, 2 clientes, 1 usuário de portaria — credenciais documentadas no README
- 2 salas
- ao menos 5 filmes sincronizados do TMDb, cada um com ao menos uma sessão **publicada e
  futura**, para que o carrossel tenha os 5 painéis previstos

O seed é idempotente: rodar duas vezes não duplica filme, sala nem sessão.
