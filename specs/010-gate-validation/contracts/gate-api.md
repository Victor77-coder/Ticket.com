# Contrato — Validação de Ingressos na Portaria

**Feature**: `010-gate-validation` · **Data**: 2026-08-12

Dois endereços, ambos exigindo sessão do papel **portaria**. Nenhum contrato existente muda de forma
(FR-045), e o formato do código continua sendo o da 008 (FR-046).

---

## 1. `GET /api/v1/portaria/sessoes/`

As sessões que este posto pode receber (FR-002, FR-003).

**Autenticação**: sessão · **Papel**: `gate`

### `200`

```json
{
  "sessoes": [
    {
      "id": 272,
      "filme": "Duna: Parte Dois",
      "inicio": "2026-08-12T21:30:00Z",
      "sala": "Sala 3"
    },
    {
      "id": 273,
      "filme": "Cidade de Deus",
      "inicio": "2026-08-12T19:00:00Z",
      "sala": "Sala 1"
    }
  ]
}
```

As sessões **do dia**, publicadas, ordenadas por horário, **incluindo as que já começaram** — gente
chega atrasada, e a portaria valida durante a sessão inteira. Canceladas ficam fora: não há entrada a
receber.

**Esta consulta não usa o filtro de vendabilidade**, e é a segunda vez no projeto que esse filtro
seria o erro natural. Ver R11.

### `200` — sem sessões hoje

```json
{ "sessoes": [] }
```

Não é `404`. "Hoje não tem sessão" é um estado da portaria, não a ausência de um recurso — e a tela
tem frase própria para ele (FR-007).

### Outros desfechos

| Código | Quando | Corpo |
|---|---|---|
| `401` | sem sessão | `{"detail": "Entre para usar a portaria."}` |
| `403` | cliente ou organizador | `{"detail": "Apenas a portaria valida ingressos."}` |

O `401` é traduzido na view, como em 007, 008 e 009 — o DRF converteria "não autenticado" em `403`
porque a sessão não oferece `WWW-Authenticate`, e o front precisa distinguir "conduza à entrada" de
"seu papel não valida" (FR-041, FR-042).

---

## 2. `POST /api/v1/portaria/validar/`

A validação. **É a única escrita da feature.**

**Autenticação**: sessão · **Papel**: `gate`

### Corpo

```json
{
  "codigo": "eyJzIjoyNzIsInQiOiI4ZTJhZDI3Ny03NTQwLTRhNjctODcwOC1mZTU2Zjk5NjIwNzMifQ:NzydRz...",
  "sessao": 272
}
```

`codigo` é **exatamente** o que a 008 emite e a 009 exibe em texto e em QR. Nenhum segundo formato
existe (FR-012). Espaços e quebras de linha nas pontas são tolerados (FR-013) — copiar de um
aplicativo de mensagens costuma trazer isso junto.

`sessao` é a **sessão da porta**, escolhida pelo operador. Vem do cliente por decisão registrada
(R9): a escolha é por posto, não por conta, e dois operadores podem usar a mesma conta do seed em
portas diferentes. Não é escalada de privilégio — o operador obteria o mesmo resultado escolhendo
outra sessão no menu; a autorização que importa continua sendo o papel, conferida no servidor.

---

### `200` — os **quatro** desfechos

**Todos os quatro respondem `200`.** Nenhum deles é erro **da requisição**: a portaria perguntou
"posso deixar entrar?" e recebeu resposta. "Não" é uma resposta.

Mapear **já utilizado** para `409` ou **inválido** para `422` faria o front distinguir desfecho de
negócio por semântica de HTTP, e qualquer camada que trate `4xx` como erro esconderia um desfecho
legítimo. (Diferença deliberada em relação à 008, onde a recusa de cartão é `402` porque lá os
códigos separam **caminhos de recuperação** distintos — "corrija o formulário" e "troque de cartão".
Aqui os quatro vão para a mesma tela.)

O front escolhe símbolo, título e destaque pelo campo `situacao` — **nunca** interpretando a frase,
que é apresentação e muda numa revisão de redação.

#### `situacao: "valido"`

```json
{
  "situacao": "valido",
  "detail": "Pode entrar. Sala 3, lugar F12.",
  "ingresso": {
    "filme": "Duna: Parte Dois",
    "sessao": "2026-08-12T21:30:00Z",
    "sala": "Sala 3",
    "assento": { "fileira": "F", "numero": 12 }
  }
}
```

O lugar é obrigatório (FR-020): é o que o operador diz à pessoa.

#### `situacao: "ja_utilizado"`

```json
{
  "situacao": "ja_utilizado",
  "detail": "Este ingresso já foi usado às 21:14. Não libere a entrada.",
  "utilizado_em": "2026-08-12T21:14:03Z",
  "ingresso": { "…": "mesmos campos de cima" }
}
```

`utilizado_em` é obrigatório (FR-021) — é o que permite ao operador julgar se é a mesma pessoa
voltando ou outra com uma captura de tela. O instante **nunca** muda em apresentações seguintes
(FR-033).

#### `situacao: "sessao_errada"`

```json
{
  "situacao": "sessao_errada",
  "detail": "Este ingresso é da sessão das 19:00, Sala 1. Não é esta porta.",
  "sessao_do_ingresso": {
    "filme": "Cidade de Deus",
    "inicio": "2026-08-12T19:00:00Z",
    "sala": "Sala 1",
    "cancelada": false
  }
}
```

`sessao_do_ingresso` é obrigatório (FR-022): sem ele o operador nega sem saber orientar a pessoa.

`cancelada` cobre FR-023. Quando `true`, a frase muda para dizer que aquela sessão foi cancelada —
**dentro** do mesmo desfecho, nunca como um quinto (FR-024).

**Este desfecho não escreve nada** (FR-031). O ingresso continua utilizável na porta certa.

#### `situacao: "invalido"`

```json
{
  "situacao": "invalido",
  "detail": "Ingresso não reconhecido. Não libere a entrada."
}
```

**Sem nenhum campo extra**, e a ausência é a decisão: assinatura que não confere, código inventado e
código bem assinado sem ingresso correspondente respondem **idênticos** (FR-029). Qualquer detalhe a
mais entregaria a quem tenta adivinhar a informação de onde o palpite chegou perto.

---

### Outros desfechos

| Código | Quando | Corpo |
|---|---|---|
| `400` | `codigo` vazio ou ausente | `{"detail": "Apresente ou digite um código."}` |
| `400` | `sessao` ausente ou inexistente | `{"detail": "Escolha a sessão que esta porta está recebendo."}` |
| `401` | sem sessão | `{"detail": "Entre para usar a portaria."}` |
| `403` | cliente ou organizador | `{"detail": "Apenas a portaria valida ingressos."}` |

**`400` de campo vazio é distinto de `invalido`** (FR-014). Nada foi apresentado — não há o que
julgar, e dizer "ingresso não reconhecido" para um campo em branco faria o operador procurar um
problema no ingresso da pessoa.

---

## Campos PROIBIDOS na resposta de validação

| Proibido | Por quê |
|---|---|
| nome, e-mail ou id do comprador | A portaria confere o ingresso, não a identidade de quem comprou |
| valor pago, `cartao_final`, `bandeira` | Dado de pagamento não tem função na porta |
| `public_id` do ingresso | Identificador reaproveitável, e é o que vai dentro do código assinado |
| id de reserva ou de pagamento | Idem |
| `codigo` ecoado de volta | Quem chamou já o tem; ecoá-lo só amplia onde ele aparece |
| `TICKET_SIGNING_KEY`, em qualquer forma | Princípio III — o segredo nunca sai do back-end |
| qualquer detalhe no desfecho `invalido` | Entregaria oráculo a quem tenta adivinhar (FR-029) |

---

## O que NÃO muda em nenhum contrato existente

- **`TicketSerializer`** (008) e **`MeuIngressoSerializer`** (009) **não** ganham o campo de uso
  (FR-048). Uma linha, e "utilizado" apareceria na página compartilhada **pública** da 009.
  `test_share_link_leakage.py` passa a listar o campo entre os proibidos.
- **O formato do código** e a **chave de assinatura** continuam os da 008 (FR-046) — há ingressos
  emitidos, e mudar qualquer um dos dois os invalidaria em massa.
- **As respostas de reserva e pagamento** (007, 008) seguem idênticas.

---

## Rotas do front

| Rota | Sessão | O que é |
|---|---|---|
| `/portaria` | exigida, papel `gate` | A tela de validação, com escolha de sessão, câmera e digitação |

**Proxy do navegador**: `POST /api/validar`, seguindo o padrão de 002, 003, 007, 008 e 009 — o
navegador nunca fala com o Django direto.

**A tela declara `dynamic = "force-dynamic"`**: o estado depende da sessão e do papel, e uma resposta
guardada serviria a pessoa errada.

**Cliente e organizador que alcancem `/portaria`** leem uma explicação e **não** são conduzidos à
entrada (FR-041): entrar de novo não muda o papel, e o caminho não teria saída. Visitante sem sessão
**é** conduzido, e volta para `/portaria` depois de entrar (FR-042).

**A câmera exige contexto seguro.** `localhost` serve; IP de rede local não, e nenhuma configuração
da aplicação muda isso (R7). A tela detecta e explica, e a digitação manual — que a constitution já
exigia estar "sempre disponível" — é o que mantém a portaria funcionando nesse cenário.
