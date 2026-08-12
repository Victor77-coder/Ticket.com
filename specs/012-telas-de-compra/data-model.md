# Data Model — Telas de Compra

**Feature**: `012-telas-de-compra` · **Data**: 2026-08-12

Esta feature **não cria tabela**. O que ela tem é um modelo de apresentação sobre entidades que
já existem, mais um campo aditivo na resposta pública do filme.

---

## Entidades persistidas (intocadas)

Nenhuma migração. Nenhuma coluna nova.

| Entidade | Feature | O que esta feature faz |
|---|---|---|
| `Movie` | 001 | Lê título, sinopse, cartaz, classificação, duração, gêneros, estreia |
| `Trailer` | 001 | Lê a lista já persistida; não marca primário novo; não sincroniza |
| `Screening` | 001 / 007 | Lê `id`, `starts_at`, `price`, sala, `has_available_seats` |
| `Seat` / `ReservedSeat` / `Reservation` | 007 | Intocados |
| `Payment` / `Ticket` | 008 | Intocados — o QR e o código continuam os mesmos |

---

## Entidades de apresentação

### Seção da página do filme

Não persiste. Estado da ilha cliente.

| Campo | Valores | Invariante |
|---|---|---|
| `ativa` | `sessoes` \| `sobre` \| `trailers` | Exatamente uma. Padrão: `sessoes` |
| Visibilidade | as três sempre existem na página | Filme sem sessão ou sem trailer **não** esconde a seção |

### Grade do dia

Derivada de `screenings[]` no cliente (R1). Não é payload da API.

| Campo | Origem |
|---|---|
| `dia` | data civil de `starts_at` em `America/Sao_Paulo` |
| `rotulo` | "Hoje" se for hoje nesse fuso; senão o dia da semana abreviado + `DD/MM` |
| `salas[]` | agrupamento estável por `room_name` |
| `horarios[]` | as sessões daquele dia naquela sala, ordenadas por `starts_at` |

**Invariantes**:
- Não aparece dia sem sessão.
- Um único dia continua no seletor.
- `id` da sessão é o mesmo `screenings[].id` — o link `/sessoes/{id}` não muda.
- Esgotada (`has_available_seats === false`) permanece na grade e não é link.

### Resumo da compra

Já existe (007/008). Reposicionado.

| Superfície | Quando | Conteúdo |
|---|---|---|
| Mapa, antes de confirmar | seleção local | filme, horário, sala, lugares, total **estimado** como hoje (preço da sessão × quantidade) |
| Mapa, reserva feita | `ReservationPanel` | lugares, prazo, CTA de pagamento — conteúdo da 007 |
| Pagamento, a pagar | `ResumoDaCompra` | filme, sessão, sala, lugares, **total do servidor** |

O total pago **nunca** é recontado no cliente a partir do preço unitário na tela de pagamento
(FR da 008). Esta feature não reabre isso.

### Ingresso emitido (variante)

Mesma entidade `Ticket` da 008. Duas composições, um componente (R7).

| Variante | Onde | O que muda |
|---|---|---|
| `cartao` (padrão) | meus ingressos, página pública | a da 008/009 — **não alterar** |
| `objeto` | só a tela de pagamento após aprovação | hierarquia: lugar maior, picote; QR branco e código digitável **iguais** |

---

## Campo aditivo na resposta do filme

`GET /api/v1/filmes/<slug>/` — ver [contracts/filme-detalhe.md](./contracts/filme-detalhe.md).

```text
MovieDetail += trailers: TrailerPublico[]
TrailerPublico = { provider, external_key, kind, name }
```

`trailers` é lista, possivelmente vazia. Ordem: primário primeiro, depois `published_at`
descendente, desempate por `pk`. Determinística.

**O que NÃO entra**: `is_primary` como flag de gestão, `language`, ids internos do TMDb além da
chave do vídeo que a home já usa. Gate do Princípio IV — a resposta continua pública.

---

## Invariantes que o teste verifica

1. Highlights, home e busca **não** ganham `kind`/`name` por esta feature.
2. `trailers: []` no detalhe de filme sem vídeo — nunca omitir a chave, nunca `null`.
3. Agrupamento: duas sessões no mesmo dia civil e salas diferentes caem no mesmo dia, salas
   distintas.
4. Variante `cartao` do `Ingresso` continua passando os testes da 009 (código visível, QR com
   fundo branco, sem comprador).
5. Variante `objeto` também tem QR branco e código visível — SC-006.
