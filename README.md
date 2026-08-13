# ticket.com — Plataforma de Ingressos de Cinema

Resposta ao Desafio Elite Dev 2026 (Verzel). Venda e validação de ingressos: catálogo do TMDb,
sessões, mapa de assentos, pagamento simulado, ingresso com QR e portaria.

**No ar:** <https://ticketcom-app.onrender.com>

No plano gratuito do Render a primeira visita do dia pode levar cerca de um minuto — o serviço
dorme após 15 minutos parado. Depois disso responde normal. As credenciais estão na seção
[Dados de teste](#dados-de-teste).

---

## Documentação — configurar e executar

### O que sobe

| Camada | Tecnologia |
|---|---|
| Back-end | Django 5 + Django REST Framework (Python 3.12) |
| Front-end | Next.js 15 (App Router) + React 19 |
| Banco | PostgreSQL 16 |
| Catálogo | TMDb — consumido **apenas** pelo back-end |
| Orquestração | Docker Compose |

| Serviço | Endereço |
|---|---|
| Interface web | <http://localhost:5003> |
| API | <http://localhost:8000> |
| PostgreSQL | `localhost:5438` |

A porta **5438** evita colidir com um PostgreSQL local em 5432. A interface usa **5003** e não
5000: no macOS o AirPlay Receiver escuta na 5000 e o `ControlCenter` intercepta a requisição
antes do Docker, respondendo 403.

### Pré-requisitos

- Docker e Docker Compose
- Uma chave de API do TMDb: <https://www.themoviedb.org/settings/api>

### 1. Variáveis de ambiente

```bash
cp .env.example .env
```

Preencha no `.env`:

```bash
POSTGRES_DB=ingressos
POSTGRES_USER=ingressos
POSTGRES_PASSWORD=<escolha uma>
POSTGRES_PORT=5438

# Gere com: python -c "import secrets; print(secrets.token_urlsafe(50))"
DJANGO_SECRET_KEY=<gere uma>
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,backend

# Gere com o MESMO comando, mas PRECISA SER UM VALOR DIFERENTE da DJANGO_SECRET_KEY.
TICKET_SIGNING_KEY=<gere outra>

TMDB_API_KEY=<sua chave do TMDb>

NEXT_PUBLIC_SITE_PORT=5003
API_BASE_URL=http://backend:8000
```

`DJANGO_SECRET_KEY`, `TICKET_SIGNING_KEY` e `TMDB_API_KEY` nunca são commitados. O
`.env.example` traz só os nomes.

**Sem `TICKET_SIGNING_KEY` o back-end não sobe.** Um valor padrão em código viraria o segredo
real de todo mundo que não leu esta seção, e o QR passaria a ser forjável por quem leu o
repositório. Ela é separada da `DJANGO_SECRET_KEY` de propósito: vazar a chave da aplicação
compromete sessões; vazar a do ingresso compromete a catraca.

### 2. Subir os serviços

```bash
docker compose up -d --build
```

### 3. Migrações

```bash
docker compose exec backend python manage.py migrate
```

Isso também cria a extensão `unaccent` do PostgreSQL, exigida pela busca (digitar "cacador"
encontra "Caçador"). Conferir:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\dx unaccent"
```

### 4. Importar o catálogo do TMDb

```bash
docker compose exec backend python manage.py sync_tmdb --limit 20
```

Persiste título, sinopse, arte, duração, gênero, classificação indicativa e a chave do trailer.
Depois deste passo o TMDb pode ficar fora do ar sem afetar a navegação nem a compra. O comando
é idempotente.

Se a chave estiver vazia ou inválida, o comando falha e o catálogo permanece vazio — não há
filmes de fallback no repositório.

### 5. Semear o cenário de demonstração

```bash
docker compose exec backend python manage.py seed_demo
```

Cria as quatro contas, duas salas e **12 sessões publicadas** com ingressos disponíveis. A
primeira execução, em base vazia, roda direto.

Da segunda execução em diante o comando **recusa e explica**. A grade também pode ser produzida
pelo painel do organizador, e o sistema não registra de onde veio cada sessão — então trata
qualquer grade existente como perda possível, em vez de apagar em silêncio. Para recriar:

```bash
docker compose exec backend python manage.py seed_demo --force
```

`--force` apaga reservas, pagamentos e ingressos da demonstração e remonta a grade. Use isso
depois de percorrer o fluxo várias vezes (lugar pago não volta ao estoque).

### 6. Abrir

<http://localhost:5003>

Entre pelo ícone de pessoa no canto direito do cabeçalho. Depois de entrar, o mesmo ponto
identifica você e oferece a saída.

### Percurso sugerido para avaliação

1. **Cliente** (`cliente1`) — home → filme → horário → assentos → pagamento com
   `4242 4242 4242 4242` → QR em "Meus ingressos".
2. **Portaria** (`portaria`) — pousa em `/portaria`. Escolha a sessão da porta e valide pelo
   código em texto do ingresso (a câmera também funciona em `localhost` e no deploy HTTPS).
3. **Organizador** (`organizador`) — pousa em `/programacao`. Confira a grade, publique outra
   sessão se quiser; ela aparece à venda na hora.
4. **Segundo cliente** (`cliente2`) — entre e tente o mesmo assento já vendido: a reserva
   recusa. Ou compre outro lugar e compartilhe o ingresso por link.

O pagamento é simulado. O desfecho é decidido pelo **número do cartão**:

| Número | Desfecho |
|---|---|
| `4242 4242 4242 4242` | Aprovado — emite os ingressos |
| `4000 0000 0000 9995` | Recusado — saldo insuficiente |
| `4000 0000 0000 0069` | Recusado — cartão expirado |
| `4000 0000 0000 0002` | Recusado — banco recusou |

Qualquer outro número bem formado (16 dígitos, Luhn válido) também é aprovado. Validade e CVV
são conferidos quanto à forma e **não** participam da decisão. Número mal formado é erro de
preenchimento, não recusa de cobrança — a tela usa frases diferentes.

**A recusa não devolve o lugar.** A reserva segue viva até o vencimento original de dez minutos,
para trocar de cartão sem perder o assento.

### Testes (opcional)

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
```

Ponta a ponta, **a partir do host** (não do contêiner — ver [O que não funciona como
esperado](#o-que-não-funciona-como-esperado)):

```bash
cd frontend && npm install && npx playwright install chromium && npx playwright test --workers=2
```

`--workers=2` não é detalhe: com o número padrão o servidor de desenvolvimento do Next satura
e alguns testes caem por timeout.

---

## Dados de teste

Todas as contas usam a senha **`desafio2026`**:

| Papel | Usuário | Para onde vai ao entrar |
|---|---|---|
| Organizador | `organizador` | `/programacao` — a grade dele |
| Cliente | `cliente1` | `/` — o catálogo, para comprar |
| Cliente | `cliente2` | `/` |
| Portaria | `portaria` | `/portaria` — e não alcança o resto do site |

O seed também cria **Sala 1** (60 lugares) e **Sala 2** (40 lugares) e publica sessões futuras
de 12 filmes importados do TMDb (entre eles *A Odisseia*, *Homem-Aranha* e *Minions* no
carrossel). Há ingressos disponíveis nessas sessões.

Não há criação de conta nem recuperação de senha. Estas quatro contas são as únicas. O desafio
não pede auto-cadastro.

---

## Deploy

Front, API e Postgres sobem no mesmo painel, o [Render](https://render.com). O avaliador só
abre o endereço do front-end.

**Endereço no ar:** <https://ticketcom-app.onrender.com>

O Vercel não entra neste projeto: ele não roda Django nem PostgreSQL. No plano gratuito um web
service **não recebe** tráfego da rede interna, então o Next chama a API pela URL pública. A
primeira visita do dia acorda o Django pelo navegador (~1 min).

Credenciais: as mesmas da tabela [Dados de teste](#dados-de-teste).

A câmera da portaria funciona no deploy — o endereço é HTTPS.

### Como foi publicado (e como republicar)

O Blueprint lê o `render.yaml` no GitHub.

1. Publique este repositório no GitHub (branch `main`).
2. Em <https://dashboard.render.com>: **New** → **Blueprint** → selecione o repositório.
3. Quando pedir `TMDB_API_KEY`, cole a mesma chave do `.env` local. Se o Blueprint já existir
   e a variável estiver vazia, preencha em **ticketcom-api → Environment** e faça Manual Deploy
   desse serviço.
4. Apply.

O Render cria o Postgres (`ticketcom-db`), a API (`ticketcom-api`) e o site (`ticketcom-app`).
No primeiro deploy a API importa o catálogo, semeia as quatro contas e sobe a grade. Os deploys
seguintes só migram — não apagam o que o organizador programou.

Se o Render acrescentar um sufixo no nome (URL diferente da documentada), copie o endereço
**público do front** e atualize na API as variáveis `SITE_URL`, `CORS_ALLOWED_ORIGINS` e
`CSRF_TRUSTED_ORIGINS`. Sem isso o link de compartilhamento do ingresso aponta para o host
errado.

### Conferir no ar

- Home com carrossel e trilhas
- Entrar como `cliente1` → comprar → QR
- Entrar como `portaria` → cai em `/portaria`
- Entrar como `organizador` → cai em `/programacao`

---

## O que não funciona como esperado

Estes pontos existem de propósito ou são limitações conhecidas. Nenhum impede percorrer o
fluxo de avaliação.

**A primeira abertura do dia no Render pode levar cerca de um minuto.** No plano gratuito o
serviço dorme após 15 minutos parado. Espere o carregamento; depois responde normal. Não é
falha da aplicação.

**A câmera da portaria só funciona em contexto seguro** (`https` ou `localhost`). Em
`http://localhost:5003/portaria` na própria máquina, funciona. Abrindo **pelo IP da rede
local** — o gesto natural para testar com o celular — ela **não** funciona, e nenhuma
configuração da aplicação muda isso. A digitação manual do código fica visível o tempo todo,
lado a lado com a câmera. No deploy HTTPS a câmera funciona.

**Lugar pago não volta ao estoque.** Percorrer o fluxo de compra várias vezes esgota a sessão
usada. Localmente: `docker compose exec backend python manage.py seed_demo --force`. No
Render a grade do primeiro deploy permanece; escolha outro filme/horário ou publique uma
sessão nova como organizador.

**A expiração da reserva não é demonstrável ao vivo.** O prazo é fixo em dez minutos e não é
lido do ambiente — um prazo configurável viraria "dois segundos" na demonstração e a garantia
deixaria de ser a mesma que roda em produção.

**Não há criação de conta nem recuperação de senha.** Só as quatro contas do seed.

**Não há seletor de localidade.** O domínio modela um cinema, não uma rede: uma sala existe
sem cidade associada, então o seletor não teria o que filtrar.

**O "local" do evento é o nome da sala.** Data e preço aparecem na grade de horários; o local
é o cabeçalho sob o qual os horários se agrupam. Um campo "local" na sessão teria o mesmo
valor em todas as linhas.

**Não há cota legal de meia-entrada** (40% dos lugares). A meia é comprável; a conferência do
documento é humana e acontece na porta. A portaria mostra o tipo para o operador pedir o
documento — o tipo nunca é condição de entrada.

**Não há cancelamento nem estorno de ingresso pago.** `paga` é estado terminal nesta entrega.

**`/filmes/{slug-inexistente}` responde HTTP 200 em vez de 404.** A página "Filme não
encontrado" é exibida, mas o Next.js não troca o status depois que a renderização dinâmica
começou a ser transmitida. Afeta rastreadores, não o usuário.

**Os testes ponta a ponta não rodam dentro do contêiner.** A imagem do front-end é Alpine
(musl) e os navegadores do Playwright são compilados para glibc. Rode a partir do host, com a
aplicação no ar.

**O limite de tentativas de login vive em cache local.** Reiniciar o back-end zera os
bloqueios.

**A leitura do QR por um aplicativo de terceiro é verificada à mão** (celular apontado para a
tela). Os testes automatizados cobrem que o QR é SVG, tem contraste de fundo claro e que o
código em texto é o mesmo conteúdo assinado.

---

## Uso de IA

O desafio pede para contar as ferramentas, em que partes entraram, e o que foi feito sem
IA. Isso não é disclaim; é o rastro de como o projeto foi conduzido. A frase que importa
está na constitution: *"o problema não é a IA ter feito, é ninguém ter escolhido nada."*

Este projeto foi escrito **spec-driven**. Nenhuma feature entrou no código sem uma
especificação, um plano e uma lista de tarefas. Esses artefatos estão versionados no
repositório — não foram descartados depois que o código compilou.

A IA redigiu e implementou. As decisões foram minhas. Cada saída foi revisada por mim
contra a spec e contra a constitution **antes** de entrar no Git.

### Ferramentas

| Ferramenta | Onde entrou |
|---|---|
| **[Spec Kit](https://github.com/github/spec-kit)** | O método. Constitution, `/speckit-specify`, `/speckit-plan`, `/speckit-tasks`, `/speckit-implement`. Produziu a pasta [`specs/`](./specs/) e [`.specify/`](./.specify/). |
| **Claude Code** (Anthropic, Claude Opus) | A maior parte do fluxo Spec Kit, o back-end (modelos, serviços, serializers, views, comandos), autenticação, pagamento, portaria, painel do organizador (013), meia-entrada (014) e a maior parte dos testes. |
| **Cursor** | Identidade de marca (011), telas de compra (012), a camada de front-end das reservas (007), o deploy no Render, ajustes de vitrine e este README. |

Quem fez o quê está no próprio histórico, no trailer `Co-Authored-By` de cada commit.
Conferir:

```bash
git log --format="%(trailers:key=Co-Authored-By,valueonly)" | sort | uniq -c
```

Hoje: da ordem de 160 commits com Claude Code e 30 com Cursor, além do commit inicial do
template do Spec Kit. Não houve um commit gigante no último dia.

Não usei BMAD, PRD separado nem gerador de tela colado no enunciado do desafio. O equivalente
ao PRD é a constitution + as 14 specs.

### Como conduzi a ferramenta

A ordem, em cada uma das 14 features, foi a mesma. A ferramenta **não** recebia "faça um
sistema de ingressos". Recebia um recorte.

1. **Eu definia o recorte** — o que entra, o que fica congelado, o que a constitution
   proíbe reabrir. Isso ia para `/speckit-specify` como enunciado curto, muitas vezes com
   captura de tela ou com a frase da feature anterior que tinha deixado um buraco.
2. **A IA redigia spec, pesquisa, plano e tarefas.** Eu lia. Recusava o que dilatava o
   escopo. Emendava fronteiras. Só então autorizava `/speckit-implement`.
3. **A IA escrevia o código e os testes.** Eu revisava o diff contra a spec e contra os
   sete princípios. Trabalho que desfazia uma decisão minha era revertido — inclusive
   código que a própria feature tinha acabado de produzir.
4. **O rastro ficou no Git.** Spec, plano, pesquisa, contratos, checklist e quickstart de
   cada feature estão em `specs/00N-…/`. O contexto que a ferramenta lia a cada sessão está
   em [`CLAUDE.md`](./CLAUDE.md) (bloco gerido pelo Spec Kit) e na constitution.

A constitution prevalece sobre a sugestão da ferramenta. Está escrito nela: produzir código
não autoriza ignorar os princípios; o output deve ser revisado contra ela antes do commit.
Isso não é ornamentação — foi o que impediu, por exemplo, a 013 de criar coluna nova e a
014 de abrir um segundo caminho de reserva.

### Artefatos versionados

| Artefato | Onde está | Para que serve |
|---|---|---|
| Constitution | [`.specify/memory/constitution.md`](./.specify/memory/constitution.md) | As regras que a ferramenta foi obrigada a obedecer. Sete princípios, stack, o que está fora de escopo, portões de qualidade. |
| Spec, plano, pesquisa, tarefas, contratos, checklist e quickstart | [`specs/001`](./specs/001-movie-highlights-carousel/) … [`specs/014`](./specs/014-cartao-de-sessao-e-meia-entrada/) | Uma pasta por feature. A pesquisa registra a decisão, o motivo e o que foi **descartado**. |
| Contexto da ferramenta | [`CLAUDE.md`](./CLAUDE.md) | O que o agente lia ao abrir a sessão: feature atual, o que já estava fechado, as fronteiras que não podia cruzar. |
| Histórico | `git log` | Commits incrementais, mensagem descritiva, `Co-Authored-By` da ferramenta daquela fatia. |

A pasta `specs/` é a evidência de que a ferramenta não escolheu sozinha. Quem avalia pode
abrir qualquer `research.md` e ver a alternativa que foi recusada, não só a que entrou.

### O que foi feito sem IA

- O domínio (cinema, não show genérico) e o recorte do desafio: fluxo ponta a ponta fechado
  **antes** de qualquer profundidade.
- A stack: Django + Next.js + PostgreSQL, depois de descartar Nuxt — o PDF exige React.
- A constitution inteira. A IA não inventou os sete princípios; ela foi obrigada a
  obedecê-los. A ordem de construção (auth → compra → ingresso → portaria → só então o
  painel) também.
- Mapa de assentos em vez de venda por quantidade.
- Pagamento simulado com cartões **determinísticos**, não sorteio — para os dois caminhos
  serem exercitáveis de propósito.
- A portaria com exatamente quatro desfechos. O tipo do ingresso (inteira/meia) informa o
  operador; nunca é condição de entrada.
- O organizador pousa no painel mas **não** é confinado como a portaria: ele precisa ver o
  catálogo público para conferir que a sessão que publicou apareceu à venda.
- A meia-entrada ser **comprável**, não só informativa. Tomada depois de ver o custo das
  duas opções lado a lado na spec 014.
- O painel de assentos da grade ser **somente leitura**. Selecionar continua no mapa da
  007; um segundo caminho de reserva duplicaria a regra que `UNIQUE(sessão, assento)`
  protege.
- Tirar o preço do chip de horário e do topo da página depois de ver a grade montada. A
  informação estava repetida e a grade virava um mural de números. Essa decisão **desfez**
  trabalho da IA feito horas antes; está no histórico, não escondida.
- A cor da marca. As restrições (não colidir com cor de estado, contraste, anti-slop)
  eliminaram os outros candidatos; a medição foi da IA; o julgamento de adotar o que
  sobrou — e a ressalva de que a composição da home ainda é convencional — foram meus.
  [`specs/011-marca-sem-laranja/research.md`](./specs/011-marca-sem-laranja/research.md), R1.
- Não criar coluna nenhuma no painel do organizador (013). Não haver seletor de localidade.
  Não haver auto-cadastro. Não haver cota legal de meia. Cancelar sessão = parar de vender,
  e mais nada.
- A revisão de cada spec, de cada diff e da checagem anti-slop. Interface autoral é
  princípio da constitution (V) e é humano por definição.

### O que a IA fez

Redação dos artefatos em `specs/` a partir do recorte que eu dei. Implementação de back-end
e front-end. Testes — inclusive as provas de concorrência que **falham** se a garantia do
banco for removida. Medição de contraste e ΔE na 011. O deploy no Render (Cursor). Este
README, a partir das seções que o desafio pede.

### Decisões que parecem estranhas numa leitura rápida

O desafio avisa que muita escolha se justifica quando se conta como se chegou nela. Estas
são as que mais pedem esse contexto. Nenhuma foi "a IA preferiu assim".

**A recusa de pagamento não libera o assento na hora.** O Princípio II diz "pagamento
recusado DEVE liberar o assento". Depois da recusa o assento **continua com dono** (a mesma
reserva) e **continua com prazo** (os dez minutos originais). Nenhum dos dois defeitos que
o princípio previne acontece — assento preso sem dono, ou sem prazo. Liberar na recusa
faria quem digitou o cartão errado perder o lugar entre uma tentativa e a seguinte. A
leitura está registrada em
[`specs/008-payment-ticket-issuance/spec.md`](./specs/008-payment-ticket-issuance/spec.md),
não implementada em silêncio. Se não se sustentar em revisão, o caminho é emendar a
constitution.

**O código do QR é assinado, não cifrado, e não é guardado em coluna.** Ele é derivado do
ingresso quando pedido. Guardá-lo criaria a chance de a coluna e a chave discordarem depois
de uma rotação. A assinatura impede forjar; o sigilo do conteúdo não é o que protege a
catraca. O conteúdo carrega a identidade da sessão para a portaria conseguir o desfecho
"sessão errada" — sem isso, um ingresso legítimo na porta errada seria indistinguível de um
código inventado.

**O token do link de compartilhamento fica em texto claro no banco.** O hábito correto é
guardar segredo ao portador em hash. Aqui o dono precisa **reencontrar e recopiar** o link
depois. Com hash, o token existiria só no instante da criação: fechar a aba perderia o
link. O que se perde num dump do banco são os links já ativos — não a chave de assinatura,
então um dump sozinho **não** permite forjar QR. Mitigações: 256 bits, revogação definitiva,
`noindex`/`no-referrer`. Registrado em
[`specs/009-my-tickets-sharing/plan.md`](./specs/009-my-tickets-sharing/plan.md).

**O cookie de sessão é emitido pelo Next, não repassado do Django.** Repassar o `Set-Cookie`
de origem faria `Domain` e `Path` dependerem de como o Django enxerga o host, divergindo
entre Docker e Render. Emitindo no Next, o navegador enxerga uma origem só e o
`SameSite=Lax` vira defesa real. A sessão continua sendo do Django: hash de senha,
invalidação e prazo são dele.

**"Em cartaz" significa comprável, não "em exibição nos cinemas".** O TMDb tem `now_playing`,
e a trilha **não** vem dela: vem das sessões publicadas na plataforma. Num site de
ingressos, uma faixa com esse nome que leva a filme sem sessão à venda é promessa quebrada.
"Em alta" só mostra filme com sessão marcada pelo mesmo motivo. As alternativas (ordenar em
vez de filtrar, selo "indisponível") estão em
[`specs/004-home-movie-rows/research.md`](./specs/004-home-movie-rows/research.md) (R11).

**A trilha usa `scroll-snap` nativo; o carrossel foi escrito à mão.** Parece incoerência.
O carrossel precisa fechar ciclo e rotacionar sozinho pausando em três situações;
`scroll-snap` exigiria clonar slides. A trilha não faz nenhuma das duas coisas, e o CSS
entrega gesto de toque, inércia e teclado de graça. Repetir o padrão do carrossel ali
seria coerência aparente pagando em código. R1 da mesma pesquisa.

**`seed_demo` recusa da segunda execução em diante.** Até a 013, toda sessão vinha do
comando e apagar tudo era correto. Agora o organizador também produz a grade, e o sistema
**não registra a origem** de cada sessão (criar essa coluna na 013 teria sido escopo
escorregando). Sem marcador, "existe grade" significa existe qualquer sessão, e o comando
pede `--force` em vez de apagar trabalho alheio em silêncio.

**A portaria não alcança o catálogo; o organizador alcança.** Não é assimetria de segurança
— o catálogo é público. É produto: a portaria tem uma tela só, e cair no carrossel de
filmes seria cair no lugar errado. O organizador precisa da vitrine pública para conferir
o que publicou. A autorização de verdade continua no servidor (`403` por papel).

**A 011 trocou quatro valores e a home não mudou.** A disciplina de tokens da 006 fez a
troca de cor caber num arquivo. A composição da primeira dobra (arte em tela cheia, título
à esquerda, dois botões) é o arranjo de qualquer catálogo de streaming — registrado como
achado da checagem anti-slop, não como entregável da 012. A 012 recompôs filme, assentos e
pagamento e **deixou a home intocada de propósito**.

Cada uma dessas escolhas tem a alternativa descartada escrita ao lado, na spec ou na
pesquisa da feature. Abrir `specs/` e ler o `research.md` é ver o processo, não só o
resultado.
