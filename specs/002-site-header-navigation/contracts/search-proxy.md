# Contrato — `GET /api/busca` (Route Handler do Next)

**Feature**: `002-site-header-navigation` | **Date**: 2026-08-11

Único endereço de busca que o **navegador** conhece. Roda no servidor do Next
(`frontend/app/api/busca/route.ts`), repassa a consulta ao Django e traduz falhas em mensagem
pt-BR. Existe para preservar duas propriedades já estabelecidas no projeto: o navegador não fala
com o Django direto, e o endereço do back-end não entra no bundle (`research.md`, R1).

---

## Requisição

```http
GET /api/busca?q=<termo> HTTP/1.1
```

| Parâmetro | Tipo | Obrigatório | Regras |
|---|---|---|---|
| `q` | string | sim | Repassado ao Django já com `encodeURIComponent`. Truncado em 80 caracteres antes do repasse. |

Mesma origem do front-end (`http://localhost:5003`), portanto **sem CORS e sem preflight** no
caminho quente da digitação.

**Métodos**: apenas `GET`.

**Cache**: `export const dynamic = "force-dynamic"`. O resultado depende do catálogo corrente e do
termo; uma resposta estática devolveria sugestão obsoleta.

---

## Resposta `200 OK`

Repassa **sem alteração de forma** o payload de
[`GET /api/v1/busca/`](./search-api.md#resposta-200-ok):

```json
{
  "termo": "matr",
  "count": 2,
  "truncated": false,
  "results": [
    { "slug": "matrix-1999", "title": "Matrix", "poster_url": "…", "year": 1999, "movie_path": "/filmes/matrix-1999" }
  ]
}
```

O proxy não enriquece, não reordena e não reformata. Qualquer transformação criaria uma segunda
verdade sobre o formato da busca, divergente do contrato do Django.

---

## Resposta de erro

O proxy **nunca repassa o corpo de erro do Django**. Ele traduz:

```json
{ "erro": "Não foi possível buscar agora. Tente de novo em instantes." }
```

| Situação | Código devolvido ao navegador | Mensagem |
|---|---|---|
| Django respondeu `5xx` | `502` | "Não foi possível buscar agora. Tente de novo em instantes." |
| Timeout na chamada ao Django (8 s, igual a `lib/api.ts`) | `504` | "A busca demorou demais para responder." |
| Django inalcançável (rede, container fora do ar) | `502` | "Não foi possível falar com o servidor." |
| `q` ausente | `200` | `{ "termo": "", "count": 0, "truncated": false, "results": [] }` — mesmo comportamento do Django |

**Nunca podem atravessar o proxy**: stack trace, corpo de erro do DRF, nome de host interno
(`backend:8000`), valor de `API_BASE_URL`, cabeçalho de resposta do Django que revele versão ou
rota. O erro é registrado no log do servidor Next; o navegador recebe só a frase.

---

## Comportamento esperado do cliente

`frontend/lib/search-client.ts` é o único chamador. Ele:

1. Aplica **debounce de 250 ms** antes de chamar (R3).
2. Passa um `AbortSignal`; a busca anterior é abortada quando uma nova começa.
3. Carrega um **número de sequência**; aplica a resposta ao estado apenas se for a mais recente
   já vista. Esta guarda é o que sustenta FR-015 e SC-005 — o abort sozinho não fecha a janela de
   corrida.
4. Trata `AbortError` como **não-erro**: requisição abortada não pinta o estado de erro na tela.

---

## Casos cobertos por teste

`frontend/tests/search.test.tsx` (Vitest + Testing Library, `fetch` dublado):

| # | Caso | Esperado |
|---|---|---|
| 1 | Digitação rápida de 5 caracteres | Uma única requisição, com o termo final |
| 2 | Resposta antiga resolve **depois** da nova | A lista mostra o resultado da nova; o da antiga é descartado |
| 3 | Resposta `200` com `results: []` | Estado "nenhum resultado", com o termo na mensagem |
| 4 | Resposta de erro do proxy | Estado de erro em pt-BR, termo digitado preservado |
| 5 | Requisição em voo | Estado "buscando", visualmente distinto de "nenhum resultado" |
| 6 | `truncated: true` | Aviso de que há mais resultados |
| 7 | Setas ↓/↑ | `aria-activedescendant` acompanha a opção destacada |
| 8 | Enter com opção destacada | Navega para `movie_path` |
| 9 | Esc | Lista fecha, foco permanece no input |
| 10 | Campo esvaziado | Lista fecha, nenhuma requisição disparada |
| 11 | Campo com só espaços | Nenhuma requisição disparada |
