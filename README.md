# Plataforma de Ingressos de Cinema

Venda e validação de ingressos de cinema — catálogo vindo do TMDb, sessões, mapa de assentos,
pagamento simulado, ingresso com QR assinado e validação na portaria. **O fluxo ponta a ponta está
fechado.** Resposta ao Desafio Elite Dev 2026 (Verzel).

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

# Assina o código em QR do ingresso. Gere com o MESMO comando acima, mas
# PRECISA SER UM VALOR DIFERENTE da DJANGO_SECRET_KEY — ver abaixo.
TICKET_SIGNING_KEY=<gere outra>

TMDB_API_KEY=<sua chave do TMDb>

NEXT_PUBLIC_SITE_PORT=5003
API_BASE_URL=http://backend:8000
```

`DJANGO_SECRET_KEY`, `TICKET_SIGNING_KEY` e `TMDB_API_KEY` nunca são commitados. O `.env.example`
traz só os nomes.

**Sem `TICKET_SIGNING_KEY` o back-end não sobe**, e isso é intencional: um valor padrão em código
viraria o segredo real de todo mundo que não leu esta seção, e o QR passaria a ser forjável por
quem leu o repositório.

**Por que ela é separada da `DJANGO_SECRET_KEY`**: são dois raios de comprometimento diferentes.
Vazar a chave da aplicação compromete sessões; vazar a do ingresso compromete a catraca. Usar a
mesma nas duas faz um incidente virar dois. Há teste que **falha** se um código assinado com a
`DJANGO_SECRET_KEY` for aceito.

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

Coloca **12 filmes à venda** e informa quais ficaram no carrossel e quais entraram só na trilha —
a vitrine é conferível sem abrir o navegador.

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

## Cartões de teste

O pagamento é **simulado**: não há transação financeira real nem provedor externo. O desfecho é
decidido pelo **número do cartão**, por esta tabela — **determinístico, nunca por sorteio**, para
que os dois caminhos sejam exercitáveis de propósito por quem avalia.

| Número | Desfecho | O que aparece na tela |
|---|---|---|
| `4242 4242 4242 4242` | **Aprovado** | os ingressos, um por lugar, com QR |
| `4000 0000 0000 9995` | Recusado | Não havia saldo suficiente neste cartão. Tente outro cartão. |
| `4000 0000 0000 0069` | Recusado | Este cartão está expirado. Use um cartão com validade em dia. |
| `4000 0000 0000 0002` | Recusado | O banco emissor recusou a cobrança. Tente outro cartão ou fale com o banco. |

Qualquer outro número bem formado (16 dígitos com verificador de Luhn válido) é **aprovado**, para
que não seja preciso consultar esta tabela só para ver o caminho feliz. Validade e código de
segurança são conferidos quanto à forma e **não** participam da decisão — quem decide é o número.

Número mal formado é **erro de preenchimento**, não recusa de cobrança: são coisas diferentes, e a
tela diz isso com palavras diferentes. Numa você corrige o que digitou, na outra troca de cartão.

**A recusa não devolve o lugar.** A reserva segue viva até o vencimento original de dez minutos,
para que dê para trocar de cartão sem perder o assento. O raciocínio por trás disso está em
*Decisões que podem estranhar numa leitura rápida*.

---

## Testes

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
```

Ponta a ponta (ver a ressalva em Limitações conhecidas):

```bash
cd frontend && npx playwright test --workers=2
```

`--workers=2` não é detalhe: com o número padrão o servidor de desenvolvimento do Next satura e
alguns testes caem por timeout. Verificado que passam sozinhos.

Os testes obrigatórios são os que a constitution exige como prova: acesso público e ausência de
vazamento de dado de gestão nas respostas públicas (Princípio IV), resiliência à queda do TMDb
(Princípio VII), a garantia de que a lista de sugestões nunca exibe o resultado de um termo já
abandonado, a corrida de reserva — exatamente uma vence, e o teste **falha** se a constraint for
removida (Princípio II) —, a corrida de pagamento, que emite um único conjunto de ingressos e
**falha** se qualquer uma das duas garantias de banco for removida, a rejeição de QR forjado,
verificada **sem nenhuma consulta ao banco** (Princípio III), a ausência de vazamento na página de
ingresso compartilhado, inspecionada por valor na resposta inteira (Princípio III), e a corrida de
geração de link, que produz um único link ativo e **falha** sem o índice parcial.

Seis verificações foram feitas **quebrando o código de propósito**, porque uma prova que passa sem a
garantia que ela protege é pior do que prova nenhuma:

| Garantia removida | O que passa a acontecer | Teste que falha |
|---|---|---|
| `condition` do índice de link ativo | 5 pedidos simultâneos criam **5** credenciais ativas | `test_share_link_concurrency.py` |
| campo novo no serializer público | o campo aparece na página compartilhada | `test_share_link_leakage.py` |
| `sellable()` na consulta de ingressos | somem o histórico e o ingresso de sessão cancelada | `test_my_tickets_api.py` |
| escrita condicional → `if` + `save()` na portaria | **quatro** pessoas entram com o mesmo ingresso | `test_gate_concurrency.py` |
| `sellable()` na lista de sessões da portaria | some a sessão **em andamento**, que é a que a porta recebe | `test_gate_api.py` |
| campo de uso no serializer do ingresso | "utilizado" aparece na página compartilhada pública | `test_share_link_leakage.py` |

> Os testes ponta a ponta de pagamento **compram de verdade**, e lugar pago não volta ao estoque.
> Rodar a suíte muitas vezes consome a grade semeada; `seed_demo` devolve o cenário ao início.

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

**Trilhas da home** (`specs/004-home-movie-rows/`) — três faixas horizontais de cartazes abaixo do
carrossel: **Em cartaz** (o que dá para comprar agora), **Em alta** e **Em breve**, as duas
últimas vindas do TMDb. Cada cartaz leva à página do filme; quando não há sessão, a página informa
a data de estreia e explica o motivo.

**Escolha de assentos** (`specs/007-seat-selection/`) — mapa da sala a partir da sessão, seleção
com limite de seis lugares e reserva com prazo de dez minutos. O mapa é público; reservar exige
entrar, e só o papel cliente reserva — organizador e portaria recebem recusa **do servidor**.
Passado o prazo, os lugares voltam ao estoque sem nenhuma rotina agendada: a liberação é por
consulta, o que elimina a janela entre o vencimento e a passagem de um processo.

O mesmo lugar nunca é vendido duas vezes, e a garantia é do PostgreSQL: `UNIQUE(sessão, assento)`
na tabela de ocupação. A corrida perdedora falha no banco, não numa checagem prévia em Python.
`backend/tests/test_reservation_concurrency.py` prova isso com duas threads e conexões separadas —
e está verificado que ele **falha** se a constraint for removida.

**Pagamento simulado e emissão do ingresso** (`specs/008-payment-ticket-issuance/`) — a reserva é
revisada, cobrada de forma simulada e, se aprovada, vira ingresso na **mesma transação**. Um
ingresso **por assento**, não por reserva: quem entra na sala é uma pessoa por lugar. Cada um traz
seu código em QR e o mesmo código em texto, para a digitação manual que a portaria vai exigir.

Os dois caminhos são exercitáveis de propósito pelos cartões da tabela acima. Só o papel cliente
paga, e só o dono paga a sua — organizador e portaria recebem `403` **do servidor**.

O código do QR é assinado com `TICKET_SIGNING_KEY`, segredo próprio que nunca chega ao navegador,
e a assinatura é conferida **antes de qualquer consulta ao banco**. Código adulterado, código
assinado com outro segredo e código assinado com a `DJANGO_SECRET_KEY` são todos rejeitados, com
teste para cada caso.

Uma reserva nunca gera dois conjuntos de ingressos, e a garantia também é do PostgreSQL: índice
parcial `UNIQUE(reserva) WHERE aprovado` no pagamento e `UNIQUE(assento reservado)` no ingresso.
`backend/tests/test_payment_concurrency.py` prova isso com threads, e está verificado que ele
**falha** se qualquer uma das duas for removida.

**Meus ingressos e compartilhamento por link** (`specs/009-my-tickets-sharing/`) — até a 008 o
ingresso existia e era **inalcançável**: saindo da confirmação da compra, o cliente não tinha
caminho de volta. Agora ele tem endereço permanente em **`/meus-ingressos`**, alcançável pelo menu
da conta (só para o papel cliente) e pela própria confirmação.

A lista mostra **um item por lugar comprado**, cada um com seu QR e seu código em texto, separada
em dois grupos: **Próximas sessões**, com a que acontece primeiro no topo, e **Já aconteceram**, da
mais recente para a mais antiga. Os dois grupos vêm separados do servidor — a fronteira é decisão
dele, não do relógio do navegador. Quem nunca comprou vê um estado vazio escrito para gente, com
saída para o catálogo. Ingresso de sessão cancelada **continua na lista**, com aviso: some da venda,
não do histórico.

Cada ingresso tem endereço próprio, e é lá que mora o **link de compartilhamento**. A página do
link é pública, abre sem conta nenhuma e mostra **apenas** filme, sessão, sala, lugar e o QR —
nunca quem comprou, nunca os outros ingressos da mesma compra, nunca valor ou dado de pagamento.
`backend/tests/test_share_link_leakage.py` inspeciona a resposta pública inteira **por valor** e
falha se qualquer um desses aparecer; está verificado que ele **falha** quando um campo é
acrescentado ao serializer público.

**O link é credencial ao portador, e isso é assumido.** Compartilhar ingresso é entregar o direito
de entrar — é para isso que a pessoa manda o ingresso a quem vai com ela, e uma página
compartilhada sem o QR seria decorativa. Daí as duas contrapartidas: o token tem 256 bits de
entropia, e o dono pode **revogar** o link a qualquer momento e gerar outro. Um link revogado nunca
volta a valer, e responde exatamente como um link inventado — distinguir contaria a quem está
adivinhando que um palpite chegou perto.

O token do link é **distinto do código do QR**, e os dois têm ciclos de vida independentes:
revogar um convite não pode queimar uma entrada paga.
`backend/tests/test_ticket_signature.py` compara o código antes e depois de revogar e exige que
seja byte a byte o mesmo.

Um ingresso tem **no máximo um link ativo**, e a garantia é do PostgreSQL: índice parcial
`UNIQUE(ingresso) WHERE revogado_em IS NULL`. `backend/tests/test_share_link_concurrency.py` prova
com threads, e está verificado que ele **falha** sem a constraint — sem ela, cinco pedidos
simultâneos criam cinco credenciais ativas, e o dono revogaria uma achando que revogou tudo.

**Validação na portaria** (`specs/010-gate-validation/`) — **é esta feature que fecha o fluxo ponta
a ponta**: catálogo → sessão → assento → pagamento → ingresso → **entrada**.

O operador entra com a conta `portaria`, escolhe **qual sessão aquela porta está recebendo** e
valida — pela câmera ou digitando o código escrito no ingresso. Cada apresentação produz um de
**quatro desfechos**, distinguíveis por símbolo e título antes de qualquer cor: **pode entrar**,
**já foi usado** (com a hora do primeiro uso), **ingresso de outra sessão** (com a sessão a que ele
pertence, para o operador orientar a pessoa) e **não reconhecido**.

**A escolha da sessão da porta não é conveniência de interface.** Sem ela o desfecho "sessão errada"
seria **impossível**: o código carrega a sessão a que o ingresso pertence, e comparar esse valor com
ele mesmo sempre dá igual. Entregar três desfechos onde a constitution exige quatro seria tela pela
metade.

Um ingresso legítimo apresentado na porta errada **não é consumido** — continua valendo na porta
certa. E "sessão errada" vem **antes** de "já utilizado" na ordem de decisão, porque é essa a
informação que muda o que o operador faz.

Um ingresso nunca é validado duas vezes, e **aqui a garantia muda de forma**: as três features
anteriores fecharam seus invariantes com índices `UNIQUE`. Este invariante é de **transição** —
"esta coluna só sai de nulo uma vez" —, e nenhum índice o expressa: uma `CHECK` enxerga o valor
final, não a história. A garantia é a forma da escrita,
`UPDATE ... WHERE used_at IS NULL`, e **o número de linhas afetadas é o desfecho**. Continua sendo o
banco decidindo: o segundo `UPDATE` bloqueia, reavalia o predicado contra a versão nova e afeta zero
linhas.

`backend/tests/test_gate_concurrency.py` prova com threads, e está verificado que ele **falha**
quando a escrita condicional é trocada pelo `if` natural — com **quatro** validações resultando em
"pode entrar". Sem constraint atrás dele, este teste é a única defesa da garantia, e por isso foi
escrito antes do serviço.

O código forjado é rejeitado **sem nenhuma consulta ao registro de ingressos**, reusando a
verificação que a feature de pagamento já deixou pronta em módulo puro.

---

## Decisões que podem estranhar numa leitura rápida

**A recusa de pagamento não libera o assento na hora.** O Princípio II da constitution diz
"pagamento recusado DEVE liberar o assento", e à primeira vista isto contraria a regra. Não
contraria, e a leitura está registrada em `specs/008-payment-ticket-issuance/spec.md`.

O critério é a frase seguinte do próprio princípio: "não existe estado intermediário durável em que
o assento esteja preso sem dono". Depois de uma recusa o assento tem **dono** — a mesma reserva, do
mesmo cliente — e tem **prazo correndo**, o vencimento original, intocado. Nenhum dos dois defeitos
que a cláusula previne acontece, e quem devolve o lugar ao estoque continua sendo o vencimento, por
consulta, sem rotina agendada.

Liberar na recusa seria pior para quem compra e não melhoraria a integridade: quem digitou o cartão
errado perderia o lugar para outra pessoa entre uma tentativa e a seguinte. A resposta de recusa
devolve `expira_em` justamente para que a ausência de mudança no prazo seja observável de fora.

**O código do QR é assinado, não cifrado, e não é guardado em coluna.** Ele é derivado do ingresso
quando pedido. Guardá-lo criaria a chance de a coluna e a chave discordarem depois de uma rotação,
e não há o que ganhar: a assinatura é o que impede forjar, não o sigilo do conteúdo.

O conteúdo carrega a identidade da **sessão** além da do ingresso, e isso é para a feature seguinte:
sem ela, um ingresso legítimo apresentado na porta errada seria indistinguível de um código
inventado, e a portaria não teria como produzir o desfecho "sessão errada" que o Princípio III
exige. Entrou agora porque acrescentá-lo depois invalidaria todo código já emitido.

**O ingresso não tem campo "utilizado".** A marcação de uso e a garantia de validação única nascem
juntas na feature da portaria — o mesmo cuidado que a 007 teve ao criar a ocupação de assento e sua
constraint na mesma migração. Uma coluna de estado que nada transiciona e nada protege seria
convite para alguém marcá-la sem a garantia atrás.

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

**A trilha usa `scroll-snap` nativo; o carrossel foi escrito à mão.** Parece incoerência e é o
contrário. O carrossel precisa fechar ciclo — do último volta ao primeiro — e rotacionar sozinho
pausando em três situações distintas; `scroll-snap` exigiria clonar slides e não dá esse controle.
A trilha não faz nenhuma das duas coisas, e sem esses requisitos o CSS entrega gesto de toque,
inércia e rolagem por teclado de graça e melhor do que qualquer código nosso. Repetir o padrão do
carrossel ali seria coerência aparente pagando em código e em acessibilidade pior.

**"Em alta" só mostra filme com sessão marcada.** O TMDb devolve os filmes mais comentados da
semana, e a trilha não exibe todos: filtra pelos que já têm sessão publicada e futura na
plataforma. A consequência foi medida antes de aplicar e é significativa — com o catálogo atual a
trilha cai de 9 para 3 filmes, e os três já aparecem em "Em cartaz" logo acima. A trilha deixa de
ser descoberta de catálogo e vira "o que está bombando entre o que dá para comprar". Foi decisão
consciente: num site de ingressos, mandar o visitante para um filme sem nada à venda é atrito sem
contrapartida. As alternativas descartadas — ordenar em vez de filtrar, ou marcar com um selo —
estão em `specs/004-home-movie-rows/research.md` (R11), caso a decisão precise ser revista.

**"Em cartaz" significa comprável, não "em exibição nos cinemas".** O TMDb tem uma lista chamada
`now_playing`, e a trilha **não** vem dela: vem das sessões publicadas na plataforma. Num site de
ingressos, uma faixa chamada "Em cartaz" que leva a filmes sem sessão à venda é promessa quebrada.
As trilhas Em alta e Em breve, essas sim, vêm do TMDb — elas prometem descoberta, não compra.

**A busca combina debounce, `AbortController` e uma guarda por número de sequência.** Os dois
primeiros não bastam: uma resposta já decodificada pode chegar depois de uma mais nova, e a lista
passaria a mostrar o resultado de um termo já apagado. A guarda por sequência é o que fecha essa
janela.

**A tipografia é Archivo, não Inter, Roboto ou a fonte do sistema.** Archivo é fonte variável com
eixo de largura, o que significa que o título do filme sai expandido e o corpo sai normal **do
mesmo arquivo** — não há duas famílias a casar, e a coerência é estrutural em vez de fruto de bom
gosto. O corte expandido evoca cartaz de mostra de cinema, que é o oposto do genérico de
streaming. Licença **SIL Open Font License**: uso comercial, modificação e redistribuição
embutida, sem exigir atribuição na interface — a mais fácil de defender num repositório público.

A fonte é baixada em tempo de build e servida pelo próprio domínio, sem requisição a terceiro em
tempo de visita. É o mesmo raciocínio que mantém o TMDb fora do caminho de leitura, aplicado a
fontes. O fallback ajustado por métrica é o que impede o texto de saltar quando ela chega.

**O ritmo vertical tem dois níveis, e a diferença é o ponto.** O respiro entre o painel de
destaques e a primeira trilha é maior que entre trilhas consecutivas. Antes os dois eram o mesmo
valor, e era por isso que a home lia como lista uniforme em vez de página com hierarquia.

**Três gestos de movimento, e só três**: elevação do cartaz, transição do painel, deslocamento da
trilha. Retorno de pressão e brilho de carregamento são categorias distintas, com justificativa
própria. Todo movimento anima apenas `transform` — a barra do indicador do carrossel usa `scaleX`
em vez de animar `width`, e o brilho do esqueleto atravessa por `transform` em vez de repintar a
área a cada quadro.

**O cookie de sessão é emitido pelo Next, não repassado do Django.** Repassar o `Set-Cookie` de
origem faria o `Domain` e o `Path` dependerem de como o Django enxerga o host, divergindo entre
desenvolvimento e deploy. Emitindo aqui, o navegador enxerga uma origem só — e aí o `SameSite=Lax`
vira defesa real contra requisição forjada, em vez de exigir propagar o par
`csrftoken`/`X-CSRFToken` através do proxy, que é onde esse arranjo costuma quebrar em silêncio.
A sessão continua sendo do Django: hash de senha, invalidação no logout e prazo de validade são
dele.

**As rotas de reserva usam uma `SessionAuthentication` que não exige CSRF.** Parece o atalho que
abre um buraco, e é o contrário: a proteção continua onde ela funciona. O navegador nunca chama o
Django direto — ele chama o Next, na mesma origem, e o Next repassa o cookie numa requisição
servidor-a-servidor, que não carrega credencial ambiente de navegador nenhuma. Exigir
`X-CSRFToken` nesse salto não protege contra site de terceiro; só quebra o proxy. É a mesma
decisão que o login já tinha tomado com `csrf_exempt`, agora explícita em
`apps/accounts/authentication.py`. O que defende contra requisição forjada é o cookie
`httpOnly` + `SameSite=Lax` emitido pelo próprio Next.

**As três recusas de entrada produzem a mesma frase.** Usuário inexistente, senha errada e conta
inativa respondem "Usuário ou senha incorretos.". Não foi preciso unificar nada à mão: o
`authenticate()` do Django devolve `None` nos três casos, e os caminhos convergem sozinhos. É mais
seguro assim — a versão manual é exatamente onde esse requisito vaza depois, quando alguém
acrescenta um `if not user` com texto diferente e a enumeração de contas volta.

**O token do link de compartilhamento fica em texto claro no banco.** O hábito correto é guardar
segredo ao portador em hash, como se faz com senha e chave de API. Aqui a escolha é outra, e é
deliberada.

O motivo é de produto: o dono precisa **reencontrar e recopiar** o link ativo depois — abrir o
ingresso noutro dia e mandar de novo para quem vai com ele. Com hash, o token existiria só no
instante da criação: quem fechasse a aba perderia o link e teria de revogar e gerar outro. "Meu
link" deixaria de ser algo que se tem para virar algo que se recebe uma vez.

**O que se perde, dito sem eufemismo:** um vazamento do banco entrega links utilizáveis contra o
servidor vivo, e a página compartilhada renderiza QR válido para eles. **O que não se perde:** a
`TICKET_SIGNING_KEY` não está no banco, então um dump sozinho **não** permite forjar código nenhum
— o alcance se limita aos ingressos que já têm link ativo, e o dono revoga.

As mitigações que entraram junto: 256 bits de entropia (adivinhar é inviável), revogação imediata e
definitiva, o token nunca aparece em resposta que não seja a do próprio dono, e a página pública
declara `noindex` e `no-referrer` — o endereço **é** a credencial, e sem `no-referrer` ele vazaria
no cabeçalho `Referer` de qualquer navegação a partir dali.

Se a troca não se sustentar numa revisão, o caminho é mudar o requisito de recopiar o link — não
guardar hash em silêncio e deixar o botão de copiar quebrado. Registrado em
`specs/009-my-tickets-sharing/plan.md`, seção Complexity Tracking.

---

## Limitações conhecidas

**A leitura do QR por um leitor de terceiro é verificada à mão.** O requisito é que um aplicativo
leitor de QR decodifique o código da tela a 320px de largura. Automatizar isso exigiria uma
biblioteca nativa de decodificação (`zbar` e afins) trazida ao projeto só para essa asserção.

O que os testes automatizados cobrem no lugar: o QR é SVG vetorial (não pixeliza), renderiza com no
mínimo 128px de lado a 320px de viewport, mantém o fundo claro do token `--cor-fundo-qr` — leitor
precisa do contraste, e é por isso que essa superfície não segue o tema escuro —, e o código em
texto está presente, inteiro e igual ao conteúdo assinado. A leitura em si está no percurso 3 do
`specs/009-my-tickets-sharing/quickstart.md`, com celular.

**O link de compartilhamento não expira por tempo.** Ele vale até ser revogado. Um prazo criaria um
segundo motivo de "este link não funciona" para o avaliador distinguir do primeiro, sem substituir
a revogação — que precisa existir de qualquer jeito, e é imediata.

**Não há contador de aberturas do link.** Contar seria telemetria sobre quem recebeu o ingresso, e
a feature existe justamente para que essa pessoa não precise se identificar.

**Compartilhar não transfere titularidade.** O ingresso continua pertencendo a quem comprou; o link
só exibe. Revenda entre usuários está explicitamente fora de escopo pelo Princípio I.

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

**A leitura do QR pela câmera é verificada à mão.** Apontar uma câmera para um código real exige
hardware. O automatizado cobre o resto do caminho: o mesmo código, entregue por digitação, produz o
mesmo desfecho pelo mesmo caminho de servidor, e o percurso ponta a ponta da portaria roda inteiro
pela via digitada. A leitura em si está no percurso 5 do
`specs/010-gate-validation/quickstart.md`.

**A câmera da portaria só funciona em contexto seguro.** `getUserMedia` exige `https` ou
`localhost`. Abrindo `http://localhost:5003/portaria` na própria máquina, a câmera funciona. Abrindo
**pelo IP da rede local** — que é o gesto natural para testar com o celular — ela **não** funciona, e
nenhuma configuração da aplicação muda isso.

O que torna isso aceitável em vez de um buraco: a constitution já exige que a digitação manual esteja
"sempre disponível". A exigência que parecia redundante é justamente a que mantém a portaria
funcionando no cenário mais provável de demonstração. O campo de digitação fica visível o tempo todo,
lado a lado com a câmera — nunca escondido atrás da falha dela.

**O cliente não vê o estado de uso do ingresso.** O campo existe no modelo desde a feature da
portaria, mas "Meus ingressos" e a página compartilhada continuam exatamente como a feature anterior
as entregou. Exibir "utilizado" ao cliente é decisão de produto que não era preciso tomar para fechar
o fluxo — e a página compartilhada é **pública**, então o campo lá teria consequência real.
`test_share_link_leakage.py` lista o campo entre os proibidos.

**Não há registro de qual operador validou.** Seria auditoria, e nenhum dos quatro desfechos depende
disso. Contador de leituras e telemetria também estão fora: contar quantas vezes um link foi aberto é
informação sobre quem recebeu o ingresso.

**Não há validação offline.** Validar sem rede exigiria decidir o uso no aparelho e reconciliar
depois — e reconciliação é exatamente onde a validação única se perde.
— mesma disciplina que fez a 007 criar a ocupação de assento com sua constraint na mesma migração,
e a 008 criar pagamento e emissão na mesma transação. Exibir agora um selo que nada escreve seria
tela pela metade, que o Princípio V proíbe.

**O ingresso emitido não pode ser cancelado nem estornado.** `paga` é estado terminal nesta etapa.
Cancelamento com devolução ao estoque está listado na constitution como item posterior ao
fechamento do fluxo.

**Lugar pago não volta ao estoque, nem depois de o prazo original vencer.** É o comportamento
correto — o lugar está vendido —, mas tem uma consequência prática na demonstração: percorrer o
fluxo de compra várias vezes esgota a sessão usada. Para voltar ao cenário conhecido, rode
`docker compose exec backend python manage.py seed_demo` de novo.

**A expiração da reserva não é demonstrável ao vivo.** O prazo é fixo em dez minutos e não é lido
do ambiente — um prazo configurável viraria "dois segundos" na demonstração e a garantia deixaria
de ser a mesma que roda em produção. Esperar dez minutos parado também não é demonstração. Para
ver o comportamento, force o vencimento no banco seguindo
`specs/007-seat-selection/quickstart.md`; quem **prova** o comportamento são
`test_reserva_vencida_aparece_livre_no_mapa` e `test_outro_cliente_reserva_lugares_vencidos`, em
`backend/tests/test_reservation_api.py`.

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
