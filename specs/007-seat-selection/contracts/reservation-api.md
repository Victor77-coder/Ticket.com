# Contract — Seat Map & Reservation API

**Feature**: `007-seat-selection` | **Date**: 2026-08-11

Dois endpoints no Django e um proxy no Next, seguindo o padrão já estabelecido na `002` e na
`003`: o navegador nunca fala com o Django direto quando há cookie de sessão envolvido.

```
navegador ──GET público──────────────> Next (rota de página, fetch no servidor)
                                         └──> Django  GET  /api/v1/sessoes/<id>/mapa/

navegador ──POST + cookie────────────> Next (/api/reservar)
                                         └──> Django  POST /api/v1/reservas/
```

---

# Django

## `GET /api/v1/sessoes/<id>/mapa/`

**Autenticação**: nenhuma. **Público de propósito** (FR-010, R10) — ver onde há lugar não exige
conta, e exigir login para olhar afastaria o visitante antes de ele ter motivo para criar conta.

### `200 OK`

```json
{
  "id": 12,
  "filme": { "titulo": "A Odisseia", "slug": "a-odisseia" },
  "sala": { "nome": "Sala 1" },
  "inicio": "2026-08-12T19:30:00-03:00",
  "preco": "32.00",
  "esgotada": false,
  "limite_por_reserva": 6,
  "fileiras": [
    {
      "letra": "A",
      "assentos": [
        { "id": 101, "numero": 1, "tipo": "comum",        "situacao": "livre" },
        { "id": 102, "numero": 2, "tipo": "comum",        "situacao": "tomado" }
      ]
    },
    {
      "letra": "F",
      "assentos": [
        { "id": 151, "numero": 1, "tipo": "acessibilidade", "situacao": "livre" }
      ]
    }
  ]
}
```

**`situacao` tem dois valores, não quatro**: `livre` e `tomado`. **Selecionado** é estado do
navegador — nunca do servidor, porque a seleção não existe no banco até virar reserva.
**Acessibilidade** é `tipo`, não situação: um lugar de acessibilidade pode estar livre ou tomado
como qualquer outro. Colapsar as quatro coisas num campo só obrigaria o front a desfazer a fusão.

**Agrupamento por fileira no servidor**: o front recebe a sala já organizada. Deixar uma lista
plana forçaria o cliente a reagrupar, e a ordem de leitura do mapa passaria a depender de código
de apresentação.

**`esgotada`** é derivado — todos os lugares comuns tomados. Existe para o front escolher o estado
explicativo (FR-030) sem varrer a lista.

**Ocupação vencida não aparece como `tomado`** (FR-021), sem depender de rotina ter passado.

> **Correção durante a implementação (2026-08-11)**: o rascunho deste contrato trazia
> `sala.capacidade`. Foi retirado ao ser confrontado com o gate do Princípio IV — o
> `ScreeningSerializer` do catálogo já declara "sem custo, sem capacidade" desde a `001`, e abrir
> exceção aqui seria incoerente. Não faz falta: o cliente recebe todos os lugares e conta se
> precisar. `test_mapa_nao_expoe_a_capacidade_da_sala` fixa a ausência.

### `404 Not Found` — sessão inexistente, em rascunho, cancelada ou já iniciada

```json
{ "detail": "Sessão não encontrada." }
```

**Uma resposta só para os quatro casos** (FR-003). Distinguir "não existe" de "está em rascunho"
revelaria a grade interna de programação a quem não deveria vê-la.

---

## `POST /api/v1/reservas/`

**Autenticação**: cookie de sessão repassado pelo Next. **Papel exigido: cliente** (FR-024).

### Requisição

```json
{
  "sessao": 12,
  "assentos": [101, 103],
  "chave_idempotencia": "3f9a1e2c-7b04-4c8d-9f21-5a6b8c0d1e2f"
}
```

`chave_idempotencia` é gerada pelo navegador **uma vez por seleção**, não por clique (R9, FR-023).

### `201 Created`

```json
{
  "id": 77,
  "sessao": 12,
  "assentos": [
    { "fileira": "A", "numero": 1 },
    { "fileira": "A", "numero": 3 }
  ],
  "total": "64.00",
  "expira_em": "2026-08-11T20:40:00-03:00",
  "situacao": "reservada"
}
```

`expira_em` é **instante absoluto**, não "600 segundos restantes": o relógio do navegador pode
estar errado, e a contagem regressiva precisa de um alvo fixo para não derivar (FR-020).

**Envio repetido com a mesma `chave_idempotencia`** devolve **`200 OK`** com a reserva já criada,
não `201` e não erro. O status diferente é o que permite ao front distinguir "criei" de "já era
minha" sem adivinhar.

### `400 Bad Request` — seleção inválida

```json
{ "detail": "Escolha ao menos um lugar." }
```

Também: mais de 6 lugares · assento que não pertence à sala da sessão · assento de
acessibilidade no fluxo comum (FR-009, FR-013, FR-014).

### `401 Unauthorized` — sem sessão ativa

```json
{ "detail": "Entre para reservar." }
```

O front usa isto para conduzir a `/entrar` com retorno ao mapa (FR-026).

### `403 Forbidden` — papel que não compra

```json
{ "detail": "Apenas clientes podem reservar lugares." }
```

Organizador e portaria. **A recusa é do servidor** (FR-025) — esconder o botão não conta, e é o
teste de acesso cruzado que prova a diferença.

### `404 Not Found` — sessão não vendável

```json
{ "detail": "Sessão não encontrada." }
```

Mesma frase do `GET`, mesma razão.

### `409 Conflict` — o lugar acabou de ser tomado

```json
{
  "detail": "O lugar A3 acabou de ser reservado por outra pessoa. Escolha outro.",
  "assentos_indisponiveis": [{ "fileira": "A", "numero": 3 }]
}
```

**É o código que o Princípio II produz.** Vem de duas origens indistinguíveis para o cliente:

1. o `SELECT FOR UPDATE` encontrou ocupação viva;
2. a constraint `UNIQUE(sessão, assento)` foi violada na inserção.

A segunda **não é erro de sistema** (R3) — é a rede pegando o que o bloqueio deixou passar.
Traduzi-la em `500` esconderia justamente o mecanismo que mais importa.

**Nenhum lugar da seleção é reservado** (FR-018, FR-019). A resposta nomeia quais causaram a
recusa, para que a pessoa saiba o que mudar em vez de tentar de novo às cegas.

---

## `GET /api/v1/reservas/<id>/`

**Autenticação**: cookie de sessão. **Só o dono** (FR-027).

`200 OK` — mesmo corpo do `201`, com `situacao` refletindo o vencimento:

```json
{ "situacao": "expirada", "detail": "Esta reserva expirou. Escolha os lugares de novo." }
```

**`404`, não `403`, para reserva de outro cliente**: um `403` confirmaria que a reserva existe.

---

# Next — `POST /api/reservar`

Repassa o corpo ao Django com o cookie de sessão, e devolve status e corpo **sem alterá-los** —
`409` chega ao navegador com a mesma frase em pt-BR. Padrão idêntico ao de `/api/entrar` (`003`)
e `/api/busca` (`002`).

**Por que o proxy existe**: o cookie de sessão é `httpOnly`; script na página não o alcança, então
a chamada precisa sair do servidor Next. Sem o proxy, ou o cookie deixaria de ser `httpOnly` — o
que reabriria exatamente o que a `003` fechou —, ou o Django teria de aceitar CORS com credencial.

---

# Campos proibidos nas respostas

Gate do **Princípio IV**. Nenhuma resposta desta feature pode conter:

- identificação de **quem** ocupou um lugar — nome, `id`, e-mail ou qualquer traço do outro
  cliente. O mapa diz `tomado`, nunca *por quem*
- `id` da reserva alheia, ou qualquer campo dela
- dado de gestão: `status` interno da sessão, `id` da reserva que ocupa o lugar, `expires_at` de
  reserva de terceiro, custo, ocupação agregada
- sessões em rascunho ou canceladas, sob qualquer forma

Deve existir teste que serialize o mapa inteiro de uma sessão com reservas de **outro** cliente e
afirme a ausência de cada item acima.

---

# O que o contrato deliberadamente não tem

| Ausente | Por quê |
|---|---|
| `DELETE /reservas/<id>/` | Cancelamento pelo cliente está fora de escopo; só a expiração devolve o lugar |
| `POST /reservas/<id>/pagar/` | Pagamento é a próxima feature — aqui há só o handoff (FR-028) |
| Qualquer campo de ingresso ou QR | Nenhum ingresso é emitido nesta feature (FR-029) |
| WebSocket ou *polling* do mapa | Atualização em tempo real está fora de escopo; o `409` é o que informa a mudança |
| `PATCH` de assentos da reserva | Trocar de lugar exigiria liberar e retomar sob bloqueio, com regra própria — não está no escopo |
