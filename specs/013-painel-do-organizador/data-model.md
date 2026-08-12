# Data Model — Painel do Organizador

## Zero migração

Nenhuma tabela, nenhuma coluna, nenhuma constraint nova. Esta é a primeira feature do projeto que
escreve no banco sem tocar no esquema — e isso é resultado, não sorte: `Movie`, `Room`, `Seat` e
`Screening` foram modelados desde a 001 para a programação que só agora ganha tela.

Se durante a implementação aparecer a necessidade de uma coluna, **isso é sinal de que o escopo
escorregou**, não de que o modelo estava incompleto. A única candidata conhecida — origem da sessão
("seed" vs. "painel") — foi avaliada e recusada em FR-042 e está em Complexity Tracking.

## As entidades, e o que esta feature faz com cada uma

| Entidade | Leitura | Escrita | Observação |
|---|---|---|---|
| `Movie` | sim | **cria** (importação do TMDb) | Nunca edita filme existente. `tmdb_id` unique é a defesa contra duplicata |
| `Genre` | sim | cria/associa, via `sync_movie` | Efeito colateral do mapeamento reusado, não decisão desta feature |
| `Trailer` | sim | cria/atualiza, via `sync_movie` | Idem. É o que mantém a aba Trailers da 012 preenchida |
| `Room` | sim | **cria, renomeia, troca capacidade** | Troca de capacidade recria os `Seat` |
| `Seat` | sim | **cria e apaga** (só com zero ocupação) | PROTECT em `ReservedSeat.seat` é a rede de segurança |
| `Screening` | sim | **cria, edita rascunho, publica, cancela** | `UNIQUE(room, starts_at)` é a garantia do conflito |
| `Reservation`, `ReservedSeat` | **só leitura** | nunca | Consultadas para decidir se a capacidade pode mudar |
| `Payment`, `Ticket`, `TicketShareLink` | nenhuma | nunca | Fora do alcance da feature |

## Ciclo de vida da sessão

Os três estados já existem em `Screening.Status`. O que esta feature acrescenta são as **transições
permitidas** e o que cada uma exige.

```
                    ┌──────────────────────────────┐
                    │  criar (publicar = false)    │
                    ▼                              │
            ┌───────────────┐                      │
   editar ──│   RASCUNHO    │──── publicar ───────┐│
  (livre)   └───────────────┘                     ││
                    │                             ▼▼
                 cancelar               ┌───────────────┐
                    │                   │  PUBLICADA    │◄── criar (publicar = true)
                    │                   └───────────────┘
                    │                           │
                    │                       cancelar
                    ▼                           ▼
            ┌─────────────────────────────────────────┐
            │              CANCELADA                  │  terminal
            └─────────────────────────────────────────┘
```

**Pré-condições, por transição:**

| Transição | Exige | FR |
|---|---|---|
| criar (rascunho) | preço > 0 · `(sala, horário)` livre | FR-022, FR-025, FR-027 |
| criar (publicada) | o acima **+** horário futuro **+** sala com ≥ 1 lugar | FR-026, FR-028 |
| editar | estado == rascunho · `(sala, horário)` livre · preço > 0 | FR-023, FR-024, FR-025 |
| publicar | estado == rascunho · horário futuro · sala com ≥ 1 lugar | FR-026, FR-028, FR-030 |
| cancelar | estado ∈ {rascunho, publicada} | FR-030 |
| qualquer coisa a partir de cancelada | **nada** — terminal | FR-024, US5 cenário 10 |

**O que cancelar NÃO faz** (FR-031): não estorna pagamento, não apaga ingresso, não devolve ao
estoque lugar já pago, não mexe em `used_at`. Ingressos de sessão cancelada continuam no histórico do
cliente (009) e viram "sessão errada" na portaria (010) — os dois comportamentos já existem e não são
reabertos.

**O que a publicação NÃO faz**: não marca o filme como "em alta" nem "em breve" (FR-046), e não cria
um conceito de visibilidade — `sellable()` continua sendo `published() AND starts_at > now()` e não
ganha responsabilidade nova (FR-033).

## Ciclo de vida da sala

```
criar(nome, capacidade) ──► Room + Seat[] gerados pela MESMA regra do seed
                                    │
                     renomear ──────┤  (sempre permitido — não afeta lugar nem venda)
                                    │
        trocar capacidade ──────────┤  permitido SE ocupação viva == 0 → Seat[] refeitos
                                    │  recusado SE ocupação viva > 0  → nada é apagado
                                    ▼
                              (não há apagar)
```

**Validação de capacidade** (FR-018): recusa ausente, não numérica, ≤ 0 e acima do teto.
O teto é `26 × SEATS_PER_ROW` — 26 é o alfabeto, e o corte explícito existe para não gerar
identificação de fileira ilegível em silêncio. Com `SEATS_PER_ROW = 10`, o teto é **260**.

**Geometria** (FR-017), inalterada e agora com dono único em `services/salas.py`:
- fileiras de `SEATS_PER_ROW` lugares, letra por fileira (`A`, `B`, …);
- capacidade que não fecha a fileira deixa a última incompleta — nenhum lugar é inventado;
- os últimos `ACCESSIBLE_SEATS_PER_ROOM` lugares da **última** fileira são de acessibilidade;
- sala menor que a cota: todos os lugares da última fileira viram acessíveis, e a criação **não**
  falha (o `min(...)` que garante isso é parte da regra extraída, não um detalhe do seed).

## Ocupação viva — a definição que NÃO é reescrita

A pergunta "esta sala pode mudar de capacidade?" é respondida por
`Reservation.OCUPANDO = Q(status=PAID) | Q(expires_at__gt=Now())`, consumida através de
`selectors.ocupacoes_vivas()`.

Os dois termos são necessários e nenhum basta — o comentário no modelo explica por quê, e esta
feature **não repete o argumento nem o reimplementa**. Consequências diretas aqui:

- reserva **paga** bloqueia a troca de capacidade para sempre;
- reserva **viva e não paga** bloqueia enquanto o prazo corre;
- reserva **vencida e não paga** não bloqueia — o lugar não está ocupado;
- ingresso emitido implica reserva paga, então já está coberto pelo primeiro caso.

`Now()` é a função do banco, não um instante do Python. Herdar isso é o motivo de consumir a
constante em vez de escrever a condição de novo.

## Entidades derivadas expostas ao painel

Nada disso é coluna. Tudo é calculado na consulta ou na serialização:

| Campo exposto | De onde vem | Cuidado |
|---|---|---|
| `lugares` (da sala) | `COUNT(seat)` | Pode divergir de `capacity` quando a capacidade excede o teto |
| `ocupacao` (da sessão) | `COUNT` sobre `reserved_seats` filtrado por `OCUPANDO` | Agregado em **uma** consulta na grade (R6), nunca `seats_taken` por linha |
| `pode_editar` | `status == draft` | Serializado para a interface **não** decidir sozinha a regra |
| `pode_publicar` | rascunho ∧ futuro ∧ sala com lugar | Idem — e o servidor revalida na ação |
| `ja_no_catalogo` | `tmdb_id ∈ Movie` | Uma consulta com `__in`, não uma por resultado |

`pode_editar` e `pode_publicar` existem para a interface **desabilitar com explicação**, e nunca
como autorização: a ação revalida tudo no servidor (FR-037).

## Fronteira de dados entre painel e público

Os serializers do catálogo carregam um aviso no topo: nenhuma resposta pública pode expor status de
sessão, capacidade da sala, contagem de vendidos ou custo. Esta feature **cria a superfície onde
esses campos aparecem**, e por isso a fronteira precisa ser dita:

| Campo | Público (catálogo, mapa, portaria) | Programação |
|---|---|---|
| `status` da sessão | **nunca** | sim |
| `capacity` / `lugares` da sala | nunca | sim |
| ocupação numérica | nunca (só `esgotada`/`has_available_seats` booleano) | sim |
| `preco` | sim (é o que se paga) | sim |
| `tmdb_id` | nunca | sim (é a chave da importação) |

Rascunho e cancelada **não aparecem** em nenhuma superfície pública (FR-032) — e não por filtro novo:
`get_sellable_screening` e `sellable()` já as excluem, e a 007 registrou que rascunho, cancelada,
iniciada e inexistente saem todas como o mesmo `404` justamente para não revelar a grade interna.
