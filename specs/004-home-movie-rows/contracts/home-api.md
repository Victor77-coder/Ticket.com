# Contract — Home Rows API

**Feature**: `004-home-movie-rows` | **Date**: 2026-08-11

Um endpoint novo. O de highlights (feature 001) permanece separado e intocado — fundi-los
quebraria o contrato de uma feature entregue para economizar uma requisição que já é rápida (R4).

---

## `GET /api/v1/home/`

Devolve as três trilhas da home em uma única resposta.

**Autenticação**: nenhuma. Público e somente leitura.
**Cache**: 60 s no servidor, como o de highlights.

### Resposta `200 OK`

```json
{
  "rows": [
    {
      "key": "em-cartaz",
      "title": "Em cartaz",
      "count": 5,
      "movies": [
        {
          "id": 12,
          "slug": "homem-aranha-um-novo-dia",
          "title": "Homem-Aranha: Um Novo Dia",
          "poster_url": "https://image.tmdb.org/t/p/w500/abc.jpg",
          "certification_br": "12",
          "runtime_minutes": 143,
          "release_date": "2026-07-30",
          "movie_path": "/filmes/homem-aranha-um-novo-dia"
        }
      ]
    },
    { "key": "em-alta",  "title": "Em alta",  "count": 9, "movies": [] },
    { "key": "em-breve", "title": "Em breve", "count": 4, "movies": [] }
  ]
}
```

### A trilha vazia não aparece

Uma trilha sem filmes é **omitida do array** `rows` (FR-006). O front-end não precisa decidir se
renderiza: se veio, renderiza.

Isso é deliberado — devolver `{"key": "em-alta", "movies": []}` e esperar que o cliente esconda
coloca a regra em dois lugares, e o dia em que um deles esquecer, aparece um título de seção com
nada embaixo.

### Nenhuma trilha com conteúdo

```json
{ "rows": [] }
```

Responde `200`, **não** `404`. Catálogo vazio é estado legítimo; o front-end mostra o estado
explicativo de FR-007.

### Ordem

`rows` vem sempre nesta ordem quando presente: **em-cartaz**, **em-alta**, **em-breve** (FR-001).
A ordem é do servidor — o cliente não reordena.

### Campos do cartão

| Campo | Tipo | Nulo? | Notas |
|---|---|---|---|
| `id` | integer | não | id interno, não o `tmdb_id` |
| `slug` | string | não | usado na rota do filme |
| `title` | string | não | pt-BR; exibido como texto no cartão (FR-009) |
| `poster_url` | string | **sim** | nulo aciona o substituto legível (FR-011) |
| `certification_br` | string | **sim** | nulo omite o selo |
| `runtime_minutes` | integer | **sim** | nulo omite a duração |
| `release_date` | string `YYYY-MM-DD` | **sim** | alimenta a ordenação de Em breve |
| `movie_path` | string | não | caminho relativo, nunca URL absoluta |

**Sem `backdrop_url`**: o cartão é vertical, de cartaz. Enviar a arte horizontal seria transferir
dado que nenhuma tela usa.

**Sem `trailer`**: não há reprodução na trilha. Quem quer o trailer vai à página do filme.

### Erros

| Código | Quando | Corpo |
|---|---|---|
| `500` | falha inesperada | `{"detail": "Não foi possível carregar a programação."}` |

Não há `4xx` previsto: o endpoint não recebe parâmetro nem exige autenticação.

---

## Campos proibidos na resposta

Mesmo gate do **Princípio IV** que já vale para highlights e busca. A resposta pública NÃO PODE
conter:

- `Screening.status`, nem qualquer sessão em `draft` / `cancelled`
- custo, margem ou qualquer dado financeiro de gestão
- capacidade de sala ou contagem de assentos vendidos
- identificação de usuário de qualquer papel
- `is_trending` / `is_upcoming` / `catalog_synced_at` — são mecânica interna de classificação; o
  cliente recebe a trilha pronta e não precisa saber por que o filme está nela

Deve existir teste que faça a requisição sem autenticação e afirme `200` **e** a ausência de cada
categoria acima.

---

## Contrato de resiliência

O endpoint lê **exclusivamente** o PostgreSQL. Não chama o TMDb em nenhuma circunstância
(Princípio VII, FR-021). Com o TMDb fora do ar esta resposta permanece idêntica — apenas a
classificação para de ser atualizada, o que é observável por `catalog_synced_at` mas não afeta o
que o visitante vê (FR-022, SC-004).

---

## `GET /api/v1/filmes/<slug>/` — acréscimo

O contrato existente da feature 001 ganha **um campo**:

| Campo | Tipo | Nulo? | Notas |
|---|---|---|---|
| `release_date` | string `YYYY-MM-DD` | **sim** | alimenta "Estreia em DD/MM/AAAA" (FR-025) |

Nenhum campo é removido nem alterado. Quando `release_date` for nulo ou estiver no passado, a
página informa apenas a ausência de sessões, sem anunciar estreia (FR-027, R8).
