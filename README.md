# Plataforma de Ingressos de Cinema

Venda e validação de ingressos de cinema — catálogo vindo do TMDb, sessões, e o caminho até a
compra. Resposta ao Desafio Elite Dev 2026 (Verzel).

O projeto é conduzido por especificação: cada feature nasce de um spec, um plano e uma lista de
tarefas versionados em [`specs/`](./specs/), sob as regras de
[`.specify/memory/constitution.md`](./.specify/memory/constitution.md).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Back-end | Django 5 + Django REST Framework (Python 3.12) |
| Front-end | Next.js 15 (App Router) + React 19 |
| Banco | PostgreSQL 16 |
| Catálogo externo | TMDb — consumido **apenas** pelo back-end |
| Orquestração | Docker Compose |

---

## Portas

| Serviço | Endereço |
|---|---|
| Interface web | <http://localhost:5003> |
| API | <http://localhost:8000> |
| PostgreSQL | `localhost:5438` |

A 5438 evita colidir com um PostgreSQL local em 5432. A interface usa 5003 e **não** 5000: no
macOS o AirPlay Receiver escuta na 5000 e o `ControlCenter` intercepta a requisição antes do
Docker, respondendo 403.

---

## Setup

### Pré-requisitos

- Docker e Docker Compose
- Uma chave de API do TMDb — <https://www.themoviedb.org/settings/api>

### 1. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencher no `.env`:

```bash
POSTGRES_DB=ingressos
POSTGRES_USER=ingressos
POSTGRES_PASSWORD=<escolha uma>
POSTGRES_PORT=5438

# Gere com: python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_SECRET_KEY=<gere uma>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend

TMDB_API_KEY=<sua chave do TMDb>

NEXT_PUBLIC_SITE_PORT=5003
API_BASE_URL=http://backend:8000
```

`DJANGO_SECRET_KEY` e `TMDB_API_KEY` nunca são commitados. O `.env.example` traz só os nomes.

### 2. Subir os serviços

```bash
docker compose up -d --build
```

### 3. Migrações

```bash
docker compose exec backend python manage.py migrate
```

Isso também cria a extensão `unaccent` do PostgreSQL, exigida pela busca do cabeçalho — é o que
permite digitar "cacador" e encontrar "Caçador". Conferir:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\dx unaccent"
```

### 4. Importar o catálogo do TMDb

```bash
docker compose exec backend python manage.py sync_tmdb --limit 20
```

Persiste título, sinopse, arte, duração, gênero, classificação indicativa brasileira e a chave do
trailer. **Depois deste passo o TMDb pode ficar fora do ar sem afetar a navegação nem a compra.**
O comando é idempotente.

### 5. Semear o cenário de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

### 6. Abrir

<http://localhost:5003>

---

## Credenciais de seed

Todas com a senha **`desafio2026`**:

| Papel | Usuário |
|---|---|
| Organizador | `organizador` |
| Cliente | `cliente1` |
| Cliente | `cliente2` |
| Portaria | `portaria` |

Entre pelo ícone de pessoa no canto direito do cabeçalho. Depois de entrar, o mesmo ponto passa a
identificar você e oferece a saída.

---

## Testes

```bash
docker compose exec backend pytest          # 92 testes
docker compose exec frontend npm run test   # 80 testes
```

Ponta a ponta (ver a ressalva em Limitações conhecidas):

```bash
cd frontend && npx playwright test
```

Os testes obrigatórios são os que a constitution exige como prova: acesso público e ausência de
vazamento de dado de gestão nas respostas públicas (Princípio IV), resiliência à queda do TMDb
(Princípio VII), e a garantia de que a lista de sugestões nunca exibe o resultado de um termo já
abandonado.

---

## O que está pronto

**Carrossel de destaques** (`specs/001-movie-highlights-carousel/`) — 5 filmes em cartaz na home,
com trailer reproduzido dentro do próprio painel e botão que leva à página de sessões do filme.

**Cabeçalho global** (`specs/002-site-header-navigation/`) — faixa persistente em todas as páginas
com a identidade **ticket.com**, que leva à home, e busca de filmes por título com sugestões
ancoradas ao campo. A busca ignora acento e caixa, encontra por trecho do título e é operável só
pelo teclado.

**Autenticação** (`specs/003-user-authentication/`) — entrada, saída e sessão para os três papéis.
O ponto de conta no cabeçalho convida a entrar quando não há sessão e identifica o usuário quando
há. Depois de entrar, o visitante volta para a página de onde partiu.

---

## Decisões que podem estranhar numa leitura rápida

**A busca do navegador passa por um proxy do Next (`/api/busca`), não pelo Django direto.** Dentro
do Docker Compose o front-end alcança o back-end por `http://backend:8000` — um nome que só resolve
dentro da rede do Compose e que o navegador não consegue usar. O proxy mantém uma única verdade
sobre onde a API está, evita CORS no caminho quente da digitação e impede que o endereço do
back-end entre no bundle.

**A busca usa a extensão `unaccent`, não uma coluna normalizada.** Guardar uma cópia normalizada
do título criaria um segundo ponto de verdade para manter em sincronia com o TMDb. E o full-text
do PostgreSQL não serve: ele trabalha por palavra e não encontra "matr" dentro de "Matrix", que é
justamente o que a busca por trecho exige.

**A busca devolve filmes sem sessão à venda; o carrossel não os destaca.** As duas regras divergem
de propósito. Destaque é promessa de compra — apontar para uma página sem nada comprável seria a
tela pela metade que a constitution proíbe. Busca é navegação: esconder um filme que existe no
site faria a pessoa procurar pelo nome exato e ouvir "nada encontrado".

**O wordmark tem `aria-label` aparentemente redundante.** Não é: o nome é dividido em dois
elementos para o tratamento tipográfico, e o algoritmo de nome acessível insere um espaço na
fronteira entre eles. Sem o rótulo, o leitor de tela anuncia "ticket .com".

**A busca combina debounce, `AbortController` e uma guarda por número de sequência.** Os dois
primeiros não bastam: uma resposta já decodificada pode chegar depois de uma mais nova, e a lista
passaria a mostrar o resultado de um termo já apagado. A guarda por sequência é o que fecha essa
janela.

**O cookie de sessão é emitido pelo Next, não repassado do Django.** Repassar o `Set-Cookie` de
origem faria o `Domain` e o `Path` dependerem de como o Django enxerga o host, divergindo entre
desenvolvimento e deploy. Emitindo aqui, o navegador enxerga uma origem só — e aí o `SameSite=Lax`
vira defesa real contra requisição forjada, em vez de exigir propagar o par
`csrftoken`/`X-CSRFToken` através do proxy, que é onde esse arranjo costuma quebrar em silêncio.
A sessão continua sendo do Django: hash de senha, invalidação no logout e prazo de validade são
dele.

**As três recusas de entrada produzem a mesma frase.** Usuário inexistente, senha errada e conta
inativa respondem "Usuário ou senha incorretos.". Não foi preciso unificar nada à mão: o
`authenticate()` do Django devolve `None` nos três casos, e os caminhos convergem sozinhos. É mais
seguro assim — a versão manual é exatamente onde esse requisito vaza depois, quando alguém
acrescenta um `if not user` com texto diferente e a enumeração de contas volta.

---

## Limitações conhecidas

**As áreas por papel não existem.** Os três papéis autenticam e o cabeçalho identifica cada um,
mas organizador e portaria voltam para a mesma página de qualquer visitante — não há painel de
organizador nem tela de validação. Eles chegam com as features que lhes dão conteúdo real; criar
landings vazias agora contrariaria o Princípio V, que proíbe "em breve" na entrega.

**Não há criação de conta nem recuperação de senha.** As quatro contas do seed são as únicas. O
desafio não pede auto-cadastro e exclui recuperação de senha explicitamente.

**O limite de tentativas vive em cache local.** Reiniciar o back-end zera os bloqueios. Aceitável
no escopo de avaliação; num deploy real o cache seria compartilhado entre instâncias.

**Não há seletor de localidade**, embora tenha sido pedido. O domínio não representa cidade nem
cinema — uma sala existe sem lugar associado —, então o seletor não teria o que filtrar. Ele volta
quando houver o conceito de praça no modelo. Registrado em
`specs/002-site-header-navigation/spec.md`.

**Não há reserva de assento, pagamento, ingresso com QR nem tela de portaria.** São o núcleo do
desafio e ainda não foram construídos. O que existe hoje vai do catálogo até a listagem de sessões.

**`/filmes/{slug-inexistente}` responde HTTP 200 em vez de 404.** A página correta — "Filme não
encontrado" — é exibida, mas o Next.js não consegue trocar o status depois que a renderização
dinâmica começou a ser transmitida. Verificado também no build de produção, então não é artefato
do modo de desenvolvimento. Afeta rastreadores, não o usuário.

**Os testes ponta a ponta não rodam dentro do contêiner.** A imagem do front-end é Alpine (musl) e
os navegadores do Playwright são compilados para glibc. Rode a partir do host, com a aplicação no
ar: `cd frontend && npm install && npx playwright install chromium && npx playwright test`.

**Um teste e2e da feature 001 falha de forma intermitente** —
`highlights.spec.ts › descobre um filme, assiste ao trailer e chega às sessões`. O teste usa
`.first()` para achar o botão "Ver ingressos", que pega sempre o painel 0; se o carrossel
rotacionar durante o passo do trailer, esse painel sai da viewport e o clique falha. É falha do
teste, não do produto: verificado que ela ocorre igualmente com o cabeçalho removido. O ajuste é
mirar o painel ativo em vez do primeiro.

---

## Uso de IA

Este projeto foi desenvolvido com **Claude Code (Anthropic)** em um fluxo de spec-driven
development. O que a IA fez e o que não fez:

**Com IA** — redação dos specs, planos e listas de tarefas em `specs/`; implementação do back-end
(modelos, seletores, serializers, views, comandos de sincronização e seed) e do front-end
(carrossel, página de filme, cabeçalho e busca); redação dos testes; este README.

**Sem IA** — a definição do domínio e do escopo; a escolha da stack; as decisões de produto que
aparecem como "Decisões que podem estranhar" acima; a decisão de tirar o seletor de localidade do
escopo e de deixar login para uma feature própria; e a revisão de cada saída contra a constitution
antes do commit.

O histórico de commits e os artefatos em `specs/` são o rastro dessas decisões.
