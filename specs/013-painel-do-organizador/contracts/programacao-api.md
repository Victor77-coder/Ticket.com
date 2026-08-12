# Contrato — API de Programação

**Prefixo**: `/api/v1/programacao/`
**Autorização**: `IsOrganizer` em **todos** os endpoints abaixo, sem exceção.

Um endpoint novo colocado sob este prefixo nasce coberto. Um endpoint de programação colocado
**fora** dele é falha de FR-034, ainda que declare a permissão certa — o prefixo é o que torna a
regra legível de fora.

## Autorização, antes de tudo

| Quem chama | Resposta | Por quê |
|---|---|---|
| Sem sessão | `401` + `{"detail": "Entre para programar sessões."}` | Não entrou |
| Cliente autenticado | `403` + `{"detail": "Apenas organizadores programam sessões."}` | **Entrou**, papel errado |
| Portaria autenticada | `403` + mesma frase | Idem |
| Organizador | `200`/`201`/`204` | — |

**`403`, nunca `401`, para papel errado.** Entrar de novo não muda o papel; um `401` mandaria o
front para a entrada e o caminho não teria saída. É a mesma distinção que `IsCustomer`,
`IsCustomerParaPagar`, `IsCustomerParaIngressos` e `IsGate` já aplicam.

**Proibido**: qualquer um destes endpoints responder diferente conforme o front esconda ou não o
controle. A recusa é do servidor (FR-037).

---

## Filmes

### `GET /programacao/filmes/`

Catálogo **local**, para escolher sem passar pelo TMDb (FR-013).

```json
{
  "count": 12,
  "results": [
    { "id": 7, "tmdb_id": 872585, "titulo": "A Odisseia", "ano": 2026,
      "poster_url": "https://…/w500/abc.jpg", "duracao_min": 166, "sessoes": 3 }
  ]
}
```

`sessoes` é a contagem de sessões **não canceladas** do filme — agregada, não por linha.

### `GET /programacao/filmes/busca/?q=<termo>`

Busca no TMDb, **pelo back-end** (FR-009, FR-010).

```json
{
  "termo": "duna",
  "count": 8,
  "results": [
    { "tmdb_id": 693134, "titulo": "Duna: Parte Dois", "ano": 2024,
      "poster_url": "https://…/w500/xyz.jpg", "ja_no_catalogo": true }
  ]
}
```

| Situação | Status | Corpo |
|---|---|---|
| `q` vazio ou só espaços | `200` | `{"termo": "", "count": 0, "results": []}` — não é erro |
| TMDb indisponível / timeout / chave recusada | `502` | `{"detail": "<frase do TMDBError, em pt-BR>"}` |
| Nada encontrado | `200` | `count: 0` — o estado vazio é da interface |

**A frase do erro vem do `TMDBError`, não é reescrita aqui.** Ele já distingue timeout ("O TMDb não
respondeu em 10s…"), chave recusada e erro de status, todas com próxima ação. Traduzir de novo
criaria duas redações da mesma falha.

**Nunca** aparece no corpo, em nenhuma circunstância: `TMDB_API_KEY`, a URL com a chave, ou qualquer
cabeçalho da chamada externa (FR-010).

### `POST /programacao/filmes/`

Importa e persiste localmente (FR-011, FR-011a).

**Entrada**: `{ "tmdb_id": 693134 }`

| Situação | Status | Corpo |
|---|---|---|
| Importado | `201` | O filme, no formato de `GET /programacao/filmes/` |
| **Já existia** | `200` | O filme existente — **não duplica, não é erro** (FR-012) |
| `tmdb_id` ausente/inválido | `400` | `{"tmdb_id": ["…"]}` |
| TMDb fora do ar | `502` | frase do `TMDBError` |

O que é persistido: **tudo** o que `sync_movie` já mapeia — título, pôster, sinopse, duração,
gêneros, classificação indicativa e trailers. Não existe um segundo mapeamento reduzido (FR-011a).

`is_trending` e `is_upcoming` são passados como `False` e, por construção de `sync_movie`, **não
desmarcam** um filme que já estava marcado. Importar pelo painel nunca rebaixa um filme na home
(FR-046).

---

## Salas

### `GET /programacao/salas/`

```json
{
  "count": 2,
  "results": [
    { "id": 1, "nome": "Sala 1", "capacidade": 60, "lugares": 60,
      "acessiveis": 3, "ocupacao_viva": 4, "pode_trocar_capacidade": false }
  ]
}
```

`pode_trocar_capacidade` é `ocupacao_viva == 0`. Existe para a interface **desabilitar com
explicação**, nunca como autorização — `PATCH` revalida (FR-020).

### `POST /programacao/salas/`

**Entrada**: `{ "nome": "Sala 3", "capacidade": 80 }` → `201` com a sala e seus lugares já gerados.

| Recusa | Status | Frase |
|---|---|---|
| Capacidade ausente, não numérica, ≤ 0 | `400` | "Informe uma capacidade maior que zero." |
| Capacidade acima do teto | `400` | "A capacidade máxima é 260 lugares (26 fileiras de 10)." |
| Nome vazio | `400` | "Dê um nome à sala." |

O teto é derivado de `26 × SEATS_PER_ROW`, **calculado**, nunca digitado como literal na frase — se
`SEATS_PER_ROW` mudar, a mensagem acompanha.

### `PATCH /programacao/salas/<id>/`

**Entrada**: `{ "nome"?: str, "capacidade"?: int }`

| Situação | Status | Efeito |
|---|---|---|
| Só `nome` | `200` | Renomeia. **Sempre permitido** — não afeta lugar nem venda |
| `capacidade`, sala sem ocupação viva | `200` | Lugares refeitos pela regra de `services/salas.py` |
| `capacidade`, sala **com** ocupação viva | `409` | Nada é apagado |
| Capacidade fora dos limites | `400` | Mesmas frases do POST |

Frase do `409`, que precisa dizer **o que** e **o que fazer**:

> "Esta sala tem 4 lugares ocupados por reservas ou ingressos. Só é possível mudar a capacidade de
> uma sala sem ocupação."

---

## Sessões

### `GET /programacao/sessoes/`

A grade inteira — **os três estados** (FR-029). É a única superfície do sistema que expõe `status`.

```json
{
  "count": 36,
  "results": [
    { "id": 272, "estado": "published", "estado_rotulo": "Publicada",
      "filme": { "id": 7, "titulo": "A Odisseia", "poster_url": "…" },
      "sala": { "id": 1, "nome": "Sala 1", "lugares": 60 },
      "inicio": "2026-08-14T20:30:00-03:00", "preco": "32.00",
      "ocupacao": 12, "a_venda": true,
      "pode_editar": false, "pode_publicar": false, "pode_cancelar": true }
  ]
}
```

- `a_venda` = `sellable()` — publicada **e** no futuro. É **leitura**, e `sellable()` não ganha
  responsabilidade nova (FR-033).
- `ocupacao` vem de uma agregação única sobre a grade, nunca de `seats_taken` por linha (R6).
- Os três `pode_*` são conveniência de interface, revalidados no servidor.

### `POST /programacao/sessoes/`

**Entrada**: `{ "filme": 7, "sala": 1, "inicio": "2026-08-14T20:30:00-03:00", "preco": "32.00", "publicar": true }`

| Recusa | Status | Frase |
|---|---|---|
| `(sala, horário)` já ocupado | `409` | "A Sala 1 já tem sessão às 20:30 de 14/08. Escolha outro horário ou outra sala." |
| Preço ausente, ≤ 0 | `400` | "Informe um preço maior que zero." |
| `publicar: true` com horário passado | `400` | "Não dá para publicar uma sessão que já começou. Escolha um horário futuro." |
| `publicar: true` em sala sem lugares | `400` | "A Sala 3 ainda não tem lugares. Defina a capacidade antes de publicar." |
| Filme ou sala inexistente | `400` | frase do campo |

**O `409` vem do banco.** A frase é montada capturando `IntegrityError` e reconhecendo a constraint
`uma_sessao_por_sala_e_horario` — nunca de um `exists()` prévio (R4). Um `UniqueTogetherValidator`
pode coexistir para o caminho feliz, mas o teste de concorrência é o que prova quem realmente
recusa.

Horário no passado com `publicar: false` é **aceito**: um rascunho é anotação, não promessa.

### `PATCH /programacao/sessoes/<id>/`

Só rascunho (FR-023, FR-024). Campos: `filme`, `sala`, `inicio`, `preco`.

| Situação | Status | Frase |
|---|---|---|
| Sessão publicada ou cancelada | `409` | "Só é possível alterar uma sessão em rascunho. Para mudar esta, cancele e programe outra." |
| Move para `(sala, horário)` ocupado | `409` | mesma frase de conflito do POST |

### `POST /programacao/sessoes/<id>/publicar/`

Corpo vazio. `200` com a sessão publicada.

| Recusa | Status | Frase |
|---|---|---|
| Já publicada | `409` | "Esta sessão já está publicada." |
| Cancelada | `409` | "Esta sessão foi cancelada e não pode voltar." |
| Horário no passado | `400` | mesma frase do POST |
| Sala sem lugares | `400` | mesma frase do POST |

### `POST /programacao/sessoes/<id>/cancelar/`

Corpo vazio. `200` com a sessão cancelada. Vale para **rascunho e publicada** (FR-030).

| Recusa | Status | Frase |
|---|---|---|
| Já cancelada | `409` | "Esta sessão já foi cancelada." |

**O que este endpoint não faz** e nenhum teste pode afrouxar (FR-031): não estorna pagamento, não
apaga `Ticket`, não apaga `ReservedSeat`, não mexe em `used_at`, não devolve ao estoque lugar pago.
Ele muda **uma** coluna: `status`.

---

## Proibições do contrato

Verificáveis em `backend/tests/test_programacao_*.py`:

1. **Nenhum endpoint público ganha campo de gestão.** `status`, `capacity`, contagem de vendidos e
   `tmdb_id` continuam fora de highlights, home, busca, detalhe do filme, mapa e portaria. Os
   serializers públicos mantêm o aviso do topo intacto.
2. **Nenhuma pré-consulta como garantia de unicidade.** Um `exists()` antes do INSERT de sessão é
   falha de R4, mesmo que o teste de caminho feliz passe.
3. **Nenhuma segunda regra de geometria de sala.** A geração de assentos entra por
   `screening/services/salas.py` ou não entra.
4. **Nenhum segundo mapeamento de TMDb.** A importação entra por `sync_movie` ou não entra.
5. **Nenhuma chave do TMDb no corpo, no log de resposta ou em cabeçalho devolvido.**
6. **Nenhuma migração.** `python manage.py makemigrations --check` continua limpo.
