# Quickstart — Carrossel de Highlights de Filmes

**Feature**: `001-movie-highlights-carousel` | **Date**: 2026-08-10

Subir o ambiente do zero e ver o carrossel funcionando. Este documento é a base do `README.md`
do projeto, exigido pelo Princípio VI da constitution.

---

## Portas

| Serviço | Endereço | Origem |
|---|---|---|
| Interface web (Next.js) | `http://localhost:5000` | fixada pelo usuário |
| API (Django) | `http://localhost:8000` | padrão do Django |
| PostgreSQL | `localhost:5438` | fixada pelo usuário |

A 5438 evita colidir com um PostgreSQL local já rodando em 5432.

---

## Pré-requisitos

- Docker e Docker Compose
- Uma chave de API do TMDb — criada em <https://www.themoviedb.org/settings/api>

---

## 1. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencher no `.env`:

```bash
POSTGRES_DB=ingressos
POSTGRES_USER=ingressos
POSTGRES_PASSWORD=<escolha uma>
POSTGRES_PORT=5438

DJANGO_SECRET_KEY=<gere uma>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

TMDB_API_KEY=<sua chave do TMDb>

NEXT_PUBLIC_SITE_PORT=5000
API_BASE_URL=http://backend:8000
```

`TMDB_API_KEY` e `DJANGO_SECRET_KEY` **nunca** são commitados. O `.env.example` traz só os
nomes, com valores vazios.

---

## 2. Subir os serviços

```bash
docker compose up -d --build
```

Sobe três contêineres: `db` (5438), `backend` (8000) e `frontend` (5000).

---

## 3. Migrações

```bash
docker compose exec backend python manage.py migrate
```

---

## 4. Importar o catálogo do TMDb

```bash
docker compose exec backend python manage.py sync_tmdb --limit 20
```

Traz filmes em cartaz com título, sinopse, arte, duração, gênero, classificação indicativa
brasileira e a chave do trailer — tudo persistido localmente. Depois deste passo o TMDb pode
ficar fora do ar sem afetar o carrossel (Princípio VII).

O comando é idempotente: rodar de novo atualiza, não duplica.

---

## 5. Semear o cenário de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

Cria o que o desafio exige para percorrer o fluxo sem montar nada:

- **1 organizador**, **2 clientes** e **1 usuário de portaria**
- 2 salas
- ao menos **5 filmes com sessões publicadas e futuras** — os 5 painéis do carrossel

As credenciais são impressas ao final do comando e devem ser copiadas para o `README.md`.

---

## 6. Verificar

Abrir <http://localhost:5000>. O esperado:

1. O carrossel exibe o primeiro filme com arte, título, classificação, duração, gênero e sinopse
   curta.
2. O indicador mostra "1 de 5"; avançar e retroceder funcionam, inclusive circularmente.
3. Sem interação, o painel troca sozinho. Passar o ponteiro por cima pausa.
4. **Trailer** reproduz o vídeo dentro do próprio painel, sem abrir janela sobreposta.
5. **Ver ingressos** leva a `/filmes/{slug}` com as sessões futuras listadas.
6. Navegar só pelo teclado alcança todos os controles, com foco visível.

Conferir a API diretamente:

```bash
curl http://localhost:8000/api/v1/highlights/ | jq
```

Deve responder `200` com no máximo 5 itens, ordenados pela sessão mais próxima.

---

## 7. Testes

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
docker compose exec frontend npm run test:e2e
```

---

## Verificar a resiliência ao TMDb (SC-006)

Vale a pena conferir, porque é um requisito da constitution:

```bash
# remover a chave e reiniciar apenas o backend
docker compose exec backend env TMDB_API_KEY= python manage.py check
```

Recarregar <http://localhost:5000>: o carrossel continua completo, com todos os dados e imagens.
Só a reprodução do trailer depende de rede externa no navegador.

---

## Problemas comuns

**Porta 5438 ocupada** — outro PostgreSQL está usando a porta. Verificar com
`lsof -i :5438` e parar o processo, ou trocar `POSTGRES_PORT` no `.env`.

**Carrossel mostra o estado vazio** — não há filme com sessão publicada e futura. Rodar
`seed_demo` novamente; se o seed for antigo, as sessões podem ter ficado no passado.

**Botão "Trailer" ausente em algum filme** — comportamento correto (FR-015): aquele filme não
tem trailer no TMDb. O botão é omitido em vez de aparecer desabilitado.

**Imagens não carregam** — conferir se `image.tmdb.org` está em `remotePatterns` no
`next.config.ts`.
