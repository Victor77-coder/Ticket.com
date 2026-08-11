# Quickstart — Cabeçalho Global do Site

**Feature**: `002-site-header-navigation` | **Date**: 2026-08-11

Este documento **continua** o [quickstart da feature 001](../001-movie-highlights-carousel/quickstart.md).
Ele assume o ambiente já de pé: banco em 5438, Django em 8000, Next em 5003, catálogo importado do
TMDb e seed rodado. Aqui está só o que muda.

---

## O que esta feature acrescenta ao setup

| Item | Novo? | Ação necessária |
|---|---|---|
| Extensão `unaccent` no PostgreSQL | sim | Uma migração nova (passo 2) |
| `django.contrib.postgres` em `INSTALLED_APPS` | sim | Já vem no código; nenhuma ação manual |
| Variável de ambiente | **não** | O proxy do Next reutiliza `API_BASE_URL`, que já existe |
| Dependência de front-end | **não** | Nenhuma biblioteca nova |

Nenhuma porta muda. Nenhum segredo novo.

---

## 1. Atualizar o código

```bash
git checkout 002-site-header-navigation
docker compose up -d --build
```

O `--build` é necessário porque `django.contrib.postgres` entra em `INSTALLED_APPS`.

---

## 2. Aplicar a migração da extensão

```bash
docker compose exec backend python manage.py migrate
```

Aplica `catalog/0002_unaccent_extension`, que executa `CREATE EXTENSION IF NOT EXISTS unaccent`.

Confirmar que a extensão ficou ativa:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\dx unaccent"
```

Deve listar uma linha com `unaccent`. Se não listar, a busca por acento não funcionará — ver
Problemas comuns.

---

## 3. Verificar a API de busca

```bash
curl "http://localhost:8000/api/v1/busca/?q=mat" | jq
```

Esperado: `200` com no máximo 6 itens, cada um com `slug`, `title`, `poster_url`, `year` e
`movie_path`.

Conferir a insensibilidade a acento com um filme do catálogo que tenha cedilha ou til no título:

```bash
# os dois devem devolver o mesmo filme
curl "http://localhost:8000/api/v1/busca/?q=coracao" | jq '.results[].title'
curl "http://localhost:8000/api/v1/busca/?q=coração" | jq '.results[].title'
```

Conferir o termo vazio — deve ser `200` com lista vazia, **não** erro:

```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/v1/busca/?q="
# 200
```

---

## 4. Verificar o proxy do Next

O navegador só conhece este endereço. É ele que precisa funcionar, não o do Django:

```bash
curl "http://localhost:5003/api/busca?q=mat" | jq
```

Deve devolver exatamente o mesmo payload do passo 3. Se este responder e o do passo 3 não, algo
está errado no `API_BASE_URL` do contêiner do front-end.

---

## 5. Verificar na interface

Abrir <http://localhost:5003>. O esperado:

1. O cabeçalho aparece no topo com **ticket.com**, o campo de busca e — quando a US3 for
   desbloqueada — o ícone de conta.
2. Rolar a página: o cabeçalho acompanha, sem cobrir o conteúdo em leitura.
3. Abrir um filme pelo carrossel (`/filmes/{slug}`): o **mesmo** cabeçalho está lá.
4. Clicar em **ticket.com** na página do filme: volta para a home.
5. Digitar três letras de um filme do catálogo: as sugestões aparecem abaixo do campo, com
   pôster e título.
6. Clicar numa sugestão: vai para a página daquele filme.
7. Digitar algo que não existe (`zzzz`): mensagem em português dizendo que nada foi encontrado —
   não uma lista vazia sem explicação.
8. A aba do navegador mostra `ticket.com` no título.

**Só pelo teclado**, do começo ao fim:

- Tab até o campo de busca, digitar, ↓ para descer nas sugestões, Enter para abrir, Esc para
  fechar a lista. O cursor nunca sai do campo enquanto se navega pelas sugestões.

---

## 6. Verificar as duas garantias que mais quebram

**A lista corresponde sempre ao termo atual (SC-005)** — digitar rápido um termo longo e apagar
até restarem duas letras. A lista final tem de corresponder às duas letras que ficaram no campo,
nunca a um termo já apagado. Coberto por teste automatizado, mas vale ver com os olhos.

**A busca sobrevive à queda do TMDb (SC-009)**:

```bash
docker compose exec backend env TMDB_API_KEY= python manage.py check
```

Recarregar e buscar: os resultados continuam iguais. A busca lê só o PostgreSQL.

---

## 7. Testes

```bash
docker compose exec backend pytest tests/test_search_api.py -v
docker compose exec frontend npm run test
docker compose exec frontend npm run test:e2e
```

---

## Problemas comuns

**`FieldError: Unsupported lookup 'unaccent'`** — `django.contrib.postgres` não está em
`INSTALLED_APPS`. É ele que registra o lookup; a extensão no banco sozinha não basta.

**A extensão não aparece no `\dx`** — o usuário do banco não tinha permissão para
`CREATE EXTENSION`. Com a imagem oficial do PostgreSQL o usuário de `POSTGRES_USER` é dono do
banco e tem permissão; se o banco foi criado à mão por outro usuário, rodar uma vez como
superusuário: `CREATE EXTENSION IF NOT EXISTS unaccent;`.

**Busca acha por acento mas não sem acento (ou o contrário)** — a migração não foi aplicada.
Conferir com `docker compose exec backend python manage.py showmigrations catalog`.

**Sugestões não aparecem, mas `curl` no Django funciona** — o proxy do Next não está alcançando o
back-end. Dentro do Compose o endereço é `http://backend:8000`, não `http://localhost:8000`.
Conferir `API_BASE_URL` no serviço `frontend` do `docker-compose.yml`.

**Sugestões aparecem e somem sozinhas** — provável perda de foco fechando a lista antes do
clique registrar. O fechamento por blur precisa ignorar o caso em que o novo alvo do foco está
dentro da própria lista.

**O carrossel ficou espremido** — o cabeçalho agora ocupa espaço no fluxo. Ajustar
`--altura-painel` em `tokens.css` descontando `--altura-cabecalho`, em um lugar só (R7).

**O ícone de conta não está no cabeçalho** — comportamento correto por enquanto. A US3 está
bloqueada até a feature de autenticação existir; ver Complexity Tracking no `plan.md`.
