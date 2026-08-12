# Data Model — Validação de Ingressos na Portaria

**Feature**: `010-gate-validation` · **Data**: 2026-08-12

**Uma coluna.** Nenhum modelo novo, nenhuma constraint nova, nenhuma migração de dados. E, apesar
disso, é a feature em que a garantia de unicidade é mais fácil de perder — porque desta vez não há
índice que a segure.

---

## A alteração: `Ticket.used_at`

```text
Ticket  (existente, 008)
├── public_id      UUID, unique          (inalterado)
├── reserved_seat  OneToOne → ReservedSeat (inalterado)
├── payment        FK → Payment          (inalterado)
├── issued_at      DateTimeField         (inalterado)
└── used_at        DateTimeField(null=True, blank=True, default=None)   ← NOVO
```

**Instante, e não booleano.** FR-021 exige que o desfecho **já utilizado** informe **quando** o
ingresso foi usado — é isso que permite ao operador julgar se é a mesma pessoa voltando ou outra com
uma captura de tela. Um `used = True` obrigaria a acrescentar a coluna do instante depois, numa
segunda migração, para uma informação que já era requisito.

**Nulo é o estado não utilizado**, e é terminal na outra direção: não existe "desutilizar". Estorno e
cancelamento estão fora de escopo.

**Nenhum `used_by`.** Guardar qual operador validou seria auditoria; nenhum dos quatro desfechos
depende disso, e contador de leituras e telemetria estão explicitamente fora de escopo. Registrado
na spec como suposição: se a auditoria virar requisito, o campo entra com a feature que o consome —
a mesma disciplina que manteve `used_at` fora até agora.

### A migração

`0005_ticket_used_at.py` acrescenta **só a coluna**. É a primeira migração da série que **não** traz
uma constraint junto, e a ausência é a decisão — não um esquecimento. O motivo está abaixo, e
precisa estar no comentário do modelo também: alguém vai olhar esta migração procurando o índice que
as três anteriores tinham.

---

## Por que não há constraint, e por que a garantia continua sendo do banco

As três features anteriores fecharam invariantes com índices:

| Feature | Invariante | Forma |
|---|---|---|
| 007 | um assento por sessão | `UNIQUE(sessão, assento)`, absoluta |
| 008 | um pagamento aprovado por reserva | `UNIQUE(reserva) WHERE aprovado` |
| 009 | um link ativo por ingresso | `UNIQUE(ingresso) WHERE revogado_em IS NULL` |
| **010** | **uma validação por ingresso** | **`UPDATE` condicional** |

**A diferença é de natureza, não de rigor.** As três primeiras proíbem **duas linhas coexistirem** —
e é exatamente isso que um índice sabe dizer. Esta proíbe uma **transição acontecer duas vezes**,
sobre a mesma linha.

Não existe índice que expresse isso:

- uma `CHECK` enxerga o **valor final** da linha, não a história dela — `used_at` preenchido é
  legítimo, tendo sido escrito uma ou duas vezes;
- uma `UNIQUE` precisa de duas linhas para comparar, e aqui há uma só.

**O que faz a garantia continuar sendo do banco:**

```sql
UPDATE screening_ticket
   SET used_at = now()
 WHERE id = %s AND used_at IS NULL
```

No PostgreSQL, sob `READ COMMITTED`, o segundo `UPDATE` sobre a mesma linha **bloqueia** até o
primeiro confirmar, e então **reavalia o predicado** contra a versão nova. Encontra `used_at`
preenchido, o `IS NULL` não casa, e a instrução afeta **zero linhas**.

A serialização é do banco. A aplicação não decide nada — ela **lê o resultado** da decisão:

```text
linhas afetadas == 1  →  VÁLIDO        (esta chamada marcou)
linhas afetadas == 0  →  JÁ UTILIZADO  (outra marcou antes)
```

**Alternativa rejeitada — `SELECT FOR UPDATE` e depois escrever**: também correto, e mais frágil. São
duas instruções, e a correção passa a depender de ninguém as separar numa refatoração. O `UPDATE`
condicional é indivisível por construção. (A 008 usa `FOR UPDATE` porque lá há **várias** condições
para revalidar sob o bloqueio; aqui a condição é uma só e cabe no `WHERE`.)

---

## A armadilha, escrita por extenso

**O código que qualquer pessoa escreve primeiro:**

```python
ingresso = Ticket.objects.get(public_id=...)
if ingresso.used_at is not None:
    return JA_UTILIZADO
ingresso.used_at = timezone.now()
ingresso.save()
return VALIDO
```

**Está errado.** É leitura seguida de escrita: duas requisições leem `None`, ambas passam pelo `if`,
ambas escrevem. Duas pessoas entram com o mesmo ingresso.

**E é a versão mais perigosa dessa classe de erro em todo o projeto**, por três razões somadas:

1. **Passa em todo teste de uma thread só.** Todos os cenários funcionais ficam verdes.
2. **Lê como a regra da spec.** "Se já foi usado, responda já utilizado; senão marque e responda
   válido" é literalmente o texto do requisito. Uma revisão de código atenta aprova.
3. **O banco não reclama.** Nas três features anteriores, a constraint recusava a segunda escrita e o
   erro aparecia. Aqui as duas escritas são legais — a segunda apenas sobrescreve o instante.

**A única coisa entre o projeto e uma portaria furada é o teste de concorrência**, e é por isso que
ele é escrito **antes** do serviço, e por isso a verificação de que ele prova alguma coisa —
substituir a escrita condicional pelo `if` e conferir que ele **falha** — é tarefa obrigatória.

---

## O pipeline de validação

`services/portaria.py::validar(codigo, sessao_da_porta)`

```text
1. verificar_codigo(codigo)                    ← módulo PURO da 008, sem tocar o banco
   └── falhou? ──────────────────────────────→ INVÁLIDO        [não escreve, não consultou]

2. buscar ingresso por public_id do payload
   └── não existe? ──────────────────────────→ INVÁLIDO        [não escreve]

3. payload["s"] == ingresso.sessão do banco?
   └── não? ─────────────────────────────────→ INVÁLIDO        [não escreve]

4. ingresso.sessão == sessão DA PORTA?
   └── não? ─────────────────────────────────→ SESSÃO ERRADA   [NÃO ESCREVE — FR-031]

5. UPDATE ... SET used_at = now() WHERE id = ? AND used_at IS NULL
   ├── 0 linhas ─────────────────────────────→ JÁ UTILIZADO    [não alterou nada]
   └── 1 linha ──────────────────────────────→ VÁLIDO
```

**Cada fronteira é uma decisão, não uma ordem qualquer:**

**1 vem antes de tudo** — Princípio III. A 008 deixou a função pura pronta exatamente para isto, e
`django_assert_num_queries(0)` em volta do serviço prova que este caminho não consulta o registro de
ingressos.

**2 e 3 devolvem o mesmo INVÁLIDO** — quem apresenta não recebe pista sobre onde o palpite chegou
perto (FR-029). O passo 3 é defesa em profundidade: o `s` é assinado e confiável, mas comparar com o
banco custa nada e transforma uma inconsistência de dados num desfecho claro em vez de numa exceção.

**4 vem antes de 5, e a ordem é a decisão de FR-030.** Um ingresso de outra sessão **e** já utilizado
responde **sessão errada** — é essa a informação que muda o que o operador faz. A ordem inversa
consumiria o desfecho mais útil.

**4 não escreve.** É o que faz o ingresso continuar valendo na porta certa (US6-4). Um ingresso
legítimo queimado na porta errada seria pior do que não ter a checagem.

**5 é a única escrita da feature inteira.**

### O que a leitura do passo 2 serve — e o que não serve

O objeto lido serve para **duas** coisas: conferir a sessão (passo 4) e montar a resposta (lugar,
filme, horário, sala).

**O `used_at` daquela leitura não decide nada.** É a diferença entre correto e quase-correto, e é
invisível em teste de uma thread: entre a leitura e o `UPDATE` cabe outra validação inteira. Quem
decide é o `rowcount`.

---

## A consulta das sessões da porta

`selectors.sessoes_da_portaria()`

```text
Screening.objects.published()
    .filter(starts_at__date = data de hoje no fuso do servidor)
    .select_related("movie", "room")
    .order_by("starts_at")
```

**NÃO USA `sellable()`, e não pode usar.** É a segunda vez que o mesmo filtro é o erro natural — a
009 registrou a primeira. `sellable()` é `published()` **e** `starts_at > now()`, e a porta precisa
exatamente do que o segundo termo exclui: **a sessão que já começou**. Gente chega atrasada, e a
portaria valida durante a sessão inteira. Uma lista que some com a sessão em andamento é uma lista
que não serve à porta.

A regra que emerge das duas aparições, e que vale escrever ao lado da função:

> **`sellable()` responde "dá para comprar?", e nenhuma outra pergunta.**

**Canceladas ficam fora** — não há entrada a receber, e a 007 já as exclui de `published()`. O
ingresso de uma sessão cancelada continua alcançando a portaria pelo código e sai como **sessão
errada**, com o aviso do cancelamento (FR-023). É o caso em que a informação extra dentro do desfecho
importa mais: sem ela, o operador negaria a entrada sem saber orientar a pessoa.

**As sessões do dia, e não uma janela em horas.** Uma janela ("das 2h atrás às 12h à frente") teria
duas pontas para explicar e mudaria de resultado conforme o instante em que a tela foi aberta. O dia
é a unidade que o operador tem na cabeça.

---

## O que NÃO muda, e é preciso vigiar

**`TicketSerializer` e `MeuIngressoSerializer` não ganham o campo de uso** (FR-048).

É a mesma pressão de crescimento que a 009 registrou, agora vindo do outro lado. O campo passa a
existir no modelo aqui, e acrescentá-lo ao serializer é uma linha — a partir daí "utilizado" aparece
na área do cliente e, pior, na **página compartilhada pública**.

A 009 deixou a ausência escrita no modelo e nos dois serializers justamente para este momento, e
`test_share_link_leakage.py` verifica a resposta pública **por inclusão** — a lista de campos
autorizados é fechada. O campo de uso entra na lista de **proibidos** daquele teste nesta feature,
para que a proteção seja explícita em vez de consequência.

**O formato do código e a chave de assinatura não mudam** (FR-046). Há ingressos emitidos; mudar
qualquer um dos dois os invalidaria em massa. A 008 já tinha registrado que o `s` entrou no conteúdo
assinado desde o começo justamente para não precisar mudar o formato agora.

---

## Diagrama do estado do ingresso

```text
                     emitido (008)
                          │
                          │  used_at = NULL
                          ▼
              ┌───────────────────────┐
              │   NÃO UTILIZADO       │
              └───────────┬───────────┘
                          │
        UPDATE ... WHERE used_at IS NULL
                          │
              ┌───────────┴───────────┐
              │                       │
       1 linha afetada         0 linhas afetadas
              │                       │
              ▼                       ▼
         ┌─────────┐         ┌────────────────┐
         │ VÁLIDO  │         │  JÁ UTILIZADO  │
         └────┬────┘         └────────────────┘
              │                       ▲
              │  used_at preenchido   │
              └───────────────────────┘
                    toda apresentação seguinte

    SESSÃO ERRADA e INVÁLIDO não aparecem neste diagrama
    de propósito: eles não são estados do ingresso, são
    desfechos de uma apresentação. Nenhum dos dois escreve.
```
