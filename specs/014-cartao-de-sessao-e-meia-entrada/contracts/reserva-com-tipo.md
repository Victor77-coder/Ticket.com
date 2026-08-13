# Contrato: Reserva, Pagamento e Ingresso com Tipo

**Feature**: 014 | **Date**: 2026-08-13

> **Todo campo desta feature é ADITIVO.** Nenhum campo existente muda de nome, de tipo ou de
> significado. Um cliente escrito contra a 007/008 continua funcionando sem edição, e é isso que
> mantém `reserva.spec.ts` e `pagamento.spec.ts` válidos sem afrouxamento.

---

## `POST /api/v1/reservas/`

**Papel exigido**: cliente. Organizador e portaria recebem `403` — inalterado.

### Corpo

```json
{
  "sessao": 366,
  "assentos": [561, 562],
  "meias": [562],
  "chave_idempotencia": "e4f0…"
}
```

| Campo | Obrigatório | Significado |
|---|---|---|
| `sessao` | sim | **inalterado** |
| `assentos` | sim | **inalterado** — ids dos lugares |
| `meias` | **não** | **NOVO** — subconjunto de `assentos` que sai como meia |
| `chave_idempotencia` | sim | **inalterado** |

### Regras de `meias`

1. **Ausente, `null` ou `[]` → todos os lugares são inteira.** É o comportamento de antes desta
   feature, e é o padrão seguro do FR-016.
2. **Todo id em `meias` DEVE constar em `assentos`.** Id fora da lista → `400`, com mensagem em
   português. Nunca ignorado em silêncio: ignorar faria a tela e o servidor discordarem sobre o que
   foi comprado.
3. **Ids repetidos em `meias` não multiplicam nada** — o conjunto é o que importa.
4. **`meias` igual a `assentos` é válido.** Não há cota (ver Assumptions da spec).

### Resposta `201`

```json
{
  "id": 90,
  "sessao": 366,
  "assentos": [
    { "fileira": "A", "numero": 1, "tipo": "inteira", "valor": "32.00" },
    { "fileira": "A", "numero": 2, "tipo": "meia",    "valor": "16.00" }
  ],
  "total": "48.00",
  "expira_em": "2026-08-13T16:40:00-03:00",
  "situacao": "ativa"
}
```

**`tipo` e `valor` são novos dentro de cada item de `assentos`.** `fileira` e `numero` continuam
exatamente como estavam — um consumidor que só lê esses dois não percebe a mudança.

`total` continua string decimal com duas casas, e continua **calculado pelo servidor**. Passa a ser
a soma dos `valor`, e não mais preço × quantidade.

### Erros

Os mesmos da 007, mais um:

| Situação | Status | Mensagem |
|---|---|---|
| `meias` com id fora de `assentos` | `400` | "Não foi possível registrar esta reserva. Tente escolher os lugares de novo." |

Os demais — sessão indisponível, seleção inválida, lugar ocupado, limite excedido — **inalterados**.

---

## `GET /api/v1/reservas/<id>/`

Mesma forma da resposta acima. `tipo` e `valor` por lugar; `total` somado.

---

## `POST /api/v1/reservas/<id>/pagamento/`

**Corpo inalterado.** O tipo já está gravado na reserva; enviá-lo de novo no pagamento seria dar ao
cliente uma segunda chance de decidir o preço, que é exatamente o que o FR-019 proíbe.

### Resposta `201` (aprovado)

```json
{
  "pagamento": { "situacao": "aprovado", "total": "48.00", "cartao_final": "4242" },
  "ingressos": [
    { "codigo": "…", "qr_svg": "…", "assento": { "fileira": "A", "numero": 1 }, "tipo": "inteira" },
    { "codigo": "…", "qr_svg": "…", "assento": { "fileira": "A", "numero": 2 }, "tipo": "meia" }
  ]
}
```

`tipo` é **novo** em cada ingresso. Todo o resto — `codigo`, `qr_svg`, `filme`, `sessao`, `sala`,
`assento` — inalterado.

**O `codigo` não muda de forma.** Ele continua sendo assinatura sobre `public_id` + sessão (R7). Um
ingresso de meia e um de inteira produzem códigos indistinguíveis, e isso é correto: o tipo não é
credencial.

### Recusa

**Inalterada**, inclusive no valor: uma recusa não cobra nada e não altera a reserva. O total da
tentativa recusada é o mesmo total somado.

---

## `GET /api/v1/meus-ingressos/`

Cada item ganha `tipo`. Agrupamento, ordenação e a separação entre próximas e passadas —
**inalterados**.

---

## `GET /api/v1/ingressos-compartilhados/<token>/`

Ganha `tipo`, **e só isso**.

> **`test_share_link_leakage.py` precisa ser atualizado deliberadamente.** Ele inspeciona a resposta
> pública inteira por valor e reprova campo novo. O tipo é permitido por decisão registrada
> (FR-023): ele é informação do ingresso, não do comprador — quem recebe o link já vai entrar com
> ele e vai apresentar o mesmo documento na porta.
>
> A atualização DEVE ser a inclusão do tipo na lista de permitidos, **com a razão escrita no
> próprio teste**. Afrouxar a inspeção para deixar de olhar campos novos destruiria a garantia.

**Continuam proibidos**, e o teste continua provando: quem comprou, os outros ingressos da mesma
compra, valor pago, dado de pagamento e o estado de uso.

---

## `POST /api/v1/portaria/validar/`

**Contrato de entrada inalterado.** A resposta ganha `tipo` dentro do bloco de informação do
ingresso.

> **A fronteira que não pode ser cruzada (FR-024)**: `desfecho` continua tendo **exatamente quatro
> valores** — `valido`, `ja_utilizado`, `sessao_errada`, `nao_reconhecido`. O tipo é exibido ao
> operador para conferência de documento e **nunca** entra na decisão. Não existe
> `desfecho: "meia_sem_documento"`, e o campo `tipo` não pode ser lido por nenhum `if` que decida o
> desfecho.
>
> A constitution exige quatro desfechos distinguíveis. Um quinto seria emenda a ela, não feature.
