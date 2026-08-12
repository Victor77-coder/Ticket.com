# Contrato — Meus Ingressos e Compartilhamento por Link

**Feature**: `009-my-tickets-sharing` · **Data**: 2026-08-12

Cinco endereços. Quatro exigem sessão de **cliente**; um é público e é o único da API inteira que
entrega o código de um ingresso a quem não se identificou.

Nenhum contrato existente muda de forma (FR-058). `TicketSerializer` da 008 é reaproveitado **como
está**, e é ele que define o objeto `Ingresso` abaixo.

---

## O objeto `Ingresso` — o recorte da 008, inalterado

```json
{
  "codigo": "eyJzIjo0LCJ0IjoiM2Y5...":"assinado",
  "qr_svg": "data:image/svg+xml;base64,PHN2Zy...",
  "filme": "Duna: Parte Dois",
  "sessao": "2026-08-20T21:30:00Z",
  "sala": "Sala 3",
  "assento": { "fileira": "F", "numero": 12 }
}
```

`codigo` e `qr_svg` andam juntos por decisão da 008: o código é a verdade assinada, o QR é uma
representação dele, e o texto fica visível porque a portaria exige digitação manual como alternativa
sempre disponível.

---

## 1. `GET /api/v1/meus-ingressos/`

A lista do cliente autenticado (FR-001, FR-004).

**Autenticação**: sessão · **Papel**: `customer`

### `200` — com ingressos

```json
{
  "futuros": [
    {
      "id": "3f9a1c22-8e4b-4d51-9a77-2c5f0b1e9d33",
      "grupo": "futuro",
      "sessao_cancelada": false,
      "codigo": "...", "qr_svg": "...",
      "filme": "Duna: Parte Dois",
      "sessao": "2026-08-20T21:30:00Z",
      "sala": "Sala 3",
      "assento": { "fileira": "F", "numero": 12 }
    }
  ],
  "passados": [
    {
      "id": "b1d4e7f0-1122-4c33-8890-aa55bb66cc77",
      "grupo": "passado",
      "sessao_cancelada": false,
      "codigo": "...", "qr_svg": "...",
      "filme": "Cidade de Deus",
      "sessao": "2026-08-05T19:00:00Z",
      "sala": "Sala 1",
      "assento": { "fileira": "C", "numero": 4 }
    }
  ]
}
```

**Os grupos vêm separados do servidor** (FR-010). O front não recebe uma lista e um instante para
comparar: recebe dois grupos já ordenados — `futuros` por sessão **crescente** (o da próxima sessão
primeiro, FR-007) e `passados` por sessão **decrescente** (o mais recente primeiro, FR-008). O relógio
do navegador não participa da decisão.

**`sessao_cancelada` é campo próprio, e não um terceiro valor de `grupo`** (FR-011). Uma sessão
cancelada que ainda não começou continua pertencendo ao grupo dos futuros; cancelamento e horário são
fatos ortogonais, e fundi-los num campo obrigaria o front a desfazer a fusão.

**`id` é o `public_id` do ingresso**, e é o que identifica o ingresso nas rotas do dono. UUID, nunca
sequencial — a 008 já escolheu assim para não revelar quantos ingressos existem.

### `200` — sem ingresso nenhum

```json
{ "futuros": [], "passados": [] }
```

**Não é `404` e não é `204`.** O cliente sem ingressos tem uma lista, e ela está vazia — o estado
vazio é uma tela escrita para humanos (FR-012), não a ausência de um recurso. Um `404` faria o front
tratar "nunca comprou" como erro.

O front só exibe o estado vazio quando **os dois** grupos estão vazios (FR-013): quem só tem
ingressos passados vê a lista normal.

### Outros desfechos

| Código | Quando | Corpo |
|---|---|---|
| `401` | sem sessão | `{"detail": "Entre para ver seus ingressos."}` |
| `403` | organizador ou portaria | `{"detail": "Apenas clientes têm ingressos."}` |

O `401` é traduzido na view, como em 007 e 008 — o DRF converteria "não autenticado" em `403` porque
a sessão não oferece `WWW-Authenticate`, e o front precisa distinguir "conduza à entrada" de "seu
papel não tem ingressos" (FR-051).

---

## 2. `GET /api/v1/ingressos/<public_id>/`

O ingresso, para o dono, com o estado do link (FR-015).

**Autenticação**: sessão · **Papel**: `customer` · **Posse**: obrigatória

### `200`

```json
{
  "id": "3f9a1c22-8e4b-4d51-9a77-2c5f0b1e9d33",
  "grupo": "futuro",
  "sessao_cancelada": false,
  "codigo": "...", "qr_svg": "...",
  "filme": "Duna: Parte Dois",
  "sessao": "2026-08-20T21:30:00Z",
  "sala": "Sala 3",
  "assento": { "fileira": "F", "numero": 12 },
  "link": {
    "ativo": true,
    "endereco": "http://localhost:5003/ingresso/kJ8w...43-caracteres"
  }
}
```

Sem link ativo, `link` é `{"ativo": false, "endereco": null}` (FR-034: ingresso sem link gerado não
tem endereço público algum).

**`endereco` vem completo, pronto para copiar** (FR-024). Montá-lo no navegador exigiria que o front
soubesse a origem pública, o que erra atrás de proxy e em qualquer ambiente que não seja o de
desenvolvimento.

### Outros desfechos

| Código | Quando | Corpo |
|---|---|---|
| `401` | sem sessão | `{"detail": "Entre para ver seus ingressos."}` |
| `403` | organizador ou portaria | `{"detail": "Apenas clientes têm ingressos."}` |
| `404` | ingresso inexistente **ou de outro cliente** | `{"detail": "Ingresso não encontrado."}` |

**`404` e não `403` para ingresso alheio.** Um `403` confirmaria que aquele `public_id` existe — e
`public_id` é exatamente o valor que vai dentro do código assinado do QR. Mesma regra que 007 e 008
já aplicam a reservas.

---

## 3. `POST /api/v1/ingressos/<public_id>/link/`

Gera o link. **Idempotente** (FR-028).

**Autenticação**: sessão · **Papel**: `customer` · **Posse**: obrigatória · **Corpo**: vazio

| Código | Quando | Corpo |
|---|---|---|
| `201` | criou o link | `{"ativo": true, "endereco": "http://.../ingresso/<token>"}` |
| `200` | já existia link ativo | o **mesmo** endereço |
| `401` / `403` / `404` | como acima | — |

**`201` versus `200` segue o padrão que a 007 estabeleceu** em `POST /reservas/`: `201` quando criou,
`200` quando a chamada foi idempotente. É o que permite ao front distinguir "gerei agora" de "já era
seu" sem interpretar texto.

**Duas requisições simultâneas devolvem o mesmo endereço** (FR-029). A perdedora da corrida não vê
erro: a constraint `um_link_ativo_por_ingresso` recusa a segunda inserção, o serviço relê e devolve o
link do vencedor. Do lado de fora, idempotência — que é o que o cliente pediu.

**Nunca `409`.** Não há conflito a reportar: o cliente pediu um link e recebeu um link.

---

## 4. `DELETE /api/v1/ingressos/<public_id>/link/`

Revoga o link ativo (FR-030).

**Autenticação**: sessão · **Papel**: `customer` · **Posse**: obrigatória

| Código | Quando | Corpo |
|---|---|---|
| `200` | revogou, ou já não havia link ativo | `{"ativo": false, "endereco": null}` |
| `401` / `403` / `404` | como acima | — |

**Revogar duas vezes devolve `200` nas duas.** A operação é um `UPDATE` condicional
(`WHERE revoked_at IS NULL`), então a segunda chamada afeta zero linhas e responde o mesmo estado. Um
`404` na segunda chamada faria o front exibir erro por uma ação que produziu exatamente o resultado
desejado.

**A revogação não toca o ingresso** (FR-033). O código assinado do QR é derivado de `public_id` +
sessão num módulo puro que não conhece a existência de link nenhum. Verificável: `codigo` antes e
depois da revogação é o mesmo texto (SC-010).

**Gerar depois de revogar produz endereço diferente** (FR-032), e o revogado continua sem valer para
sempre (FR-031) — a linha antiga é preservada, nunca apagada.

---

## 5. `GET /api/v1/ingressos-compartilhados/<token>/` — **público**

O único endereço da API que entrega um ingresso a quem não se identificou.

**Autenticação**: nenhuma — `permission_classes = [AllowAny]` **e**
`authentication_classes = []`

A segunda metade é o que importa: sem autenticador, não existe caminho pelo qual esta view enxergue
um usuário, então não existe caminho pelo qual ela decida algo com base em quem está olhando — nem por
engano, nem numa refatoração futura. É a mesma declaração explícita que `SeatMapView` da 007 carrega,
porque o padrão do projeto é `IsAuthenticated` por default.

### `200`

```json
{
  "codigo": "...", "qr_svg": "...",
  "filme": "Duna: Parte Dois",
  "sessao": "2026-08-20T21:30:00Z",
  "sala": "Sala 3",
  "assento": { "fileira": "F", "numero": 12 }
}
```

**Exatamente o objeto `Ingresso` da 008, sem um campo a mais** (FR-037).

### `404` — token inexistente, revogado ou substituído

```json
{ "detail": "Este link não vale mais. Peça um novo a quem enviou o ingresso." }
```

**Os três casos respondem igual, byte a byte** (FR-043). A convergência acontece na consulta — o
filtro `revoked_at IS NULL` faz token morto e token inexistente saírem como o mesmo `None` —, e não
num `if` da view. Quando os casos convergem cedo, não sobra caminho por onde a distinção vaze depois.

Distinguir entregaria a quem está tentando adivinhar a informação de que um palpite chegou perto.

**A frase é do produto, não do framework.** "Não encontrado" mandaria a pessoa que recebeu o ingresso
concluir que o site está quebrado; a frase diz o que houve e qual é a próxima ação (FR-052).

---

## Campos PROIBIDOS na resposta pública

O teste de FR-042 inspeciona a resposta **inteira**, serializada, e falha se qualquer um destes
aparecer — pelo valor, não pelo nome do campo. É requisito da constitution (Princípio III), no mesmo
espírito do que `test_seat_map_api.py` já faz com o mapa público da 007.

| Proibido | Por quê |
|---|---|
| nome, e-mail, `username` ou id do comprador | FR-038. A página mostra o ingresso, não quem o comprou |
| qualquer outro ingresso da mesma compra | FR-039. Um link dá acesso a **um** ingresso |
| valor pago, `total`, `cartao_final`, `bandeira` | FR-040 |
| id de reserva, de pagamento ou de ingresso (`public_id`) | FR-041. Identificador reaproveitável — e `public_id` é o que vai dentro do código assinado |
| `expira_em`, `situacao` da reserva | Estado de compra, não do ingresso |
| capacidade da sala, status da sessão, preço | Dado de gestão. A 007 já proíbe no mapa público |
| o próprio token, ecoado no corpo | Quem abriu já o tem; ecoá-lo só amplia onde ele aparece |
| `TICKET_SIGNING_KEY`, em qualquer forma | Princípio III. O segredo nunca sai do back-end |

---

## Rotas do front

| Rota | Sessão | O que é |
|---|---|---|
| `/meus-ingressos` | exigida | A lista, com os dois grupos e o estado vazio |
| `/meus-ingressos/[id]` | exigida | O ingresso do dono, com copiar / gerar / revogar |
| `/ingresso/[token]` | **nenhuma** | A página pública |

**Proxy do navegador**: `POST` e `DELETE` em `/api/link-do-ingresso`, seguindo o padrão de 002, 003,
007 e 008 — o navegador nunca fala com o Django direto. As rotas de leitura são Server Components e
chamam `lib/api.ts` no servidor, sem proxy.

**`/ingresso/[token]` declara**:

- `export const dynamic = "force-dynamic"` — sem isso, a revogação continua correta no banco e
  **irrelevante na prática**: a credencial segue sendo servida do cache. É a falha mais discreta da
  feature, e nenhum teste de back-end a pegaria (R13, SC-009).
- `robots: { index: false, follow: false }` — o endereço **é** a credencial; indexado, passa a ser
  encontrável por quem nunca o recebeu, e revogar um por um não recupera o que já foi rastreado
  (FR-044).
- `referrer: "no-referrer"` — sem isso, qualquer navegação a partir da página manda o endereço
  completo, token incluído, no cabeçalho `Referer` do destino. A página não tem links de saída por
  FR-039, e o cabeçalho faz a garantia sobreviver ao dia em que alguém acrescentar um.

**A página pública não recebe o cookie de sessão.** O Server Component que a renderiza chama a API sem
repassá-lo — é o que faz FR-036 ("não pede autenticação e não conduz a nenhuma entrada") ser estrutura
em vez de comportamento.
