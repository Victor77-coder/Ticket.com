# Data Model — Meus Ingressos e Compartilhamento por Link

**Feature**: `009-my-tickets-sharing` · **Data**: 2026-08-12

Um modelo novo, uma constraint, nenhuma alteração nos modelos existentes. Esta feature **não escreve**
em `Reservation`, `ReservedSeat`, `Payment` nem `Ticket` — é leitura, mais uma tabela ao lado.

---

## O modelo novo: `TicketShareLink`

```text
TicketShareLink
├── ticket        FK → Ticket, on_delete=CASCADE, related_name="share_links"
├── token         CharField(64), unique, editable=False
├── created_at    DateTimeField(auto_now_add=True)
└── revoked_at    DateTimeField(null=True, blank=True, default=None)
```

**Sem `expires_at`.** Registrado em Assumptions da spec: o link vale até ser revogado. Um prazo
criaria um segundo motivo de "este link não funciona" sem substituir a revogação, que precisa existir
de qualquer jeito.

**Sem contador de aberturas.** Está no escopo excluído. Contar aberturas é telemetria sobre quem
recebeu o ingresso, e a feature inteira existe para que essa pessoa **não** precise se identificar.

**`on_delete=CASCADE`** — ao contrário de quase todo o resto do projeto, que usa `PROTECT`. A
diferença é deliberada: `PROTECT` existe onde apagar destruiria histórico de venda (ingresso,
pagamento, reserva). Um link é autorização de leitura, não histórico; se um dia um ingresso for
apagado, seus links **têm** de morrer junto — um link sobrevivente apontando para ingresso inexistente
seria uma credencial órfã.

### O campo `token`

- **`secrets.token_urlsafe(32)`** — 256 bits de entropia, 43 caracteres. Preenchido num ponto só,
  em `services/compartilhamento.py`, e nunca editado depois (FR-025).
- **Não deriva de nada**: nem de `Ticket.pk`, nem de `Ticket.public_id`, nem da reserva, nem do
  pagamento, nem — sobretudo — do código assinado do QR (FR-026, FR-027).
- **`unique=True`** sobre a coluna inteira, incluindo os revogados. É o que garante FR-031: um token
  revogado continua ocupando o espaço dele, então nem o gerador nem um bug de reatribuição conseguem
  ressuscitá-lo.
- **Guardado em texto claro.** A troca está declarada em R3 e em Complexity Tracking, e vai para o
  README pelo Princípio VI. Resumo: FR-028/FR-035 exigem que o dono recopie o link depois, e hash
  torna isso impossível.

### A constraint

```python
models.UniqueConstraint(
    fields=["ticket"],
    condition=models.Q(revoked_at__isnull=True),
    name="um_link_ativo_por_ingresso",
)
```

**Índice PARCIAL, e ele é possível aqui.** `revoked_at IS NULL` é teste de nulidade sobre coluna —
imutável, que é o que o PostgreSQL exige de predicado de índice parcial.

É a terceira vez que o projeto encara essa escolha, e a forma muda por limitação do banco, nunca por
preferência:

| Feature | Garantia | Forma | Por quê |
|---|---|---|---|
| 007 | `UNIQUE(sessão, assento)` | **absoluta** | O predicado natural seria `expira_em > now()`, e `now()` não é imutável. A conciliação com a expiração foi para o serviço, sob `SELECT FOR UPDATE`. |
| 008 | `UNIQUE(reserva) WHERE aprovado` | **parcial** | `status = 'approved'` é imutável. É o que permite guardar todas as tentativas recusadas. |
| 009 | `UNIQUE(ingresso) WHERE revogado_em IS NULL` | **parcial** | `revoked_at IS NULL` é imutável. É o que permite **preservar os links revogados**, que R1 exige. |

Uma `UNIQUE(ticket)` sem condição impediria gerar um segundo link depois de revogar o primeiro —
justamente o que FR-032 promete ao dono.

### A migração

`0004_ticketsharelink.py` cria **o modelo e a constraint juntos**. Mesma disciplina de 007 e 008: o
modelo não entra sem a garantia que o protege. Aqui a consequência de separar seria menor que nas
duas anteriores — nenhum assento é vendido duas vezes por causa de um link — mas a regra do projeto é
uma só, e abrir exceção nela é como as regras acabam.

Nenhuma alteração de esquema em modelo existente. Nenhuma migração de dados.

---

## A operação de gerar link

`services/compartilhamento.py::gerar_link(ingresso)` — **idempotente do ponto de vista de quem pede**
(FR-028).

```text
1. Procurar link ativo do ingresso (revoked_at IS NULL).
   └── existe? devolve ele. Fim.

2. Não existe → criar dentro de atomic():
   token = secrets.token_urlsafe(32)
   INSERT ...

3. IntegrityError na constraint "um_link_ativo_por_ingresso"?
   └── Outra requisição venceu a corrida entre o passo 1 e o passo 2.
       Reler o link ativo e devolvê-lo.
```

**O passo 3 é a feature, não o tratamento de erro dela.** "Consultar se já existe e criar se não
existir" é exatamente o padrão que a concorrência quebra — duas requisições consultam, nenhuma
encontra, ambas criam. A 007 já tinha registrado isso ao escolher `idempotency_key` em vez de "existe
reserva parecida?".

Quem perde a corrida **não recebe erro**: recebe o link do vencedor. Do lado de fora, as duas
requisições devolvem o mesmo endereço, que é literalmente o que FR-028 promete. É por isso que a
prova de FR-029 é um teste de concorrência com transação real: sem `transaction=True`, as threads
compartilham conexão e o teste passa com ou sem a constraint.

**Não há `SELECT FOR UPDATE` aqui**, e a ausência é escolha. Na 007 o bloqueio era necessário porque
havia leitura-antes-de-escrita sobre linhas de terceiros (ocupações vencidas de outras reservas). Aqui
a única linha em jogo é a que está sendo criada, e a constraint resolve sozinha. Acrescentar bloqueio
seria mover a garantia do banco para a aplicação — o oposto do que o Princípio II pede.

## A operação de revogar

`services/compartilhamento.py::revogar_link(ingresso)`

```text
UPDATE ... SET revoked_at = now()
WHERE ticket = <ingresso> AND revoked_at IS NULL
```

**Um `UPDATE` condicional, não leitura seguida de escrita.** A condição `revoked_at IS NULL` no
próprio `WHERE` torna a operação idempotente sem transação e sem bloqueio: duas revogações
simultâneas resultam em uma linha afetada e uma linha não afetada, e as duas respondem "revogado" —
que é o estado que quem pediu queria.

**A linha nunca é apagada** (FR-031, FR-043). Preservá-la é o que faz o token morto continuar
ocupando o espaço dele e o que permite responder a um token revogado exatamente como a um token que
nunca existiu.

**Nada em `Ticket` é tocado** (FR-033, SC-010). O código do QR é derivado de `public_id` +
`screening_id` em `services/ingressos.py`, módulo puro que não conhece a existência de link nenhum.
A independência é estrutural — o teste que compara o código antes e depois de revogar existe para
pegar o dia em que alguém "simplificar" fundindo os dois segredos.

---

## As consultas de leitura

### `selectors.ingressos_do_cliente(cliente)` — a lista

Devolve dois conjuntos, já separados e já ordenados:

```text
base = Ticket.objects.filter(reserved_seat__reservation__customer=cliente)
                     .select_related(
                         "reserved_seat__seat",
                         "reserved_seat__screening__movie",
                         "reserved_seat__screening__room",
                     )

futuros  = base.filter(reserved_seat__screening__starts_at__gt=Now())
               .order_by("reserved_seat__screening__starts_at")     # crescente  (FR-007)

passados = base.filter(reserved_seat__screening__starts_at__lte=Now())
               .order_by("-reserved_seat__screening__starts_at")    # decrescente (FR-008)
```

**Três coisas nesta consulta são decisões, não detalhes:**

**1. Não há `sellable()`, e não pode haver.** É a armadilha herdada desta feature (R10). Toda consulta
de sessão escrita da 001 até a 008 passa por `Screening.objects.sellable()`, que é `published()` **e**
`starts_at > now()`. É o filtro certo para **estoque** e o errado para **histórico**:

- toda sessão que já começou deixa de ser `sellable` → o grupo "já aconteceram" ficaria
  permanentemente vazio, violando FR-009;
- toda sessão **cancelada** deixa de ser `sellable` → sumiria justamente o ingresso sobre o qual o
  cliente precisa da explicação que FR-011 exige.

Nenhuma constraint pega isso, nenhum teste pega por acidente, e a linha errada é mais parecida com o
resto do projeto do que a certa. O motivo fica escrito ao lado da função.

**2. A ordenação é explícita, contra o padrão do modelo.** `Ticket.Meta.ordering` é
`["reserved_seat__seat__row", "reserved_seat__seat__number"]` — herdado da 008, onde a ordenação certa
era a dos lugares **dentro de uma compra**. Herdá-la aqui daria uma lista ordenada por poltrona: uma
resposta plausível e errada, que passaria despercebida numa revisão rápida.

**3. `Now()` do banco, não `timezone.now()` do Python.** Mesma razão que o `Reservation.OCUPANDO` da
008 já registra: a fronteira futuro/passado é do servidor (FR-010), e o relógio de referência tem de
ser um só.

**O `select_related` não é otimização opcional.** O serializer toca filme, sala, sessão e assento de
cada linha; sem ele, doze ingressos viram dezenas de consultas. `django_assert_num_queries` fixa a
contagem no teste, para que remover o `select_related` quebre alguma coisa (R11).

### `selectors.ingresso_do_dono(cliente, public_id)`

Mesma base, filtrada por `public_id` **e** por dono na mesma consulta. Ingresso de outro cliente
devolve `None`, e a view responde `404` — não `403`. Um `403` confirmaria que aquele `public_id`
existe, e `public_id` é o que vai dentro do código do QR (R12).

### `selectors.ingresso_por_token(token)`

```text
TicketShareLink.objects.filter(token=token, revoked_at__isnull=True)
                       .select_related(<mesma cadeia, a partir de ticket>)
                       .first()
```

**Token inexistente e token revogado convergem para o mesmo `None`** (FR-043) — o filtro
`revoked_at__isnull=True` faz a convergência acontecer na consulta, não num `if` da view. É a mesma
técnica que `get_sellable_screening` da 007 usa para fazer rascunho, cancelada, iniciada e inexistente
saírem iguais: quando os casos convergem cedo, não sobra caminho por onde a distinção vaze depois.

---

## O que a resposta expõe, por superfície

| Campo | Lista do dono | Ingresso do dono | **Página pública** |
|---|---|---|---|
| filme, sessão, sala, assento | ✅ | ✅ | ✅ |
| `codigo` (assinado) e `qr_svg` | ✅ | ✅ | ✅ |
| `id` (= `public_id`) | ✅ | ✅ | ❌ |
| `grupo` (`futuro`/`passado`) | ✅ | ✅ | ❌ |
| `sessao_cancelada` | ✅ | ✅ | ❌ |
| estado do link (`ativo`, endereço) | ❌ | ✅ | ❌ |
| nome/e-mail do comprador | ❌ | ❌ | ❌ |
| outros ingressos da compra | ❌ | ❌ | ❌ |
| valor, cartão, pagamento | ❌ | ❌ | ❌ |
| identificador de reserva ou pagamento | ❌ | ❌ | ❌ |

**A coluna pública é servida pelo `TicketSerializer` da 008, sem alteração** (R6, FR-058). Os campos
das duas primeiras colunas vivem em `MeuIngressoSerializer`, que **compõe** o primeiro em vez de
estendê-lo.

A separação não é sobre o que o serializer expõe hoje — hoje ele já expõe exatamente o recorte
autorizado. É sobre a **pressão de crescimento**: com um serializer só, o primeiro campo novo da área
do dono aparece na página pública no mesmo commit, em silêncio, e o teste de FR-042 vira a única coisa
entre isso e um vazamento. Com dois, quem precisa de um campo novo o acrescenta onde está
trabalhando — que é o lado não público.

**`public_id` fora da resposta pública** é a linha mais fácil de errar da tabela. Ele identifica o
ingresso nas rotas do dono e é inofensivo lá, porque aquelas rotas exigem sessão. Na página pública
ele seria um identificador reaproveitável (FR-041) e, pior, o valor exato que vai dentro do código
assinado — entregá-lo ao lado do QR daria a metade não secreta do par de graça.

---

## Diagrama de relações

```text
Reservation ──< ReservedSeat ──1:1── Ticket ──< TicketShareLink
     │              │                   │              │
     │              │                   │              └─ token (opaco, 256 bits)
     │              │                   │                 revoked_at (preservado)
     │              │                   │                 UNIQUE(ticket) WHERE revoked_at IS NULL
     │              │                   │
     │              │                   └─ public_id ─┐
     │              │                                 ├─→ código assinado do QR
     │              └─ screening ────────────────────┘    (derivado, nunca armazenado,
     │                                                     TICKET_SIGNING_KEY, módulo puro)
     └─ customer  ← é por aqui que a posse é decidida

    Os dois segredos NUNCA se encontram:
    o token do link não conhece a chave de assinatura,
    e o código do QR não conhece a existência de link nenhum.
```
