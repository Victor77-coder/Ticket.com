# Contract — Highlights API

**Feature**: `001-movie-highlights-carousel` | **Date**: 2026-08-10

Único endpoint que esta feature expõe. Consumido pelo Server Component da home (R5).

---

## `GET /api/v1/highlights/`

Devolve os filmes em destaque do carrossel — no máximo 5, conforme a regra de elegibilidade de
FR-002.

**Autenticação**: nenhuma. O endpoint é público (FR-019).
**Cache**: 60 s no servidor (R7).

### Resposta `200 OK`

```json
{
  "count": 5,
  "results": [
    {
      "id": 12,
      "slug": "duna-parte-dois",
      "title": "Duna: Parte Dois",
      "synopsis_short": "Paul Atreides se une aos Fremen para vingar sua família…",
      "backdrop_url": "https://image.tmdb.org/t/p/w1280/xOMo8BRK7PfcJv9JCnx7s5hj0PX.jpg",
      "poster_url": "https://image.tmdb.org/t/p/w500/czembW0Rk1Ke7lCJGahbOhdCuhV.jpg",
      "certification_br": "14",
      "runtime_minutes": 166,
      "genres": ["Ficção científica", "Aventura"],
      "trailer": {
        "provider": "youtube",
        "external_key": "Way9Dexny3w"
      },
      "next_screening_at": "2026-08-11T19:30:00-03:00",
      "has_available_seats": true,
      "movie_path": "/filmes/duna-parte-dois"
    }
  ]
}
```

### Campos

| Campo | Tipo | Nulo? | Notas |
|---|---|---|---|
| `count` | integer | não | 0 a 5. Alimenta o indicador "n de N" (FR-005) |
| `results[].id` | integer | não | id interno, não o `tmdb_id` |
| `results[].slug` | string | não | usado para montar a rota do filme |
| `results[].title` | string | não | pt-BR |
| `results[].synopsis_short` | string | não | pode ser `""`; o painel omite a linha se vazio |
| `results[].backdrop_url` | string | **sim** | nulo aciona o fallback de arte do painel |
| `results[].poster_url` | string | **sim** | usado no fallback e em telas estreitas |
| `results[].certification_br` | string | **sim** | nulo omite o selo — nunca exibir "N/A" |
| `results[].runtime_minutes` | integer | **sim** | nulo omite a duração |
| `results[].genres` | string[] | não | pode ser `[]` |
| `results[].trailer` | object | **sim** | **nulo esconde o botão "Trailer"** (FR-015) |
| `results[].next_screening_at` | string ISO 8601 | não | sessão publicada mais próxima; define a ordem |
| `results[].has_available_seats` | boolean | não | `false` muda o botão para o estado esgotado (FR-020) |
| `results[].movie_path` | string | não | caminho relativo, nunca URL absoluta |

**Ordenação**: `next_screening_at` ascendente, desempate por `title` (R6). Determinística.

### Catálogo vazio

```json
{ "count": 0, "results": [] }
```

Responde `200`, **não** `404`. Ausência de destaque é um estado legítimo, não erro — o front-end
renderiza o estado vazio de FR-022.

### Erros

| Código | Quando | Corpo |
|---|---|---|
| `500` | falha inesperada no servidor | `{"detail": "Não foi possível carregar os filmes em cartaz."}` |

Não há `4xx` previsto: o endpoint não recebe parâmetro, não exige autenticação e não tem
variante inválida.

**Comportamento no front-end diante de `500` ou timeout**: renderiza o estado de erro em pt-BR
com ação de recarregar (FR-024), nunca uma área em branco (SC-008).

---

## Campos proibidos na resposta

Gate do **Princípio IV** — a resposta pública NÃO PODE conter, hoje nem em evolução futura:

- `Screening.status` ou qualquer sessão em `draft` / `cancelled`
- qualquer campo de custo, margem ou dado de gestão do organizador
- capacidade da sala, contagem de assentos vendidos ou dados de outros clientes
- identificação de usuário de qualquer papel

`has_available_seats` é intencionalmente um **booleano**, não uma contagem: o carrossel só
precisa saber se ainda dá para comprar, e expor o número aberto seria vazar operação.

Deve existir teste automatizado que faça a requisição sem autenticação e afirme tanto o `200`
quanto a ausência de cada categoria acima.

---

## Contrato de resiliência

O endpoint lê **exclusivamente** o PostgreSQL. Não chama o TMDb em nenhuma circunstância
(Princípio VII, R7). Com o TMDb fora do ar, esta resposta permanece idêntica — só a reprodução
do trailer no navegador degrada, o que é coberto pelo cenário 6 da US2 e por SC-006.
