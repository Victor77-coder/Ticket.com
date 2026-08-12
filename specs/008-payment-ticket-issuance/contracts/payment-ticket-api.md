# Contract — Payment & Ticket API

**Feature**: `008-payment-ticket-issuance` | **Date**: 2026-08-11

Um endpoint novo no Django, um proxy novo no Next, e uma ampliação do `GET` de reserva que a 007
já entregou. O padrão da `002`, `003` e `007` continua: o navegador nunca fala com o Django direto
quando há cookie de sessão envolvido.

```
navegador ──GET  (página)────────────> Next  /pagamento/[id]  (fetch no servidor, com cookie)
                                         └──> Django  GET  /api/v1/reservas/<id>/

navegador ──POST + cookie────────────> Next  /api/pagar
                                         └──> Django  POST /api/v1/reservas/<id>/pagamento/
```

---

# Django

## `POST /api/v1/reservas/<id>/pagamento/`

**Autenticação**: cookie de sessão repassado pelo Next. **Papel exigido: cliente** (FR-039).
**Só o dono da reserva** (FR-040).

### Requisição

```json
{
  "numero": "4242424242424242",
  "nome": "MARIA DE SOUZA",
  "validade": "12/2030",
  "cvv": "123"
}
```

Não há `valor` na requisição. **O total é calculado pelo servidor** a partir do preço da sessão e
da quantidade de lugares (FR-003) — valor vindo do cliente não é aceito em nenhuma forma, nem para
conferência.

Não há `chave_idempotencia`. A idempotência aqui não vem de chave: vem de a reserva só poder ter
**um** pagamento aprovado, garantido por constraint (R1). Uma chave seria um segundo mecanismo
resolvendo o que o primeiro já resolve.

### `201 Created` — aprovado, ingressos emitidos

```json
{
  "situacao": "paga",
  "pagamento": {
    "cartao_final": "4242",
    "bandeira": "visa",
    "total": "64.00",
    "pago_em": "2026-08-11T20:34:12-03:00"
  },
  "ingressos": [
    {
      "codigo": "eyJ0IjoiM2Y5YTFlMmMtN2IwNC00YzhkLTlmMjEtNWE2YjhjMGQxZTJmIiwicyI6MTJ9:1uJd3P:AbCdEf...",
      "qr_svg": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0i...",
      "filme": "A Odisseia",
      "sessao": "2026-08-12T19:30:00-03:00",
      "sala": "Sala 1",
      "assento": { "fileira": "A", "numero": 1 }
    },
    {
      "codigo": "eyJ0IjoiOWM4ZDdlNmYtNWE0Yi0zYzJkLTFlMGYtOWE4YjdjNmQ1ZTRmIiwicyI6MTJ9:1uJd3P:XyZ...",
      "qr_svg": "data:image/svg+xml;base64,PHN2ZyB4bWxucz0i...",
      "filme": "A Odisseia",
      "sessao": "2026-08-12T19:30:00-03:00",
      "sala": "Sala 1",
      "assento": { "fileira": "A", "numero": 3 }
    }
  ]
}
```

**Um objeto por assento** (FR-014). Uma reserva de três lugares devolve três ingressos, cada um
com seu `codigo` e seu `qr_svg`.

**`codigo` e `qr_svg` andam juntos de propósito.** O `codigo` é a verdade assinada; o `qr_svg` é
uma representação dele. O texto aparece na tela junto da imagem porque a portaria vai exigir
digitação manual como alternativa sempre disponível — exigência da constitution, cobrada por
FR-038 já nesta feature, para que o código não nasça sem forma legível.

**`qr_svg` é `data:` URI, não markup**: entra num `<img>` com `alt`, sem
`dangerouslySetInnerHTML` (R11).

**O que a resposta não tem**: `id` do pagamento, `id` do ingresso, `id` da ocupação. A identidade
pública do ingresso já está dentro do `codigo` assinado; expor a interna não serve a nada e amplia
a superfície.

### `402 Payment Required` — cartão recusado

```json
{
  "situacao": "recusada",
  "motivo": "saldo_insuficiente",
  "detail": "Não havia saldo suficiente neste cartão. Tente outro cartão.",
  "expira_em": "2026-08-11T20:40:00-03:00"
}
```

**`402`, não `400` e não `409`.** A requisição estava correta; a cobrança é que não passou. É o que
permite ao front distinguir "corrija o formulário" de "troque de cartão" sem interpretar texto
(R8).

Os três motivos, com frase própria cada um (FR-008, FR-009):

| `motivo` | `detail` |
|---|---|
| `saldo_insuficiente` | Não havia saldo suficiente neste cartão. Tente outro cartão. |
| `cartao_expirado` | Este cartão está expirado. Use um cartão com validade em dia. |
| `recusado_pelo_emissor` | O banco emissor recusou a cobrança. Tente outro cartão ou fale com o banco. |

**`expira_em` volta na recusa de propósito**: é a prova, para o front e para quem lê o contrato,
de que **a reserva continua viva com o vencimento original** (FR-026, FR-027). Se este campo
mudasse entre uma tentativa e a seguinte, a recusa estaria mexendo no prazo.

### `400 Bad Request` — preenchimento inválido

```json
{ "detail": "Confira o número do cartão." }
```

Número mal formado, validade fora de forma, código de segurança ausente. **Distinto da recusa**
(FR-010): aqui a pessoa corrige o que digitou; no `402` ela troca de cartão.

**A resposta nunca ecoa o número enviado** (FR-011, R10). Deve haver teste que provoque este erro
e afirme a ausência do número no corpo.

### `401 Unauthorized` — sem sessão ativa

```json
{ "detail": "Entre para concluir o pagamento." }
```

Mesma tradução que a 007 já faz: o DRF converteria "não autenticado" em `403` porque a sessão não
oferece `WWW-Authenticate`, e o front precisa distinguir "conduza à entrada" de "este papel não
compra" (FR-044).

### `403 Forbidden` — papel que não compra

```json
{ "detail": "Apenas clientes podem pagar reservas." }
```

Organizador e portaria. **A recusa é do servidor** (FR-042) — botão escondido não conta, e é o
teste de acesso cruzado que prova a diferença.

### `404 Not Found` — reserva de outro cliente, ou inexistente

```json
{ "detail": "Reserva não encontrada." }
```

**`404`, não `403`**, para reserva alheia: um `403` confirmaria que ela existe. Mesma decisão da
007 (FR-004, FR-043).

### `409 Conflict` — a reserva não pode mais ser paga

```json
{ "situacao": "expirada", "detail": "Esta reserva expirou. Escolha os lugares de novo." }
```

Três casos, cada um com sua frase (FR-045):

| `situacao` | `detail` |
|---|---|
| `expirada` | Esta reserva expirou. Escolha os lugares de novo. |
| `paga` | Esta reserva já foi paga. Seus ingressos estão logo abaixo. |
| `indisponivel` | Esta sessão não está mais disponível. |

**`situacao: "paga"` é o desfecho da corrida perdida** — e também o de quem clicou duas vezes. Vem
de duas origens indistinguíveis para o cliente: a revalidação sob bloqueio encontrou a reserva já
paga, ou a constraint `um_pagamento_aprovado_por_reserva` foi violada na inserção.

**A segunda origem não é erro de sistema** (R1, e R3 da 007) — é a rede pegando o que o bloqueio
deixou passar. Traduzi-la em `500` esconderia o mecanismo que mais importa.

**Nenhum ingresso é emitido em nenhum dos três casos** (FR-023, FR-024, FR-025).

---

## `GET /api/v1/reservas/<id>/` — ampliado

Já existe desde a 007, com o mesmo corpo do `201` da reserva. **Ampliado, não alterado**: os campos
existentes continuam com o mesmo nome e o mesmo significado (FR-050).

Quando a reserva está paga, a resposta ganha `pagamento` e `ingressos`, idênticos aos do `201`
acima:

```json
{
  "id": 77,
  "sessao": 12,
  "assentos": [{ "fileira": "A", "numero": 1 }],
  "total": "32.00",
  "expira_em": "2026-08-11T20:40:00-03:00",
  "situacao": "paga",
  "pagamento": { "cartao_final": "4242", "bandeira": "visa", "total": "32.00", "pago_em": "..." },
  "ingressos": [{ "codigo": "...", "qr_svg": "...", "...": "..." }]
}
```

**É isto que faz a confirmação sobreviver a um recarregamento** (US1-6) e que faz `/pagamento/[id]`
mostrar os ingressos em vez de um formulário inútil quando a reserva já foi paga (R13).

`expira_em` continua presente numa reserva paga, com o valor original e **sem significado de
prazo** — a reserva paga não vence. O front não exibe contagem regressiva quando
`situacao == "paga"`.

---

# Next — `POST /api/pagar`

Repassa o corpo ao Django com o cookie de sessão e devolve status e corpo **sem alterá-los** —
`402` chega ao navegador com a mesma frase em pt-BR. Padrão idêntico a `/api/entrar` (`003`),
`/api/busca` (`002`) e `/api/reservar` (`007`).

O identificador da reserva vai no corpo, porque a rota do Next é fixa:

```json
{ "reserva": 77, "numero": "...", "nome": "...", "validade": "...", "cvv": "..." }
```

**Por que o proxy existe**: o cookie de sessão é `httpOnly` e script na página não o alcança. Sem
o proxy, ou o cookie deixaria de ser `httpOnly` — reabrindo o que a `003` fechou —, ou o Django
teria de aceitar CORS com credencial.

**O proxy não guarda nem registra o corpo.** É o único ponto do sistema por onde o número completo
do cartão passa, e ele passa sem parar (R10).

---

# Campos proibidos nas respostas

Gate do **Princípio IV**. Nenhuma resposta desta feature pode conter:

- **número completo do cartão, código de segurança, validade ou nome impresso** — nem ecoado em
  erro de validação, nem em log
- **a chave de assinatura**, sob qualquer forma, nem derivada dela (FR-031, SC-011)
- identidade de outro cliente, ou qualquer campo de reserva alheia
- `id` interno de ingresso, pagamento ou ocupação
- dado de gestão: custo, ocupação agregada, `status` interno da sessão

Deve existir teste que serialize a resposta completa de um pagamento aprovado e afirme a ausência
de cada item acima.

---

# O que o contrato deliberadamente não tem

| Ausente | Por quê |
|---|---|
| `GET /ingressos/` — a lista | Área "Meus ingressos" é a feature seguinte |
| `POST /ingressos/<codigo>/validar/` | Tela de portaria é a feature seguinte, onde a marcação e a garantia de validação única nascem **juntas** — o mesmo cuidado da 007 |
| Qualquer campo `utilizado` no ingresso | Idem: o estado nasce junto do que o protege |
| Token ou link de compartilhamento | Feature seguinte |
| `DELETE` ou estorno do pagamento | `paga` é terminal nesta feature |
| Webhook, conciliação, provedor externo | A cobrança é simulada (FR-005) |
| `PATCH` da reserva paga | Trocar de lugar depois de pago exigiria liberar, retomar sob bloqueio e reemitir ingresso — regra própria, fora do escopo |
