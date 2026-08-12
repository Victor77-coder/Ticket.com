# Contract — Detalhe do filme, campo `trailers` *(aditivo)*

**Feature**: `012-telas-de-compra` | **Date**: 2026-08-12

Este documento **não substitui** o contrato de highlights da 001. Ele descreve o único acréscimo
de payload desta feature: a lista de trailers já persistidos em `GET /api/v1/filmes/<slug>/`.

Sincronização, seed, `GET /api/v1/highlights/` e `GET /api/v1/home/` **não mudam**.

---

## `GET /api/v1/filmes/<slug>/`

**Autenticação**: nenhuma. Continua público.
**O que já existia**: `id`, `slug`, `title`, `synopsis`, `backdrop_url`, `poster_url`,
`certification_br`, `runtime_minutes`, `release_date`, `genres`, `screenings`.

### Campo novo

| Campo | Tipo | Nulo? | Notas |
|---|---|---|---|
| `trailers` | array | não | Pode ser `[]`. Nunca omitido, nunca `null` |
| `trailers[].provider` | string | não | Hoje só `"youtube"` — o mesmo da home |
| `trailers[].external_key` | string | não | Chave do vídeo; a home já a usa |
| `trailers[].kind` | `"trailer"` \| `"teaser"` | não | Já existe no modelo; a home **não** passa a recebê-lo |
| `trailers[].name` | string | não | Pode ser `""`; rótulo da seção Trailers |

**Ordenação**: o primário primeiro; demais por `published_at` descendente, desempate por `pk`.

### O que a resposta NÃO ganha

- direção, elenco, idioma, orçamento, `tmdb_id`
- `is_primary` (é mecânica interna de escolha; o primeiro da lista já o expressa)
- sessão em rascunho, custo, capacidade, contagem vendida — gate do Princípio IV, intacto

### Erros

Inalterados: `404` se o slug não existe; `500` com frase em português se o servidor falhar.

### Testes obrigatórios

1. Filme **com** trailers persistidos: a lista não é vazia, o primário vem primeiro, `provider` e
   `external_key` batem com o registro.
2. Filme **sem** trailer: `"trailers": []` — a chave existe.
3. `GET /api/v1/highlights/` **não** passa a incluir `kind` nem `name` por esta feature.
4. A resposta do detalhe continua sem os campos proibidos da 001 (status de sessão, custo,
   capacidade).
