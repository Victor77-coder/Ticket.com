# Data Model — Cabeçalho Global do Site

**Feature**: `002-site-header-navigation` | **Date**: 2026-08-11

> **Resumo**: esta feature **não cria entidade nem campo novo**. Ela acrescenta uma extensão ao
> banco, uma consulta de leitura e uma projeção de serialização. Este documento existe para
> registrar isso explicitamente — e para deixar escrito por que `Localidade` não foi modelada.

---

## O que muda no banco

### Extensão `unaccent` (migração nova)

```text
apps/catalog/migrations/0002_unaccent_extension.py
    UnaccentExtension()   # django.contrib.postgres.operations
```

Habilita o lookup `title__unaccent__icontains` (R2). Exige `django.contrib.postgres` em
`INSTALLED_APPS` — sem isso o Django não registra o lookup e a consulta falha com
`FieldError`, não com erro de banco.

**Reversibilidade**: a operação tem `reverse` (`DROP EXTENSION`). Nenhum dado é migrado, nenhum
backfill é necessário, e reverter não perde informação.

### Nada mais

| Modelo | Muda? |
|---|---|
| `catalog.Movie` | Não. `title`, `slug`, `poster_path`, `release_date` e `is_active` já existem e bastam. |
| `catalog.Genre` | Não. |
| `catalog.Trailer` | Não. |
| `screening.Room` | Não. |
| `screening.Screening` | Não. |
| `accounts.User` | Não. O estado de autenticação lido pelo cabeçalho é consumido, não modelado — e quem o produz é a feature de autenticação. |

**Restrição do Princípio II reafirmada**: nenhum código desta feature escreve ocupação de
assento nem antecipa a constraint `UNIQUE(sessão, assento)`. A feature é somente leitura.

---

## Campos usados pela busca

A consulta lê apenas o que a sugestão precisa exibir. A projeção é deliberadamente pobre.

| Campo de `Movie` | Uso na sugestão |
|---|---|
| `slug` | Monta `movie_path` (`/filmes/<slug>`) e serve de chave de lista no React |
| `title` | Texto da sugestão e alvo da correspondência |
| `poster_path` → `poster_url` | Miniatura que identifica o filme visualmente (FR-010) |
| `release_date` | Só o ano, para desambiguar títulos parecidos |
| `is_active` | Filtro: filme inativo não aparece |

**Campos de `Movie` deliberadamente ausentes da resposta**: `tmdb_id`, `original_title`,
`synopsis`, `backdrop_path`, `runtime_minutes`, `certification_br`, `synced_at`, `created_at`,
`updated_at`. Não são necessários para escolher uma sugestão, e resposta pública menor é
superfície menor.

---

## Consulta de leitura

`apps/catalog/selectors.py`:

```text
search_movies(termo: str, limite: int = 6) -> tuple[list[Movie], bool]
```

**Regras**:

1. Termo é normalizado com `strip()`. Vazio ou só espaços → retorna `([], False)` sem tocar o
   banco (FR-014).
2. Termo é truncado em 80 caracteres antes da consulta (caso de borda "termo muito longo").
3. Filtro: `is_active=True` **e** `title__unaccent__icontains=termo`.
4. Sem filtro por sessão — filme sem sessão à venda aparece (R6, decisão deliberada e oposta à do
   carrossel).
5. Ordenação: prefixo antes de conteúdo, desempate por `title` ascendente (R5).
6. Busca `limite + 1` linhas; se voltarem mais que `limite`, corta em `limite` e devolve
   `truncated=True` (FR-011). Uma linha extra é mais barata que um `COUNT(*)` separado.

**Determinismo**: a ordenação nunca depende da ordem física do banco. É o que permite ao teste
afirmar uma sequência exata de resultados sem ficar instável.

---

## Estados do lado do cliente

Não persistidos — vivem apenas enquanto o cabeçalho está montado.

| Estado | Origem | Observação |
|---|---|---|
| `termo` | digitação | limitado a 80 caracteres no próprio input |
| `situacao` | ciclo da busca | `ocioso` · `buscando` · `com-resultados` · `sem-resultados` · `erro` — os cinco são visualmente distintos (FR-012, FR-013, SC-008) |
| `sugestoes` | resposta do proxy | no máximo `limite` itens |
| `truncado` | resposta do proxy | dispara o aviso de "há mais resultados" |
| `indiceAtivo` | teclado | índice do `aria-activedescendant`; `-1` = nenhum |
| `sequencia` | contador interno | guarda contra resposta fora de ordem (R3) — não é exibido |

**`situacao` nunca é derivada de "lista vazia"**. `sem-resultados` e `buscando` produzem listas
vazias e precisam de mensagens diferentes; colapsá-los é exatamente o bug que o caso de borda
"busca lenta" descreve.

---

## Por que `Localidade` não está aqui

O pedido original incluía um seletor de localidade. Ele saiu do escopo por decisão do usuário em
2026-08-11, e o motivo é estrutural, não de preferência:

**`screening.Room` tem apenas `name` e `capacity`.** Uma sala existe sem lugar no mundo. Não há
cidade, não há cinema, não há nada a que uma localidade possa se ligar — filtrar por localidade
hoje significaria filtrar por um campo que não existe.

**Onde a localidade entraria, quando entrar** (registro para a feature futura, não compromisso
desta):

```text
screening.Venue   (novo)   — cinema: nome, cidade, estado
screening.Room             — ganha FK para Venue
```

Com isso, `Screening → Room → Venue → cidade` fecha a cadeia, e o seletor passa a filtrar tanto o
carrossel quanto a busca. Antes disso, o seletor seria um controle que não muda nada na tela — o
que o Princípio V classifica como interface sem decisão.

---

## Migração e ordem de aplicação

```text
catalog/0001_initial          (existente)
catalog/0002_unaccent_extension   (nova)  ← única migração desta feature
```

Nenhuma dependência de `screening` ou `accounts`. Aplicar com `python manage.py migrate` — o
`quickstart.md` traz o passo e como verificar que a extensão ficou ativa.
