# Plataforma de Ingressos de Cinema

Resposta ao **Desafio Elite Dev 2026** (Verzel).

Um organizador monta sessões a partir do catálogo do TMDb; o cliente navega pelos filmes em
cartaz, escolhe uma sessão e compra o ingresso; a portaria valida a entrada.

**Estado atual**: o carrossel de filmes em destaque e o caminho até a listagem de sessões estão
implementados. O fluxo de reserva, pagamento, emissão de ingresso e validação na portaria
**ainda não** — ver [O que ainda não está pronto](#o-que-ainda-não-está-pronto).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Back-end | Django 5 + Django REST Framework (Python 3.12) |
| Front-end | Next.js 15 (App Router) + React 19 + TypeScript |
| Banco | PostgreSQL 16 |
| Catálogo | TMDb (The Movie Database) |

---

## Portas

| Serviço | Endereço |
|---|---|
| Interface web | <http://localhost:5003> |
| API | <http://localhost:8000> |
| PostgreSQL | `localhost:5438` |

> **Por que 5003 e não 5000?** A porta 5000 foi a pedida originalmente, mas o macOS mantém o
> AirPlay Receiver escutando nela por padrão: o serviço `ControlCenter` intercepta a requisição
> antes do Docker e responde `403`. A 5438 do banco evita colidir com um PostgreSQL local em
> 5432.

---

## Como rodar

### Pré-requisitos

- Docker e Docker Compose
- Uma chave de API do TMDb — crie em <https://www.themoviedb.org/settings/api>

### 1. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha no `.env`:

- `POSTGRES_PASSWORD` — qualquer senha
- `DJANGO_SECRET_KEY` — gere com `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `TMDB_API_KEY` — **obrigatória** para importar o catálogo

O `.env` está no `.gitignore` e nunca é commitado.

### 2. Suba os serviços

```bash
docker compose up -d --build
```

### 3. Aplique as migrações

```bash
docker compose exec backend python manage.py migrate
```

### 4. Importe o catálogo do TMDb

```bash
docker compose exec backend python manage.py sync_tmdb --limit 20
```

Traz título, sinopse, arte, duração, gênero, classificação indicativa brasileira e a chave do
trailer — tudo persistido localmente. **Depois deste passo o TMDb pode ficar fora do ar sem
afetar o carrossel.** O comando é idempotente.

### 5. Semeie o cenário de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

Cria os usuários, as salas e as sessões publicadas. Também idempotente.

### 6. Abra

<http://localhost:5003>

---

## Credenciais de teste

Todas com a mesma senha: **`desafio2026`**

| Papel | Usuário |
|---|---|
| Organizador | `organizador` |
| Cliente | `cliente1` |
| Cliente | `cliente2` |
| Portaria | `portaria` |

> Os papéis já existem no modelo de dados, mas as telas de login e as áreas de organizador,
> cliente e portaria ainda não foram construídas. Hoje essas contas só são utilizáveis pelo
> Django admin (<http://localhost:8000/admin/>, com o usuário `organizador`).

---

## Testes

```bash
docker compose exec backend pytest            # 37 testes
docker compose exec frontend npm run test     # 34 testes
docker compose exec frontend npm run test:e2e # percurso ponta a ponta (Playwright)
```

Os testes não buscam cobertura ampla. Eles se concentram onde a
[constitution](.specify/memory/constitution.md) exige prova e onde o erro seria caro:

- **Vazamento de dado de gestão** na resposta pública (gate do Princípio IV)
- **Elegibilidade ao destaque** — sessão passada ou em rascunho não pode destacar um filme
- **Mapeamento do TMDb** — classificação brasileira e escolha do trailer
- **Comportamento do carrossel** — ciclo, as três condições de pausa, movimento reduzido
- **Desmontagem do trailer** ao trocar de painel

### Verificar a resiliência ao TMDb

O carrossel não pode depender da API externa. Para conferir:

```bash
docker compose exec backend pytest tests/test_highlights_api.py::test_responde_sem_chave_do_tmdb
```

---

## Decisões que valem explicação

**O carrossel não usa biblioteca.** Foi decisão, não teimosia. A rotação precisa pausar em três
situações distintas — ponteiro sobre a área, foco de teclado interno e trailer tocando —, e as
libs de carrossel expõem `pause on hover` e raramente as outras duas. Somando o controle fino de
ARIA que seria reconstruído por cima de qualquer lib, escrever ~150 linhas próprias saiu mais
barato. A trilha desloca por `translateX` com índice modular, o que torna a navegação circular
trivial. O custo assumido foi escrever o gesto de toque à mão.

**O trailer monta e desmonta o `<iframe>`.** Em vez de controlar o player pela API JavaScript do
YouTube, o iframe só existe enquanto o trailer toca. Desmontar encerra a reprodução de forma
garantida — é o mecanismo inteiro por trás de "para ao trocar de painel" e "no máximo um trailer
por vez", sem carregar script de terceiro na abertura da home e sem estado a manter sincronizado.

**Ao dar a volta, a trilha salta em vez de rebobinar.** Fingir fita infinita exigiria clonar
slides e reposicionar o scroll no meio da transição. Para 5 painéis não compensa.

**O TMDb só é acessado pelo comando de sincronização.** O endpoint que alimenta a home lê
exclusivamente o PostgreSQL. Com o TMDb fora do ar, o carrossel continua completo; só a
reprodução do trailer degrada, porque o vídeo é servido pelo YouTube.

**`has_available_seats` é booleano, não contagem.** O carrossel só precisa saber se ainda dá
para comprar. Expor o número de assentos vendidos seria vazar operação do organizador em uma
resposta pública.

**O modelo de usuário foi criado antes da feature de autenticação.** O Django exige que
`AUTH_USER_MODEL` seja fixado antes da primeira migração; adiar obrigaria a recriar o banco
depois. Só o campo `role` foi definido — as regras de permissão por endpoint ficam para a
feature de auth.

**Next.js em vez de Nuxt.** A intenção inicial era Nuxt, mas o desafio lista React como
tecnologia obrigatória. Next.js oferece o modelo mental equivalente dentro do ecossistema
exigido.

---

## O que ainda não está pronto

Honestidade sobre o estado do projeto, conforme pede o desafio:

- **Reserva, pagamento e ingresso** — não implementados. Os modelos `Seat`, `Reservation` e
  `Ticket` não existem, e isso é deliberado: a constitution exige que a venda de assento nasça
  junto com a constraint `UNIQUE(sessão, assento)` que a protege. Criar escrita de assento antes
  disso seria pior do que não ter.
- **Tela de portaria e validação de QR** — não implementadas.
- **Login e áreas por papel** — os três papéis existem no modelo, mas não há telas.
- **`has_available_seats` sempre retorna `true`** — é derivado da contagem de ingressos, que
  hoje é zero por não haver emissão. O contrato e a interface já tratam o estado esgotado; falta
  apenas o dado real.
- **Página de filme em `/filmes/{slug}` é mínima** — cartaz, título, sinopse e lista de sessões.
  O detalhe completo e o mapa de assentos pertencem à feature de reserva.
- **`/filmes/{slug-inexistente}` responde HTTP 200 em vez de 404** — a página correta ("Filme
  não encontrado") é exibida, mas o Next.js não consegue trocar o status depois que a
  renderização dinâmica começou a ser transmitida. Verificado também no build de produção, não
  é artefato do modo de desenvolvimento. Afeta apenas rastreadores, não o usuário.
- **Deploy** — não publicado.

---

## Uso de IA

O desafio recomenda usar IA e pede que o processo seja contado. Foi usada de forma intensiva e
deliberada.

### Ferramenta

**Claude Code (Opus 5)**, conduzido pelo fluxo **[Spec Kit](https://github.com/github/spec-kit)**
— `/speckit.constitution` → `/speckit.specify` → `/speckit.plan` → `/speckit.tasks` →
`/speckit.implement`.

### O que foi feito com IA

- Redação da constitution, da especificação, do plano, da pesquisa técnica, do modelo de dados,
  do contrato de API e da lista de 71 tarefas — todos versionados em
  [`specs/`](specs/001-movie-highlights-carousel/) e em
  [`.specify/memory/`](.specify/memory/constitution.md)
- Todo o código de back-end e front-end
- Os 71 testes automatizados
- Este README

### O que foi meu

- **A leitura do desafio e a definição do escopo**: domínio cinema, TMDb em vez de Ticketmaster,
  mapa de assentos em vez de venda por quantidade
- **A decisão de trocar Nuxt por Next** quando a IA apontou que o PDF exige React
- **A estratégia de versionamento**: commits divididos por contexto, direto na `main`, sem
  branches — avaliei que PRs num projeto solo de 7 dias custam mais do que rendem
- **A troca da porta 5000 para 5003** depois que o conflito com o AirPlay do macOS foi
  diagnosticado
- **A revisão e a aprovação de cada etapa** — nenhum artefato entrou no repositório sem leitura

### Por que os artefatos de spec estão versionados

O desafio diz que ver como a ferramenta foi conduzida conta a favor. O histórico de commits
segue a ordem real do processo: primeiro as regras do projeto, depois o que construir, depois
como, depois em que ordem, e só então o código. As decisões que parecem estranhas numa leitura
rápida estão justificadas nos arquivos de `specs/`, com as alternativas que foram descartadas e
o motivo.

---

## Problemas comuns

**A porta 5003 já está em uso** — verifique com `lsof -i :5003`. Se precisar trocar, ajuste
`docker-compose.yml`, `.env` e o script `dev` em `frontend/package.json`.

**O carrossel mostra "Nenhum filme em cartaz agora"** — não há filme com sessão publicada e
futura. Rode `sync_tmdb` e depois `seed_demo`. Se o seed for antigo, as sessões podem ter ficado
no passado.

**`sync_tmdb` falha com "TMDB_API_KEY não está configurada"** — preencha a variável no `.env` e
reinicie o backend com `docker compose restart backend`.

**Algum filme não tem botão "Trailer"** — comportamento correto: aquele filme não tem trailer no
TMDb. O botão é omitido em vez de aparecer desabilitado.

**As imagens não carregam** — confira se `image.tmdb.org` está em `remotePatterns` no
`frontend/next.config.ts`.
