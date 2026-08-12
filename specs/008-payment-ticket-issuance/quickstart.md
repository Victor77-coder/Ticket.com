# Quickstart — Pagamento Simulado e Emissão do Ingresso

**Feature**: `008-payment-ticket-issuance` | **Date**: 2026-08-11

Percorrer o pagamento e o ingresso, **provocar as três recusas de propósito**, **tentar forjar um
QR** e reproduzir a corrida à mão. Pressupõe o ambiente já de pé; ver o
[README](../../README.md) para o setup completo.

---

## Pré-requisitos

Esta feature **introduz variável de ambiente nova e migração**. Nenhuma das duas é opcional.

### 1. A chave de assinatura

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

Colar em `.env`:

```
TICKET_SIGNING_KEY=<o valor gerado>
```

**Precisa ser diferente da `DJANGO_SECRET_KEY`** (FR-031). Igualar as duas faz um vazamento virar
dois: a chave da aplicação compromete sessões, a do ingresso compromete a catraca.

Sem a variável, o back-end **não sobe** — é intencional. Um valor padrão em código viraria o
segredo real de todo mundo que não leu o README, e o QR passaria a ser forjável por quem leu o
repositório.

### 2. Subir e migrar

```bash
docker compose up -d
docker compose exec backend python manage.py migrate
```

A migração cria `Payment`, `Ticket`, as duas constraints e o estado `paid` — **os cinco juntos**.

### 3. Conferir que as duas constraints existem

Antes de qualquer outra coisa. São elas que a feature existe para criar:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\d screening_payment"
docker compose exec db psql -U ingressos -d ingressos -c "\d screening_ticket"
```

**Esperado**:

| Tabela | Índice | Forma |
|---|---|---|
| `screening_payment` | `um_pagamento_aprovado_por_reserva` | `UNIQUE (reservation_id) WHERE status = 'approved'` |
| `screening_ticket` | unicidade de `reserved_seat_id` | `UNIQUE (reserved_seat_id)` — **sem `WHERE`** |

A primeira **tem** predicado, a segunda **não pode ter**. Se estiver invertido, é a versão errada
(R1).

---

## Contas e cartões

Senha **`desafio2026`** em todas as contas:

| Papel | Usuário | Nesta feature |
|---|---|---|
| Cliente | `cliente1` | paga |
| Cliente | `cliente2` | o outro lado da corrida, e o acesso cruzado |
| Organizador | `organizador` | **deve receber 403** |
| Portaria | `portaria` | **deve receber 403** |

Cartões — validade qualquer no futuro, CVV qualquer com 3 dígitos:

| Número | Desfecho |
|---|---|
| `4242 4242 4242 4242` | **aprovado** |
| `4000 0000 0000 9995` | recusado — saldo insuficiente |
| `4000 0000 0000 0069` | recusado — cartão expirado |
| `4000 0000 0000 0002` | recusado — recusado pelo emissor |

Qualquer outro número bem formado é aprovado.

---

## 1. Chegar ao pagamento

1. Entrar como `cliente1`, abrir um filme, escolher uma sessão.
2. Selecionar **três** lugares e confirmar a reserva.
3. Acionar **Continuar para pagamento**.

**Esperado**: a revisão com filme, sessão, sala, os três lugares, valor unitário, total e o prazo
correndo (FR-002).

**SC-001**: uma interação da confirmação da reserva até o pagamento. Duas, e o critério falhou.

Três lugares, não um: é o que torna visível o "um ingresso **por assento**" no passo 3. Com um
lugar só, a diferença entre um ingresso por reserva e um por assento não aparece.

## 2. As três recusas

**Este passo é obrigatório na avaliação, não opcional.** A constitution diz que o caminho de recusa
tem de ser exercitável — é aqui que ele é exercido.

Para cada um dos três cartões de recusa:

1. preencher e confirmar;
2. **esperado**: mensagem em português, própria daquele motivo, dizendo o que houve e a próxima
   ação;
3. **conferir que o prazo não mudou** — a contagem regressiva continua de onde estava, não
   reinicia (FR-027).

As três mensagens têm de ser **diferentes** (FR-008, SC-006). Se duas forem iguais, a tabela foi
silenciosamente reduzida a um caminho só.

Recarregar o mapa da sessão em outra janela: **os três lugares continuam tomados** (FR-026,
SC-007). A recusa não devolve o assento — a leitura registrada em
[spec.md](./spec.md#leitura-do-princípio-ii-sobre-a-recusa) depende disso ser verdade.

### Erro de preenchimento é outra coisa

Digitar `1234`, um número curto e sem dígito verificador válido.

**Esperado**: aviso de preenchimento (`400`), **não** uma recusa (`402`). São coisas diferentes:
numa a pessoa corrige o que digitou, na outra troca de cartão (FR-010).

E conferir, nas ferramentas do navegador, que o número digitado **não** volta no corpo da resposta
(FR-011).

## 3. Pagar e receber os ingressos

Agora com `4242 4242 4242 4242`.

**Esperado**: **três** ingressos, um por lugar, cada um com:

- código em QR próprio e visivelmente diferente dos outros;
- o **código em texto**, junto da imagem (FR-038 — é o que a portaria vai digitar quando a câmera
  falhar);
- filme, sessão, sala e o lugar daquele ingresso.

**Recarregar a página.** Os mesmos três ingressos, sem emitir novos (US1-6, FR-022). Se a
confirmação sumir ao recarregar, a suposição de "endereço próprio" da spec falhou.

**Voltar ao mesmo endereço depois**: continua mostrando os ingressos, nunca um formulário de
pagamento (R13, US3-4).

## 4. O lugar vendido não volta ao estoque

**O passo mais importante desta caminhada.** É a armadilha que a 007 deixou (R3), e ela só aparece
depois do vencimento.

Forçar o vencimento da reserva **paga**:

```bash
docker compose exec backend python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from apps.screening.models import Reservation
r = Reservation.objects.filter(status='paid').latest('created_at')
r.expires_at = timezone.now() - timedelta(minutes=1); r.save()
print('vencida no relogio:', r.id, r.status)
"
```

Recarregar o mapa da sessão.

**Esperado**: os três lugares continuam **tomados**. Uma reserva paga não devolve assento —
`expires_at` no passado não significa nada quando a reserva foi paga.

**Se aparecerem livres, a feature está vendendo o mesmo lugar duas vezes.** Continuar a verificação:

```bash
# como cliente2, tentar reservar um dos lugares vendidos
curl -s -b /tmp/c2.txt -X POST http://localhost:5003/api/reservar \
  -H 'Content-Type: application/json' \
  -d "{\"sessao\":$SESSAO,\"assentos\":[$ASSENTO_VENDIDO],\"chave_idempotencia\":\"$(uuidgen)\"}"
```

**Esperado**: `409`. E a prova que não depende da resposta HTTP — a ocupação paga **continua no
banco**:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT rs.id, rs.seat_id, r.status
     FROM screening_reservedseat rs JOIN screening_reservation r ON r.id = rs.reservation_id
    WHERE r.status = 'paid';"
```

**Esperado**: as linhas continuam lá. Se sumiram, `_liberar_ou_recusar` apagou ocupação paga — e
essa é a falha que **nenhuma constraint pega**, porque apagar antes de inserir é operação legal
para o banco.

## 5. Papéis que não pagam

Entrar como `organizador`, depois como `portaria`, e tentar pagar. E a recusa tem de vir do
**servidor** — botão escondido não conta:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  http://localhost:8000/api/v1/reservas/77/pagamento/ \
  -H 'Content-Type: application/json' \
  -b "sessionid=<sessão do organizador>" \
  -d '{"numero":"4242424242424242","nome":"TESTE","validade":"12/2030","cvv":"123"}'
```

**Esperado**: `403`. Um `201` aqui é violação de FR-042, com a interface impecável ou não.

Como `cliente2`, tentar pagar a reserva de `cliente1`: **esperado `404`**, não `403` — um `403`
confirmaria que a reserva existe (FR-040, FR-043).

## 6. Reserva vencida não paga

Criar uma reserva nova com `cliente1`, forçar o vencimento **sem** pagar, e então tentar pagar.

**Esperado**: `409` com `situacao: "expirada"` e a frase que manda escolher de novo. **Nenhum
ingresso emitido** (FR-023).

E a decisão é do **servidor**: a contagem na tela é informativa (FR-029). Para provar, chamar o
`curl` do passo 5 com a sessão do `cliente1` — sem front-end nenhum no caminho, a recusa continua.

---

## Tentar forjar um QR

O ponto alto do Princípio III. Pegar o `codigo` de um ingresso emitido (visível na resposta do
pagamento ou na tela).

### Adulterar um caractere

```bash
docker compose exec backend python manage.py shell -c "
from apps.screening.services import ingressos
codigo = '<cole aqui o codigo do ingresso>'
adulterado = codigo[:-1] + ('A' if codigo[-1] != 'A' else 'B')
try:
    print('ACEITOU:', ingressos.verificar_codigo(adulterado))
except ingressos.CodigoInvalido:
    print('rejeitado — correto')
"
```

**Esperado**: `rejeitado`. Um `ACEITOU` aqui é o Princípio III quebrado (FR-035).

### Assinar com outro segredo

Alguém que conheça o formato mas não a chave:

```bash
docker compose exec backend python manage.py shell -c "
from django.core import signing
from apps.screening.services import ingressos
forjado = signing.dumps({'t': '00000000-0000-4000-8000-000000000000', 's': 1},
                        key='chave-do-atacante', salt='ingresso.qr')
try:
    print('ACEITOU:', ingressos.verificar_codigo(forjado))
except ingressos.CodigoInvalido:
    print('rejeitado — correto')
"
```

**Esperado**: `rejeitado` (FR-036). O conteúdo é perfeitamente bem formado — só a assinatura não
confere, e é só isso que importa.

### A verificação acontece antes do banco

Não dá para ver a olho; é o teste que prova:

```bash
docker compose exec backend pytest tests/test_ticket_signature.py -k num_queries -v
```

O teste envolve a verificação de um código adulterado em `django_assert_num_queries(0)`. Se alguém
acrescentar uma consulta — nem que seja um `.exists()` de conveniência —, ele quebra e diz por quê
(FR-034, R7).

---

## Reproduzir a corrida à mão

Dois pagamentos da **mesma** reserva, ao mesmo tempo. Guardar o cookie do `cliente1` e criar uma
reserva nova:

```bash
curl -s -c /tmp/c1.txt -X POST http://localhost:5003/api/entrar \
  -H 'Content-Type: application/json' -d '{"username":"cliente1","password":"desafio2026"}'
```

Com o `id` da reserva em mãos, disparar as duas ao mesmo tempo — o `&` é o que importa:

```bash
RESERVA=77
CARTAO='{"numero":"4242424242424242","nome":"MARIA","validade":"12/2030","cvv":"123"}'

curl -s -o /tmp/p1.json -w 'a %{http_code}\n' -b /tmp/c1.txt \
  -X POST http://localhost:5003/api/pagar -H 'Content-Type: application/json' \
  -d "{\"reserva\":$RESERVA,${CARTAO:1}" &

curl -s -o /tmp/p2.json -w 'b %{http_code}\n' -b /tmp/c1.txt \
  -X POST http://localhost:5003/api/pagar -H 'Content-Type: application/json' \
  -d "{\"reserva\":$RESERVA,${CARTAO:1}" &

wait
```

**Esperado**: um `201` e um `409` com `situacao: "paga"`. Nunca dois `201`.

E as duas provas que não dependem da resposta HTTP:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT reservation_id, count(*) FROM screening_payment
    WHERE status = 'approved' GROUP BY 1 HAVING count(*) > 1;"

docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT reserved_seat_id, count(*) FROM screening_ticket
    GROUP BY 1 HAVING count(*) > 1;"
```

**Esperado**: `(0 rows)` nas duas. Qualquer linha é o Princípio II quebrado — e não deveria ser
possível, porque as constraints recusariam a inserção antes.

E a terceira, que pega o estado que o Princípio II proíbe pelo nome:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT r.id FROM screening_reservation r
    WHERE r.status = 'paid'
      AND NOT EXISTS (SELECT 1 FROM screening_ticket t
                        JOIN screening_reservedseat rs ON rs.id = t.reserved_seat_id
                       WHERE rs.reservation_id = r.id);"
```

**Esperado**: `(0 rows)`. Uma reserva paga sem ingresso é exatamente o "estado intermediário
durável em que o assento está preso sem dono" — e é por isso que aprovação e emissão são a mesma
feature.

> Dois `curl` do host não garantem colisão real: há *jitter* de milissegundos e um pode terminar
> antes do outro começar. Se o segundo der `409` com `situacao: "paga"` **sem** ter havido corrida,
> o resultado é o mesmo mas a prova não. **A prova formal é o teste automatizado**, com barreira
> sincronizando as duas threads no ponto crítico.

---

## Testes

```bash
docker compose exec backend pytest tests/test_payment_api.py tests/test_paid_seat_retention.py
docker compose exec backend pytest tests/test_ticket_signature.py
docker compose exec backend pytest tests/test_payment_concurrency.py
docker compose exec frontend npm run test
```

### Linha de base — antes da feature 008

Contra estes números SC-015 é verificado no fim: nenhuma asserção das features 001–007 pode mudar
nem falhar.

| Suíte | Asserções |
|---|---|
| Back-end (`pytest`) | **202 passed** |
| Front-end (`vitest`) | **116 passed** em 7 arquivos |

> O `vitest` também acusa **1 unhandled error** pré-existente — `el.scrollBy is not a function` em
> `components/rows/MovieRow.tsx:59`, porque o jsdom não implementa `scrollBy`. Vem da `004`, foi
> registrado na `007`, e continua não sendo desta feature.

### Contagem final — com a 008 fechada

| Suíte | Antes | Depois | Diferença |
|---|---|---|---|
| Back-end (`pytest`) | 202 passed | **288 passed** | +86, nenhuma falha |
| Front-end (`vitest`) | 116 passed em 7 arquivos | **137 passed** em 9 arquivos | +21, nenhuma falha |
| Ponta a ponta (`playwright`) | 28 passed | **32 passed** | +4 |

Nenhuma asserção das features 001–007 mudou de texto nem de resultado (SC-015, FR-049, FR-050).
O `unhandled error` do `scrollBy` continua exatamente um, e continua vindo da `004`.

Os 86 do back-end: 40 em `test_payment_api`, 29 em `test_ticket_signature`, 9 em
`test_payment_concurrency`, 7 em `test_paid_seat_retention`, 1 em `test_seed_demo`.

> **Rode o e2e com `--workers=2`.** Com o número padrão de workers, o servidor de desenvolvimento
> do Next satura e alguns testes das features anteriores caem por timeout — verificado que passam
> sozinhos e que a falha some ao limitar a concorrência. É característica do ambiente de
> desenvolvimento, não do produto.
>
> ```bash
> cd frontend && npx playwright test --workers=2
> ```

### Provar que o teste de concorrência testa alguma coisa

Herdado da 007, e obrigatório pela mesma razão: um teste de concorrência verde é fácil de conseguir
sem provar nada (R4).

1. comentar a `UniqueConstraint` `um_pagamento_aprovado_por_reserva` em `models.py`
2. gerar e aplicar a migração
3. rodar `tests/test_payment_concurrency.py`

**Esperado: FALHA.** Se passar, o teste está provando que o `SELECT FOR UPDATE` funciona, não que a
garantia é do banco — e as duas threads provavelmente estão compartilhando a conexão da transação
de teste.

Repetir com a unicidade de `Ticket.reserved_seat` trocada por `ForeignKey`: **também precisa
falhar**. A troca não muda uma linha de lógica visível, e é a forma mais fácil de remover a
garantia sem perceber.

Desfazer a alteração e a migração depois.

### Resultado medido — 2026-08-12

Executado durante a implementação, uma garantia de cada vez.

**Sem `um_pagamento_aprovado_por_reserva`** (índice parcial removido, migração aplicada):

```
2 failed, 7 passed
```

| Teste | Sem a constraint |
|---|---|
| `as_duas_garantias_existem_no_banco_com_esta_forma` | **FALHOU** |
| `insercao_direta_de_segundo_aprovado_e_recusada_pelo_banco` | **FALHOU** — o banco aceitou dois aprovados |
| `dois_pagamentos_simultaneos_da_mesma_reserva_um_so_vence` | passou |

**Com `Ticket.reserved_seat` trocado para `ForeignKey`:**

```
2 failed, 7 passed
```

| Teste | Sem a garantia |
|---|---|
| `as_duas_garantias_existem_no_banco_com_esta_forma` | **FALHOU** |
| `dois_ingressos_no_mesmo_assento_sao_recusados_pelo_banco` | **FALHOU** — o banco aceitou |

### O achado que merece registro: a corrida sobrevive sem a constraint, e isso é honesto

**`dois_pagamentos_simultaneos_da_mesma_reserva_um_so_vence` PASSOU com a constraint removida.**
Na 007 o teste equivalente falhava, e a diferença não é defeito — é estrutural, e o plano já a
previa em R2:

> lá, um assento nunca ocupado não tinha linha para o `SELECT FOR UPDATE` travar, e a constraint
> era o único árbitro. Aqui a linha da reserva **sempre existe**, então o bloqueio serializa de
> verdade.

Duas transações pagando a mesma reserva disputam uma linha que já está no banco. A primeira trava,
a segunda espera, e quando prossegue encontra a reserva já paga na revalidação. O bloqueio resolve
sozinho — **neste caminho**.

Então o que a constraint prova, e por que ela não é decorativa: a constitution exige a garantia
**no banco**, não na aplicação. Quem verifica exatamente isso é
`insercao_direta_de_segundo_aprovado_e_recusada_pelo_banco`, que escreve sem passar pelo serviço,
sem bloqueio e sem aplicação — e **falha** sem a constraint. É a diferença entre "a aplicação
evita" e "o banco impede".

**A conclusão prática**: o critério de "o teste precisa falhar" continua satisfeito ao nível do
arquivo, mas quem carrega a prova do Princípio II aqui é a inserção direta, não a corrida por
threads. Registrar isso é mais útil do que forçar a corrida a falhar com um cenário artificial —
que provaria menos, não mais.

---

## Problemas comuns

**O back-end não sobe: `ImproperlyConfigured: TICKET_SIGNING_KEY`** — é o comportamento correto. A
chave não tem padrão utilizável de propósito. Gerar e pôr no `.env`.

**Todos os cartões aprovam, inclusive os de recusa** — o número está chegando com espaços e a
comparação é literal. Normalizar antes de consultar a tabela.

**A recusa chega como `400`** — provavelmente a recusa está sendo levantada como erro de validação.
Recusa é `402` e é **retorno**, não exceção; como exceção dentro de `atomic()` ela ainda desfaz o
registro do próprio `Payment` recusado (R8).

**O lugar vendido volta a aparecer livre depois de 10 minutos** — a regra de ocupação não ganhou o
segundo termo, ou ganhou em duas das três cópias. Ver R3: o predicado tem de existir num lugar só e
ser consumido pelos três.

**`IntegrityError` chegando como 500** — a violação de unicidade é resultado **esperado** e vira
`409` com `situacao: "paga"` (R1, e R3 da 007). Como `500` ela vira erro genérico, o que também
quebra FR-046.

**O QR não aparece, mas o código em texto sim** — provável `data:` URI malformado. O código em
texto continuar visível é o comportamento correto de degradação (FR-038): é ele que a portaria
digita.

**O teste de concorrência passa em qualquer configuração** — falta `transaction=True`; as threads
estão na mesma transação e na mesma conexão. Ver R4 e o R4 da 007.
