# Phase 0 — Research: Pagamento Simulado e Emissão do Ingresso

**Feature**: `008-payment-ticket-issuance` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado.

**R1 a R4 são o núcleo do Princípio II nesta feature.** R3 é o achado que mais importa: a 007
deixou uma armadilha que só aparece quando existe reserva paga, e é a maior ameaça a "nunca vender
o mesmo lugar duas vezes" de toda a feature — maior do que a própria unicidade do pagamento.

**R5 a R7 são o Princípio III.**

---

## R1. Onde vive a garantia de "um conjunto de ingressos só"

**Decision**: **duas** constraints de banco, não uma.

| Constraint | Onde | Forma |
|---|---|---|
| Um pagamento **aprovado** por reserva | `Payment` | `UNIQUE(reservation) WHERE status = 'approved'` — índice **parcial** |
| Um ingresso por assento reservado | `Ticket` | `UNIQUE(reserved_seat)` — **absoluta**, sem predicado |

**Rationale**: as duas invariantes são diferentes e cada uma pega uma falha que a outra deixa
passar.

A segunda sozinha já impediria dois conjuntos de ingressos. Mas sem a primeira seria possível
existir **pagamento aprovado sem ingresso** — a segunda tentativa aprova, esbarra na unicidade do
ingresso e some. Com as duas, o estado "reserva paga sem ingresso" é impossível de representar, que
é exatamente o que o Princípio II exige ao dizer que aprovação e emissão não se separam.

**Por que o índice parcial é possível aqui e era impossível na 007**: a 007 quis
`UNIQUE(sessão, assento) WHERE expira_em > now()` e não pôde — o PostgreSQL exige predicado
imutável em índice parcial, e `now()` não é (R1 da 007). Aqui o predicado é `status = 'approved'`,
um literal comparado a uma coluna: imutável, e o índice parcial é legítimo.

**A diferença não é detalhe de implementação, é a razão de as duas features terem formas
diferentes.** A 007 não escolheu constraint absoluta por preferência; escolheu porque a condicional
não existia. Aqui a condicional existe, e é ela que permite guardar **todas** as tentativas
recusadas — exigidas por FR-012 — sem que a unicidade as proíba.

**Alternatives considered**:

- **`UNIQUE(reservation)` sem predicado em `Payment`** — proibiria a segunda tentativa depois de
  uma recusa, que é justamente o que a US2 exige. Sobraria guardar só a última tentativa e perder
  o rastro, ou não guardar recusa nenhuma e perder FR-012.
- **Uma coluna `paid` em `Reservation` com checagem na aplicação** — rejeitado pela constitution,
  que exige a garantia no banco. E é o padrão exato que a concorrência quebra: duas requisições
  leem `paid = false`, ambas seguem.
- **`OneToOneField` de `Ticket` para `ReservedSeat`** — é o que será usado; `OneToOne` no Django
  **é** `UNIQUE` na coluna. Registrado aqui para que ninguém o troque por `ForeignKey` achando
  que é equivalente: trocar remove a garantia sem mudar uma linha de lógica visível.

---

## R2. A ordem da transação de pagamento

**Decision**:

```
1. bloqueia a reserva                      SELECT ... FOR UPDATE
2. revalida sob o bloqueio:
      é do cliente · não vencida · não paga · sessão ainda vendável
3. autoriza (simulado, determinístico pelo número do cartão)
4. RECUSADO  → grava Payment(recusado) e RETORNA — a reserva não muda
5. APROVADO  → grava Payment(aprovado)
             → marca a reserva como paga
             → cria um Ticket por ReservedSeat
             → violação de unicidade → "esta reserva já foi paga"
```

**Rationale**: é a mesma forma da transação de reserva da 007 — bloquear, revalidar sob o
bloqueio, escrever, e tratar a violação de unicidade como resultado esperado.

**Uma diferença importante em relação à 007, a favor**: lá o `SELECT FOR UPDATE` não tinha o que
travar quando o assento nunca fora ocupado — não havia linha —, e a constraint era o único árbitro
(R3 da 007). Aqui **a linha da reserva sempre existe**, então o bloqueio serializa de verdade as
duas tentativas simultâneas. A constraint continua sendo a garantia exigida pela constitution, e
continua tendo de existir: o teste de concorrência precisa **falhar** sem ela.

**O passo 4 não pode levantar exceção.** Uma recusa que sobe como exceção dentro de
`transaction.atomic()` desfaz o `INSERT` do próprio `Payment` recusado, e o rastro exigido por
FR-012 desaparece — some justamente o registro que prova que a recusa aconteceu. A recusa é
**retorno normal** do serviço, não erro; só a aprovação e as falhas de estado (vencida, já paga,
sessão indisponível) usam o caminho de exceção. Ver R8.

---

## R3. A armadilha que a 007 deixou — a regra de ocupação viva

**Este é o achado mais importante da fase 0.** Sem ele, esta feature vende o mesmo lugar duas
vezes dez minutos depois de cada compra.

Hoje um lugar conta como tomado quando existe ocupação cuja reserva **ainda não venceu**:

```python
ReservedSeat.objects.filter(reservation__expires_at__gt=timezone.now())
```

Uma reserva **paga** não muda `expires_at`. Dez minutos depois da compra ela é, para essa regra,
indistinguível de uma reserva abandonada. As consequências, em cascata:

1. `get_seat_map` volta a mostrar o lugar **vendido** como livre;
2. `Screening.seats_taken` para de contar, e a sessão volta a parecer ter vaga;
3. pior de todos: `_liberar_ou_recusar` da 007 **apaga a linha de ocupação** de uma reserva paga,
   sob bloqueio, e entrega o lugar a outro cliente — enquanto o primeiro tem um ingresso emitido
   com aquele assento impresso.

O item 3 não dispara constraint nenhuma. A `UNIQUE(sessão, assento)` continua satisfeita, porque a
linha antiga foi apagada antes da nova entrar. **A garantia da 007 não protege contra isto**, e
nenhum teste existente pega, porque nenhum teste até hoje conseguia produzir uma reserva paga.

**Decision**: a regra de ocupação viva passa a ser

> uma ocupação está viva quando a reserva **está paga** **ou** ainda não venceu.

E, decisão igualmente importante: **a regra passa a existir em um lugar só**. Hoje ela está escrita
três vezes, em três formas diferentes:

| Onde | Como está hoje |
|---|---|
| `selectors.ocupacoes_vivas` | `filter(reservation__expires_at__gt=now())` |
| `Screening.seats_taken` | `filter(reservation__expires_at__gt=now())` — cópia literal |
| `services/reservas._liberar_ou_recusar` | `if ocupacao.reservation.expires_at <= agora` — em Python, sobre linhas já carregadas |

Três cópias de uma regra que agora ganha um segundo termo é a receita para corrigir duas e esquecer
a terceira — e a terceira é exatamente a que apaga linhas. A regra vira um único predicado
publicado pelo modelo (`Reservation.OCUPANDO`, um `Q`), consumido pelos três pontos.

**Alternatives considered**:

- **Empurrar `expires_at` para o futuro distante na aprovação** — funcionaria com uma linha e sem
  tocar em nada. Rejeitado: o campo passaria a mentir. "Vence em 2099" não é o vencimento da
  reserva, é uma flag disfarçada de data, e a próxima pessoa a ler o modelo teria de descobrir
  isso sozinha.
- **Anular `expires_at` na aprovação** — mesma objeção, e ainda quebraria a leitura de `is_expired`
  e a exibição do prazo em toda tela que já usa o campo.
- **Uma coluna `sold` em `ReservedSeat`** — duplicaria em cada ocupação um fato que pertence à
  reserva, e criaria a possibilidade de as duas discordarem.

**O que isso obriga**: teste que crie uma reserva paga, force `expires_at` para o passado, e afirme
que (a) o mapa continua mostrando o lugar tomado, (b) outro cliente **não** consegue reservá-lo, e
(c) a linha de ocupação **não** foi apagada. Sem ele, esta correção não tem prova.

---

## R4. Como o teste de concorrência prova alguma coisa

**Decision**: mesma máquina da 007 — duas threads reais, conexões de banco separadas, barreira
sincronizando no ponto crítico, `transaction=True`. Duas corridas distintas:

| Corrida | O que afirma |
|---|---|
| Dois pagamentos simultâneos da **mesma** reserva | exatamente uma aprovação, **um** conjunto de ingressos, e nenhuma reserva paga sem ingresso |
| Dois pagamentos de reservas **diferentes** na mesma sessão | ambos aprovam — o bloqueio é por reserva, não por sessão |

**Rationale**: a segunda corrida não é enfeite. Um bloqueio grosseiro demais — travar a sessão em
vez da reserva — passaria na primeira e serializaria a sala inteira. É o teste que impede
"resolver" a concorrência transformando o cinema numa fila de um.

**Verificação de que o teste testa** (herdada da 007 e obrigatória): removendo a
`UNIQUE(reservation) WHERE approved`, a primeira corrida precisa **FALHAR**. Um teste que passa sem
a constraint está provando que o `SELECT FOR UPDATE` funciona, não que o Princípio II está
garantido pelo banco.

**Armadilha já medida na 007, que vale aqui**: sob `pytest-django` padrão, cada teste roda dentro
de uma transação e as threads compartilham conexão — não há corrida, e o teste passa com ou sem
constraint. `transaction=True` e fechamento explícito das conexões por thread não são detalhe.

---

## R5. Como o código do ingresso é assinado

**Decision**: `django.core.signing.dumps` / `loads`, com **chave própria** e `salt` de domínio.

```
codigo = signing.dumps(
    {"t": <uuid público do ingresso>, "s": <id da sessão>},
    key=settings.TICKET_SIGNING_KEY,
    salt="ingresso.qr",
    compress=True,
)
```

**Rationale**: é HMAC-SHA256 com comparação em tempo constante, já revisado, já no Django, **sem
dependência nova**. Devolve texto seguro para URL, que serve tanto ao QR quanto à digitação manual
que a portaria vai exigir.

**Por que chave própria e não `salt` sobre a `SECRET_KEY`**: o `salt` dá separação de domínio, não
separação de segredo — quem obtiver a `SECRET_KEY` forja ingressos. A constitution pede um segredo
"que nunca sai do backend" para o ingresso, e a spec pede explicitamente que seja **distinto da
chave da aplicação** (FR-031). São dois raios de comprometimento diferentes: vazar a `SECRET_KEY`
compromete sessões; vazar a chave de ingresso compromete a catraca. Amarrar os dois faz um incidente
virar dois.

`salt="ingresso.qr"` entra além da chave, para que uma assinatura de ingresso nunca seja aceita em
outro contexto que venha a usar a mesma chave.

**Alternatives considered**:

- **JWT (`PyJWT`)** — dependência nova para fazer o que `django.core.signing` já faz, e traz
  semântica de expiração que o ingresso não quer: um ingresso não caduca por relógio, ele é
  consumido na portaria. `exp` mal configurado invalidaria ingressos legítimos.
- **HMAC escrito à mão** — o erro clássico é comparar com `==` em vez de comparação em tempo
  constante, e o segundo erro é esquecer a separação de domínio. Não há ganho em reescrever.
- **`TimestampSigner`** — acrescenta validade temporal ao código, pela mesma razão indesejada.
- **Guardar o código assinado numa coluna** — desnecessário: ele é derivável do ingresso a qualquer
  momento. Guardá-lo criaria a chance de a coluna e a chave discordarem depois de uma rotação.

---

## R6. O que vai dentro do código, e por que a sessão está lá

**Decision**: dois campos, `{"t": uuid, "s": screening_id}`.

**Rationale**: o `t` é a identidade pública do ingresso — **UUID, nunca a chave primária**
(FR-032). Sequencial revelaria quantos ingressos existem e convidaria a tentar o vizinho.

O `s` está lá por exigência explícita da spec (FR-033) e é para a **feature seguinte**: a portaria
precisa distinguir **"sessão errada"** de **"inválido"**, que são dois dos quatro desfechos que o
Princípio III obriga. Sem a sessão dentro do conteúdo assinado, um ingresso legítimo apresentado na
porta errada seria indistinguível de um código forjado — e a tela de portaria não teria como
produzir o desfecho que a constitution exige.

**Custo assumido**: o campo entra agora e só é consumido depois. É deliberado — acrescentá-lo
depois invalidaria todos os códigos já emitidos, porque o conteúdo assinado mudaria de forma.

**Payload curto de propósito**: `t` e `s` em vez de nomes por extenso. O QR cresce em densidade com
o tamanho do conteúdo, e um QR denso é o que falha de ler na câmera da portaria com pouca luz.

---

## R7. A verificação acontece antes do banco — e como isso é provado

**Decision**: `verificar_codigo(codigo)` é uma função **pura**: recebe texto, devolve o conteúdo, ou
levanta `CodigoInvalido`. **Não consulta o banco, não importa modelo, não recebe request.**

**Rationale**: FR-034 e o Princípio III. A verificação da assinatura antes da consulta não é
otimização — é o que impede que um código forjado vire carga no banco, e é o que garante que a
resposta a um código inválido não dependa de o registro existir.

**Como isso é provado**, e este é o ponto: a redação "antes de qualquer consulta" é fácil de
escrever e fácil de violar sem perceber. O teste usa a fixture `django_assert_num_queries(0)` do
`pytest-django` em volta da verificação de um código adulterado. Se alguém acrescentar uma consulta
— nem que seja um `.exists()` de conveniência —, o teste quebra e diz por quê.

É o mesmo espírito do teste que prova que o teste de concorrência testa: uma afirmação sobre
**ausência** só vale se algo falhar quando a ausência acabar.

---

## R8. Como a recusa é modelada sem virar erro

**Decision**: o serviço devolve um resultado, não levanta exceção, quando o cartão é recusado.

```
PagamentoRecusado  → não é exceção; é retorno com motivo
ReservaVencida     → exceção (estado inválido)
ReservaJaPaga      → exceção (estado inválido, mas resposta amigável)
SessaoIndisponivel → exceção (estado inválido)
```

**Rationale**: a distinção não é estilística. Uma recusa de cartão é **desfecho normal do negócio**
com registro obrigatório (FR-012); um estado inválido é ausência de operação. Modelar as duas como
exceção dentro de `transaction.atomic()` desfaz o registro da recusa junto com o rollback — e o
projeto perde exatamente a evidência de que o caminho de recusa existe, que a constitution trata
como não-opcional.

**Consequência prática**: a recusa responde `402 Payment Required`, não `400` nem `409`. É a
resposta que diz "sua requisição estava certa, a cobrança é que não passou", e é o que permite ao
front distinguir "corrija o formulário" de "troque de cartão" sem interpretar texto.

---

## R9. A regra determinística do cartão

**Decision**: o desfecho é decidido pelo **número**, por tabela fixa. Validade e código de
segurança são validados quanto à forma e **não** participam da decisão.

| Número | Desfecho | Mensagem |
|---|---|---|
| `4242 4242 4242 4242` | aprovado | — |
| `4000 0000 0000 9995` | recusado | Saldo insuficiente |
| `4000 0000 0000 0069` | recusado | Cartão expirado |
| `4000 0000 0000 0002` | recusado | Recusado pelo emissor |
| qualquer outro bem formado | aprovado | — |

"Bem formado" = 16 dígitos com dígito verificador de Luhn válido. Número mal formado é **erro de
preenchimento** (`400`), não recusa (`402`) — são coisas diferentes para quem está comprando, e
FR-010 exige que sejam distinguíveis.

**Rationale**: a constitution exige que os dois caminhos sejam exercitáveis pelo avaliador. Sorteio
não é exercitável nem testável — um caminho de recusa que aparece 1 vez em 5 é um caminho que o
avaliador pode não ver, e um teste que depende de sorte é um teste que falha sozinho.

Os números são os de ambiente de teste que qualquer pessoa que já integrou pagamento reconhece.
Reconhecimento importa: o avaliador que digitar `4242…` por reflexo acerta o caminho feliz sem
consultar nada.

**A tabela é contrato com o README** (FR-007). Mudar um número sem mudar o README quebra a única
forma que o avaliador tem de alcançar a recusa. Deve haver teste que percorra os três números de
recusa e afirme três mensagens **distintas** — assim a tabela não pode ser silenciosamente
reduzida a um caminho só.

**Alternatives considered**:

- **Recusa por valor da compra** (acima de X recusa) — acopla o caminho de recusa ao preço da
  sessão semeada; mudar o seed mudaria o comportamento do pagamento.
- **Botão "simular recusa"** — exercitável, mas não seria uma simulação de cobrança: qualquer
  pessoa vê que é um interruptor, e o caminho de recusa deixaria de parecer parte do produto.
- **Sorteio com semente fixa em teste** — teste determinístico, demonstração não. O avaliador
  continuaria sem conseguir provocar a recusa de propósito.

---

## R10. O que é guardado do cartão

**Decision**: **os quatro últimos dígitos e a bandeira**. Nada mais. Nunca o número completo, nunca
o código de segurança, nem em log, nem em campo de auditoria.

**Rationale**: FR-011. Não há cobrança real, então guardar o número não tem nem a desculpa de
recobrança — seria risco puro sem contrapartida. Os quatro últimos existem porque a confirmação
precisa dizer com o que foi pago sem que a pessoa releia o cartão.

**O que isso obriga**: o número não pode aparecer em exceção não tratada, e o serializer de entrada
não pode ser ecoado na resposta de erro. Deve haver teste que provoque erro de validação e afirme
que o número **não** está no corpo da resposta.

---

## R11. A imagem do QR

**Decision**: gerada no **back-end** como **SVG**, entregue como `data:` URI dentro do JSON do
ingresso, exibida em `<img>`. Dependência nova: `qrcode` (Python, pura, sem Pillow).

**Rationale**: o conteúdo assinado é a fonte da verdade e a imagem é uma representação dele — quem
gera a verdade gera a representação. SVG porque o ingresso precisa continuar legível em tela
estreita, e vetor não pixeliza.

`data:` URI em `<img>` em vez de SVG injetado no DOM: evita `dangerouslySetInnerHTML` inteiramente
e dá `alt` de graça, que é o que a leitura por tecnologia assistiva precisa.

**Por que não gerar no front-end**: exigiria uma biblioteca de codificação QR no navegador e
transformaria a integridade da imagem em responsabilidade de código que roda no cliente. O código
assinado já viaja em texto de qualquer forma (FR-038), então o front não ganha nada em recodificá-lo.

**Por que uma dependência nova é aceitável aqui** — a 007 fechou com "nenhuma dependência nova":
codificação QR é um algoritmo padronizado com casos de borda (níveis de correção, seleção de
versão, máscara). Escrever à mão seria a única parte do projeto onde reimplementar um padrão
publicado seria defensável, e não é. `qrcode` gerando SVG não arrasta Pillow nem binário.

**Alternatives considered**:

- **`qrcode[pil]` gerando PNG** — arrasta Pillow e uma cadeia de bibliotecas de imagem para gerar
  quadrados pretos. SVG não precisa de nenhuma.
- **Endpoint próprio `GET /ingressos/<uuid>/qr.svg`** — mais limpo em tese, mas exige mais um
  proxy no Next para carregar o cookie de sessão, e uma requisição por ingresso. Para no máximo 6
  ingressos, o `data:` URI numa resposta só é mais simples e não pisca ao carregar.

---

## R12. Onde os modelos moram

**Decision**: `Payment` e `Ticket` em **`apps/screening`**, junto de `Reservation` e `ReservedSeat`.

**Rationale**: a `Ticket` aponta para `ReservedSeat` e **carrega uma constraint** sobre ela. A
unicidade que garante o Princípio II fica na mesma app do modelo que ela protege, e a migração que
cria as duas coisas é uma só — que é o que o princípio exige.

A 001 estabeleceu a separação por domínio: `catalog` cuida de filme e TMDb, `screening` cuida de
sala, horário e venda. Pagamento e ingresso são a continuação da venda, não um domínio novo.

**Alternatives considered**: uma app `billing` ou `ticketing`. Separaria bem no papel, e criaria
chave estrangeira e constraint atravessando fronteira de app para nada — duas migrações
interdependentes onde uma basta. Se a feature de portaria crescer a ponto de justificar, a extração
é refatoração posterior, com os modelos já estáveis.

---

## R13. Uma rota, quatro estados

**Decision**: **`/pagamento/[id]`** faz tudo, e o que ela mostra depende do estado da reserva.

| Estado da reserva | O que a rota mostra |
|---|---|
| viva, não paga | revisão da compra + formulário de cartão |
| **paga** | os ingressos com QR |
| vencida | explicação e caminho de volta ao mapa |
| de outro cliente, ou inexistente | não encontrada |

**Rationale**: o endereço já existe — `ReservationPanel.tsx` da 007 já aponta para
`/pagamento/${reserva.id}`. Honrá-lo evita mexer em código da 007 sem necessidade.

Uma rota só resolve de graça três coisas que rotas separadas resolveriam com redirecionamento:
recarregar depois de pagar mostra os ingressos (FR-022, US1-6); voltar ao pagamento de uma reserva
já paga leva aos ingressos em vez de a um formulário inútil (US3-4); e a confirmação tem endereço
estável, que é a suposição registrada na spec.

**Por que não `/ingressos/...`**: aquele espaço pertence à área "Meus ingressos" da feature
seguinte. Ocupá-lo agora obrigaria a próxima feature a mudar de endereço ou a conviver com um
significado herdado.

---

## R14. Estratégia de testes

| Alvo | Tipo | Por quê |
|---|---|---|
| **Dois pagamentos simultâneos da mesma reserva → um conjunto** | back-end, threads reais | **Prova do Princípio II** — obrigatória |
| **Sem a constraint, o teste acima falha** | back-end | Prova que o teste testa |
| Pagamentos de reservas diferentes não se serializam | back-end, threads reais | O bloqueio é por reserva, não por sessão (R4) |
| **Código adulterado é rejeitado** | back-end | **Prova do Princípio III**, FR-035 |
| **Código assinado com outro segredo é rejeitado** | back-end | **Prova do Princípio III**, FR-036 |
| **Verificação não consulta o banco** (`num_queries == 0`) | back-end | FR-034 — a ausência precisa de teste (R7) |
| **Reserva paga não volta ao estoque no vencimento** | back-end | **R3** — a armadilha da 007 |
| **Reserva paga não tem a ocupação apagada por outra reserva** | back-end | **R3**, o caminho que nenhuma constraint pega |
| Reserva vencida não pode ser paga | back-end | FR-023 |
| Reserva já paga não emite segundo conjunto | back-end | FR-022 |
| Reserva cancelada e sessão não vendável recusam | back-end | FR-024, FR-025 |
| Os três cartões de recusa dão três mensagens distintas | back-end | FR-008, FR-009, SC-006 |
| Cartão mal formado dá `400`, não `402` | back-end | FR-010 |
| Recusa não altera o vencimento da reserva | back-end | FR-027 |
| Organizador e portaria recebem `403` | back-end | Gate do Princípio IV |
| Cliente não paga nem vê reserva/ingresso de outro | back-end | FR-040, FR-043 |
| Resposta de erro não ecoa o número do cartão | back-end | FR-011, R10 |
| Um ingresso por assento, N lugares → N ingressos | back-end | FR-014 |
| Códigos de dois ingressos são distintos | back-end | FR-037 |
| Estados da tela em pt-BR, sem texto genérico | front-end | FR-045, FR-046 |
| Formulário operável só por teclado, resultado anunciado | front-end | FR-047 |
| Nenhum valor fora dos tokens | front-end | FR-051 |
| Percurso mapa → reserva → pagamento → ingresso | e2e | Princípio I |

**Rationale**: as quatro primeiras linhas e as duas de R3 são obrigatórias pela constitution, não
diferenciais. As duas de R3 merecem destaque porque protegem contra a única falha desta feature que
**nenhuma constraint pega** — apagar a ocupação de uma reserva paga é uma operação perfeitamente
legal para o banco.
