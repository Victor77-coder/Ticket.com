# Research — Meus Ingressos e Compartilhamento por Link

**Feature**: `009-my-tickets-sharing` · **Data**: 2026-08-12

Quinze decisões. As que mais importam são **R2** (a constraint que impede dois links ativos), **R3**
(o token fica em texto claro no banco, e por quê), **R6** (a resposta pública é definida por
inclusão) e **R10** — a armadilha herdada desta feature, que é a `sellable()` de todas as features
anteriores.

---

## R1 — O link é um modelo próprio, não uma coluna no ingresso

**Decisão**: criar `TicketShareLink`, com chave estrangeira para `Ticket`, token, `revoked_at` e
`created_at`. **Não** acrescentar `share_token` a `Ticket`.

**Racional**: três requisitos da spec desmontam a coluna.

- **FR-031** — "um link revogado NUNCA volta a valer". Com coluna, revogar é escrever `NULL` ou
  sobrescrever; a linha antiga some, e a garantia de que aquele token não volta passa a depender de
  o gerador nunca repetir. Com linha própria e preservada, o token revogado continua ocupando o
  espaço dele: nem o gerador nem um bug de reatribuição conseguem ressuscitá-lo.
- **FR-043** — token inexistente e revogado respondem igual. Com linha preservada, a consulta acha o
  token, vê `revoked_at` preenchido e responde a mesma coisa do não encontrado. Com coluna, o
  revogado simplesmente não existe mais e a indistinguibilidade vira acidente feliz em vez de
  desenho.
- **FR-028/FR-029** — no máximo um link ativo, garantido pelo banco. Uma coluna `UNIQUE` não sabe
  dizer "único **entre os ativos**"; é a linha própria que permite o índice parcial de R2.

**Alternativas rejeitadas**:

- **Coluna em `Ticket`** — pelas três razões acima.
- **Guardar o token só em memória/cache** — revogação sobreviveria a restart por acaso, e a spec
  trata o link como algo que o dono reencontra depois (FR-035).

---

## R2 — `UNIQUE(ticket) WHERE revoked_at IS NULL`, índice parcial

**Decisão**: a garantia de "no máximo um link ativo por ingresso" (FR-028) é uma constraint de banco
— `UniqueConstraint(fields=["ticket"], condition=Q(revoked_at__isnull=True))` —, e não uma checagem
prévia no serviço.

**Racional**: é o terceiro capítulo da mesma história das features 007 e 008, e vale registrar a
sequência porque a forma muda por motivo técnico, não por gosto:

| Feature | Garantia | Forma | Por quê essa forma |
|---|---|---|---|
| 007 | um assento por sessão | `UNIQUE` **absoluta** | O predicado natural seria `expira_em > now()`, e o PostgreSQL exige predicado **imutável** em índice parcial. `now()` não é. |
| 008 | um pagamento aprovado por reserva | `UNIQUE` **parcial** | `status = 'approved'` é coluna comparada a literal — imutável. Por isso as tentativas recusadas cabem na mesma tabela. |
| 009 | um link ativo por ingresso | `UNIQUE` **parcial** | `revoked_at IS NULL` é teste de nulidade sobre coluna — imutável. Por isso os links revogados cabem na mesma tabela, que é o que R1 exige. |

"Consultar se já existe link ativo e criar se não existir" é exatamente o padrão que a concorrência
quebra: duas requisições consultam, nenhuma encontra, ambas criam. A 007 já registrou isso ao
escolher `idempotency_key` em vez de "existe reserva parecida?".

**O caminho da corrida**: a segunda inserção viola a constraint, o serviço captura `IntegrityError`,
relê e devolve **o link do vencedor**. Do lado de quem pediu, as duas requisições recebem o mesmo
endereço — que é literalmente o que FR-028 promete. A perdedora não vê erro: ela vê idempotência.

**Alternativa rejeitada**: `select_for_update()` na linha do ingresso antes de criar. Serializa, mas
põe a garantia num bloqueio de aplicação em vez de no banco — e o Princípio II é explícito: "esta
garantia DEVE ser aplicada no banco de dados, não apenas na aplicação". Aqui não há leitura-antes-de-
escrita de linhas de terceiros como na 007 (onde o `FOR UPDATE` é necessário por outro motivo), então
a constraint sozinha basta.

---

## R3 — O token fica em texto claro no banco, e isso é uma escolha registrada

**Decisão**: `secrets.token_urlsafe(32)` — 256 bits de entropia, 43 caracteres — armazenado **como
texto**, não como hash.

**Racional da entropia**: 256 bits torna a adivinhação inviável por qualquer margem que importe
(FR-025, FR-027). Não deriva de identificador do ingresso, da reserva ou do pagamento, e não deriva
do código do QR (FR-026). `secrets` é biblioteca padrão — **nenhuma dependência nova nesta feature**,
ao contrário da 008.

**Racional do texto claro, que é a parte que exige julgamento**: a alternativa correta pelo manual —
guardar só o hash, como se faz com senha ou chave de API — **é incompatível com FR-028 e FR-035**. Os
dois dizem que o dono reencontra o link ativo depois, para copiar de novo. Com hash, o token só
existiria no instante da criação: quem fechou a aba perderia o link e teria de revogar e gerar outro,
e "meu link" deixaria de ser algo que se tem para virar algo que se recebe uma vez.

**O que se perde, dito sem eufemismo**: um vazamento do banco entrega links de compartilhamento
utilizáveis contra o servidor vivo, e a página compartilhada renderiza QR válido. Vale notar o que
**não** se perde: a `TICKET_SIGNING_KEY` não está no banco, então um dump sozinho não permite
**forjar** código nenhum — o estrago é limitado aos ingressos que já têm link ativo, e o dono pode
revogar todos.

**Mitigações que entram junto**: token opaco de 256 bits; revogação imediata e definitiva; o token
nunca aparece em resposta que não seja a do próprio dono; a página pública declara `noindex` e
`no-referrer` (R9). E a decisão vai para o README pelo Princípio VI — é exatamente o tipo de escolha
que "pareceria estranha numa leitura rápida".

**Alternativas rejeitadas**:

- **Hash do token** — rejeitada por quebrar FR-028/FR-035, e essa é a forma do produto que o autor já
  fixou na spec.
- **Token assinado (`django.core.signing`) sem linha no banco** — seria elegante e é **fatal**: um
  valor assinado não pode ser revogado sem uma lista de revogados, ou seja, sem a tabela que se
  tentou evitar. Pior, aproximaria perigosamente o token do código do QR, que é justamente a fusão
  que a decisão 2 da spec proíbe.
- **Prazo de validade no token** — rejeitada em Assumptions da spec: criaria um segundo motivo de
  "este link não funciona" sem substituir a revogação, que precisa existir de qualquer jeito.

---

## R4 — Endereços: três da API, três do front

**Decisão**:

| Método | Endereço da API | Quem pode |
|---|---|---|
| `GET` | `/api/v1/meus-ingressos/` | cliente autenticado, só os dele |
| `GET` | `/api/v1/ingressos/<public_id>/` | o dono do ingresso |
| `POST` | `/api/v1/ingressos/<public_id>/link/` | o dono — gera, **idempotente** |
| `DELETE` | `/api/v1/ingressos/<public_id>/link/` | o dono — revoga |
| `GET` | `/api/v1/ingressos-compartilhados/<token>/` | **qualquer um**, sem sessão |

| Rota do front | O que é |
|---|---|
| `/meus-ingressos` | a lista (FR-001) |
| `/meus-ingressos/[id]` | o ingresso do dono, com as ações de link (FR-015) |
| `/ingresso/[token]` | a página pública (FR-036) |

**Racional**:

- `public_id` (UUID) é o identificador do ingresso nas rotas do dono. Já existe, já é a identidade
  pública que vai dentro do código assinado, e já foi escolhido na 008 por não ser sequencial. Usar a
  chave primária aqui reintroduziria o enumerável que a 008 evitou.
- `POST`/`DELETE` no **mesmo** endereço `/link/`: gerar e revogar são criar e apagar o mesmo recurso.
  Dois verbos num endereço é mais honesto que dois endereços (`/gerar-link/`, `/revogar-link/`) que
  descrevem ação em vez de recurso.
- `/ingresso/[token]` no front é curto porque vai ser colado em aplicativo de mensagens. Não é
  abreviação críptica: quem recebe lê "ingresso" e sabe o que vai abrir.
- O token vai no **caminho**, não em query string: query strings vazam com mais facilidade em logs de
  proxy e em históricos, e um caminho é o que a pessoa colando espera ver.

**Proxies do Next** (padrão já estabelecido em 002, 003, 007, 008 — o navegador nunca fala com o
Django): `app/api/link-do-ingresso/route.ts` com `POST` e `DELETE`. As rotas de leitura são Server
Components e chamam `lib/api.ts` direto, sem proxy, porque não partem do navegador.

---

## R5 — A página pública é endpoint `AllowAny` com `authentication_classes = []`

**Decisão**: o endpoint público do link declara `permission_classes = [AllowAny]` e
`authentication_classes = []`, exatamente como `SeatMapView` da 007. O Server Component que o consome
**não repassa o cookie de sessão**.

**Racional**: FR-036 exige que a página não peça conta e não conduza a entrada nenhuma. Com
`authentication_classes = []` isso deixa de ser comportamento e vira estrutura: não existe caminho
pelo qual essa view enxergue um usuário, então não existe caminho pelo qual ela decida algo com base
em quem está olhando — nem por engano, nem numa refatoração futura.

O padrão do projeto é `IsAuthenticated` por default no `REST_FRAMEWORK`; o acesso público é sempre
declarado explicitamente na view, com o motivo escrito, como a 007 já faz.

---

## R6 — A resposta pública é definida por **inclusão**, e o serializer dela não cresce

**Decisão**: a página compartilhada é servida pelo `TicketSerializer` **já existente da 008**, sem
alteração nenhuma. Os campos novos que a área do dono precisa vão para um `MeuIngressoSerializer`
separado, que **compõe** o primeiro em vez de estendê-lo.

**Racional**: o `TicketSerializer` da 008 hoje expõe exatamente `codigo`, `qr_svg`, `filme`,
`sessao`, `sala`, `assento` — que é, campo a campo, o recorte que FR-037 autoriza. A coincidência não
é sorte: a 008 já o desenhou sob o Princípio III.

O risco real desta feature não é o que o serializer expõe hoje, é a **pressão de crescimento**. A
lista do dono vai querer `situacao da sessão`, `existe link ativo`, `endereço do ingresso`. Se esses
campos forem acrescentados ao `TicketSerializer`, eles aparecem na página pública no mesmo commit, em
silêncio — e o teste de FR-042 seria a única coisa entre isso e um vazamento.

Manter dois serializers faz a pressão de crescimento apontar para o lado certo por construção: quem
precisa de um campo novo o acrescenta no `MeuIngressoSerializer`, porque é lá que ele está
trabalhando. E preserva FR-058: o `TicketSerializer` continua com a mesma forma nas respostas de
pagamento e de reserva.

**Alternativa rejeitada**: um serializer só com campos condicionais por contexto. Rejeitada porque
"este campo aparece dependendo de quem pergunta" é precisamente a estrutura em que um vazamento cabe
sem ninguém notar — e porque o teste de não vazamento passaria a depender de o contexto estar certo,
em vez de depender de o campo não existir.

---

## R7 — A fronteira futuro/passado e a ordenação são duas consultas, não uma

**Decisão**: um selector devolve dois conjuntos — futuros ordenados por `starts_at` **crescente**
(FR-007) e passados por `starts_at` **decrescente** (FR-008) —, e a API os entrega já separados.

**Racional**: a ordenação pedida muda de direção entre os grupos. Numa consulta só, isso exige
`Case/When` sobre a chave de ordenação, ou ordenar por uma expressão calculada — código que existe
para economizar uma consulta trivial de dezenas de linhas. Duas consultas, ambas apoiadas no índice
`idx_sessao_status_inicio` já criado na 004, custam menos que a engenhoca.

Entregar os grupos **já separados** também cumpre FR-010 sem discussão: o front não recebe uma lista
e um instante para comparar, recebe dois grupos. O relógio do navegador não participa da decisão.

**A fronteira é o `starts_at` da sessão**, conforme registrado em Assumptions da spec: `runtime_minutes`
é nulável no catálogo desde a 001, então "ainda em exibição" seria indefinido para parte do acervo.

---

## R8 — A lista mostra o QR de cada ingresso, reaproveitando o componente da 008

**Decisão**: `components/tickets/Ingresso.tsx` — o cartão com QR e código legível que a 008 escreveu
para a confirmação — é reaproveitado nas **três** superfícies: a lista, o ingresso do dono e a página
pública. A única alteração é tornar `indice`/`total` opcionais, para o caso de um ingresso só.

**Racional**: o escopo da feature pede que a área "liste os ingressos dele e exiba cada um com seu
código em QR". Um componente novo desenharia o mesmo cartão de novo, e a primeira divergência entre
as duas cópias seria o tamanho do QR — ou seja, a legibilidade na catraca, que é justamente o que
SC-005 protege.

Reaproveitar também tem uma consequência de segurança que vale nomear: o componente só aceita a forma
`Ingresso` (`filme`, `sessao`, `sala`, `assento`, `codigo`, `qr_svg`). Ele **não tem como** renderizar
comprador ou valor na página pública, porque não recebe esses campos. É R6 outra vez, do lado do
front.

A alteração é aditiva: props opcionais com o comportamento atual preservado quando presentes, para
que nenhuma asserção de `tests/ingresso.test.tsx` mude (FR-057).

**Detalhe de marcação**: `Ingresso` renderiza `<li>`. A página pública, com um ingresso só, o envolve
num `<ul>` de um item — uma lista de um é semanticamente correta e mais barata que dar ao componente
um prop de elemento.

**Custo**: até 12 QR gerados por carregamento da lista. Cada SVG comprime bem e o custo de CPU é de
milissegundos; a meta de desempenho do plano fixa ≤ 1 s para a lista completa, e o teste de contagem
de consultas garante que o custo não vira N+1 (R11).

---

## R9 — `noindex` e `no-referrer` na página compartilhada

**Decisão**: a rota `/ingresso/[token]` declara, no `metadata` do Next,
`robots: { index: false, follow: false }` (FR-044) e `referrer: "no-referrer"`.

**Racional**: o endereço **é** a credencial. Indexado, ele passa a ser encontrável por quem nunca o
recebeu — e revogar um por um não recupera o que já foi rastreado.

O `no-referrer` é a metade menos óbvia e resolve um vazamento real: sem ele, qualquer navegação a
partir daquela página manda o endereço completo — token incluído — no cabeçalho `Referer` do destino.
A página não tem links de saída por FR-039, mas `no-referrer` faz a garantia sobreviver ao dia em que
alguém acrescentar um.

**Não** entra `Disallow` no `robots.txt`: diria a mesma coisa num segundo lugar, e um `robots.txt`
público anunciando o prefixo de rota é informação dada de graça. O `noindex` na resposta basta e é
verificável em teste de componente.

---

## R10 — A armadilha herdada: `sellable()` some com o ingresso

**Decisão**: as consultas desta feature **não podem** usar `selectors.get_sellable_screening` nem
`Screening.objects.sellable()`. A lista de ingressos filtra por dono, e por mais nada.

**Racional**: toda consulta de sessão escrita da 001 até a 008 passa por `sellable()`, que é
`published()` **e** `starts_at > now()`. É o filtro certo para **estoque** — o que ainda dá para
comprar. É o filtro errado para **histórico**, e a diferença é invisível até o momento em que causa
o defeito:

- toda sessão que **já começou** deixa de ser `sellable` → o grupo "já aconteceram" ficaria
  permanentemente vazio, e FR-009 ("ingressos passados não podem ser escondidos") seria violado por
  uma linha que parece idiomática e igual a todas as outras do projeto;
- toda sessão **cancelada** deixa de ser `sellable` → o ingresso de uma sessão cancelada
  desapareceria da lista em vez de aparecer com o aviso que FR-011 exige. E é o pior caso possível:
  some justamente o ingresso sobre o qual o cliente precisa de explicação.

É o análogo desta feature ao achado da 008 (`expires_at` sozinho devolvendo o lugar vendido ao
estoque): não é um erro que o banco recuse, não é um erro que a suíte pegue por acidente, e a linha
errada é mais parecida com o resto do código do que a certa.

**Como fica protegido**: teste com ingresso de sessão já iniciada e ingresso de sessão cancelada, os
dois obrigatoriamente presentes na resposta. E o selector da lista fica em função própria, com o
motivo escrito ao lado, para que a próxima pessoa que for "padronizar" as consultas leia antes.

**Corolário, mesma família**: `Ticket.Meta.ordering` é por fileira e número do assento — herdado da
008, onde a ordenação certa era a dos lugares dentro de uma compra. A lista **precisa** ordenar por
horário da sessão e tem de dizer isso explicitamente; herdar a ordenação padrão daria uma lista
ordenada por poltrona, que é uma resposta plausível e errada.

---

## R11 — Uma consulta por grupo, provada por contagem

**Decisão**: `select_related("reserved_seat__seat", "reserved_seat__screening__movie",
"reserved_seat__screening__room")` nas consultas da lista, com o número de consultas fixado por
`django_assert_num_queries` no teste.

**Racional**: o serializer do ingresso toca filme, sala, sessão e assento de cada linha. Sem
`select_related`, doze ingressos viram dezenas de consultas — o mesmo caminho ingênuo que a 007 já
tinha evitado no mapa de assentos com `EXISTS`. A `ReservationSerializer.to_representation` da 008 já
usa exatamente esse `select_related`; aqui ele é repetido pelo mesmo motivo, agora com o teste que
falha se alguém o remover.

---

## R12 — Autorização: `403` por papel, `404` por dono

**Decisão**: permissão `IsCustomerParaIngressos`, subclasse de `IsCustomer` só para trocar a
mensagem; e as consultas do dono filtram por
`reserved_seat__reservation__customer=request.user`, devolvendo `404` para ingresso alheio.

**Racional**: é a mesma distinção que 007 e 008 já fixaram e que a spec repete em FR-048/FR-049.

- **`403` para organizador e portaria** — eles entraram, só não têm ingressos. Um `401` mandaria o
  organizador para a tela de entrada, que é caminho sem saída: entrar de novo não muda o papel.
- **`404` para ingresso de outro cliente** — um `403` confirmaria que aquele `public_id` existe, e
  `public_id` é o que vai dentro do código do QR. Confirmar existência é dar um oráculo.
- **A subclasse só pela mensagem** é o padrão que a 008 estabeleceu com `IsCustomerParaPagar`:
  "Apenas clientes podem reservar lugares." apareceria para quem abriu **Meus ingressos**, descrevendo
  outra tela — texto que o Princípio V proíbe.

E o `401` continua sendo traduzido na view, como em 007 e 008: o DRF converte "não autenticado" em
`403` quando o autenticador não oferece `WWW-Authenticate`, e o front precisa distinguir "conduza à
entrada" de "seu papel não tem ingressos" (FR-051).

---

## R13 — Revogação e cache: onde SC-009 pode morrer em silêncio

**Decisão**: a rota pública declara `export const dynamic = "force-dynamic"`, e a chamada à API
mantém o `cache: "no-store"` que `lib/api.ts` já aplica a tudo.

**Racional**: FR-031 e SC-009 dizem que o link revogado deixa de exibir o ingresso na primeira
abertura seguinte. Se a página compartilhada fosse renderizada estaticamente ou revalidada por
intervalo, a revogação continuaria correta no banco e **irrelevante na prática** — a credencial
seguiria sendo servida do cache por quanto tempo o cache durar.

É a falha mais discreta da feature: nada no back-end estaria errado, nenhum teste de serviço falharia,
e o comportamento observável seria "revoguei e o link continua abrindo". Por isso a declaração é
explícita na rota e vai como item de vigilância na revisão pós-desenho.

---

## R14 — O ponto de entrada na navegação é o menu da conta

**Decisão**: acrescentar "Meus ingressos" como item do `AccountMenu`, visível **apenas** quando
`sessao.papel === "customer"`.

**Racional**: o `AccountMenu` da 003 já é o lugar onde o menu autenticado vive, já rotula o papel e já
é ilha cliente. Acrescentar um item ali é uma linha; acrescentar um item de navegação principal no
`SiteHeader` mexeria na composição do cabeçalho, que é território da 002, para um destino que só
metade dos papéis tem.

Verificado em 2026-08-12: `tests/header.test.tsx` e `tests/e2e/header.spec.ts` **não** contêm asserção
de contagem ou enumeração de itens de navegação, então o acréscimo não exige tocar em nenhuma
asserção existente (FR-057).

A confirmação de compra (`/pagamento/[id]` no estado pago) ganha o mesmo destino, por FR-003.

---

## R15 — Nenhuma dependência nova

**Decisão**: `secrets` (biblioteca padrão) para o token. Nada é acrescentado a `pyproject.toml` nem a
`package.json`.

**Racional**: vale registrar por contraste. A 008 precisou justificar `qrcode` em Complexity Tracking
porque codificação QR é um padrão publicado com casos de borda reais. Geração de token aleatório não é
nada disso — é uma chamada de biblioteca padrão, e qualquer pacote que a embrulhe seria dependência
para não escrever uma linha.

O QR da página compartilhada usa o mesmo `qrcode` que a 008 já trouxe, pelo mesmo caminho
(`services/ingressos.py`), sem nenhuma geração no navegador.
