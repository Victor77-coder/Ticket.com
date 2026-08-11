# Contrato — `GET /api/v1/busca/` (Django)

**Feature**: `002-site-header-navigation` | **Date**: 2026-08-11

Endpoint público de busca de filmes por título. Lê exclusivamente o PostgreSQL local; **nunca**
chama o TMDb (Princípio VII). Consumido pelo Route Handler do Next descrito em
[search-proxy.md](./search-proxy.md), nunca pelo navegador direto.

---

## Requisição

```http
GET /api/v1/busca/?q=<termo>&limite=<n> HTTP/1.1
Accept: application/json
```

| Parâmetro | Tipo | Obrigatório | Padrão | Regras |
|---|---|---|---|---|
| `q` | string | sim | — | Truncado em 80 caracteres. Espaços das pontas removidos. |
| `limite` | inteiro | não | `6` | Faixa aceita: 1 a 20. Fora da faixa → fixado no limite mais próximo, sem erro. |

**Autenticação**: nenhuma. A view declara `permission_classes = [AllowAny]` e
`authentication_classes = []` **explicitamente** — o padrão do projeto é `IsAuthenticated`
(`REST_FRAMEWORK` em `config/settings/base.py`), e o acesso público é decisão registrada na view,
não herança silenciosa.

**Métodos**: apenas `GET`. Qualquer outro → `405 Method Not Allowed`.

---

## Resposta `200 OK`

```json
{
  "termo": "matr",
  "count": 2,
  "truncated": false,
  "results": [
    {
      "slug": "matrix-1999",
      "title": "Matrix",
      "poster_url": "https://image.tmdb.org/t/p/w500/abc.jpg",
      "year": 1999,
      "movie_path": "/filmes/matrix-1999"
    },
    {
      "slug": "matrix-reloaded",
      "title": "Matrix Reloaded",
      "poster_url": null,
      "year": 2003,
      "movie_path": "/filmes/matrix-reloaded"
    }
  ]
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `termo` | string | O termo já normalizado. Permite ao cliente confirmar a qual busca a resposta pertence. |
| `count` | inteiro | Quantidade de itens em `results`. Nunca maior que `limite`. |
| `truncated` | booleano | `true` quando existem mais correspondências do que `limite`. Dispara o aviso de FR-011. |
| `results[].slug` | string | Identificador estável do filme. |
| `results[].title` | string | Título exibido na sugestão. |
| `results[].poster_url` | string \| null | URL absoluta do pôster. `null` quando o filme não tem pôster — o cliente exibe um substituto, nunca uma imagem quebrada. |
| `results[].year` | inteiro \| null | Ano de estreia, para desambiguar títulos parecidos. `null` quando `release_date` não está preenchida. |
| `results[].movie_path` | string | Caminho relativo da página do filme no front-end (`/filmes/<slug>`). O cliente não monta URL a partir do slug. |

### Regras de correspondência

- **Parcial**: `"matr"` encontra `"Matrix"`. Não é necessário digitar o título completo (FR-008).
- **Insensível a caixa**: `"MATRIX"` = `"matrix"`.
- **Insensível a acento**: `"cacador"` encontra `"Caçador"`; `"CAÇADOR"` encontra `"cacador"`.
- **Somente filmes ativos**: `is_active=False` nunca aparece.
- **Sem filtro por sessão**: filme sem sessão à venda **aparece** nos resultados. Decisão
  registrada em `research.md` (R6) — a busca não esconde o que existe no catálogo; a página do
  filme é quem comunica a indisponibilidade.

### Ordenação

1. Correspondências que **começam** com o termo, antes das que apenas o **contêm**.
2. Desempate por `title` ascendente.

A ordenação é determinística e não depende da ordem física das linhas.

---

## Resposta com termo vazio

```http
GET /api/v1/busca/?q=   →  200 OK
```

```json
{ "termo": "", "count": 0, "truncated": false, "results": [] }
```

Termo ausente, vazio ou só com espaços devolve **200 com lista vazia**, não `400`. O parâmetro
ausente não é erro do cliente: é o estado inicial do campo, e o banco não é consultado (FR-014).

---

## Respostas de erro

| Código | Quando | Corpo |
|---|---|---|
| `405` | Método diferente de `GET` | Padrão do DRF |
| `500` | Falha inesperada no servidor | `{"detail": "Não foi possível concluir a busca."}` — mensagem em pt-BR, sem stack, sem detalhe interno |

Não existe `404` neste endpoint: busca sem resultado é `200` com `results: []`, e o cliente
distingue "nada encontrado" de "falhou" pelo código, não por lista vazia.

---

## Campos proibidos na resposta

**Gate do Princípio IV.** Esta é uma resposta pública e não autenticada. Nenhum dos campos abaixo
pode aparecer, em nenhum nível do payload:

- `Screening.status`, `Screening.price`, `Screening.id`, qualquer dado de sessão
- `Room.capacity`, `Room.name`, qualquer dado de sala
- Contagem de assentos, vendidos ou disponíveis
- Qualquer campo de `accounts.User` — identificação, e-mail, papel
- `Movie.tmdb_id`, `Movie.synced_at`, `Movie.created_at`, `Movie.updated_at`
- Chave de API, endereço interno, nome de host do back-end

`tests/test_search_api.py` verifica a ausência desses campos comparando o conjunto de chaves da
resposta com o conjunto permitido — não por inspeção manual.

---

## Casos cobertos por teste

`backend/tests/test_search_api.py`:

| # | Caso | Esperado |
|---|---|---|
| 1 | Termo parcial no meio do título | Filme encontrado |
| 2 | Termo com acento diferente do cadastrado | Filme encontrado |
| 3 | Termo em caixa diferente | Filme encontrado |
| 4 | Termo vazio / só espaços | `200`, `results: []`, sem consulta ao banco |
| 5 | Mais correspondências que o limite | `count == limite`, `truncated == true` |
| 6 | Exatamente o limite | `truncated == false` |
| 7 | Filme com `is_active=False` | Não aparece |
| 8 | Filme sem sessão publicada | **Aparece** (R6) |
| 9 | Requisição sem autenticação | `200` |
| 10 | Conjunto de chaves da resposta | Igual ao conjunto permitido — nenhum campo proibido |
| 11 | Dois títulos, um com prefixo | Prefixo vem primeiro |
| 12 | Termo com mais de 80 caracteres | Truncado, sem erro |
| 13 | `limite` fora da faixa | Fixado no limite mais próximo, sem erro |
