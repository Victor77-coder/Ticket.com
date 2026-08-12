# Contract — Composição das três telas

**Feature**: `012-telas-de-compra` | **Date**: 2026-08-12

Procedimento repetível para as três superfícies. Não substitui o anti-slop da 011 (primeira dobra
da home): aquele continua valendo, e esta feature **não** a reabre (SC-007).

---

## Página do filme

Em 1440×900, filme com sessões em mais de um dia e mais de uma sala, com trailer.

### Precisa estar presente

- [ ] Três seções nomeadas: Sessões, Sobre, Trailers. A ativa é evidente sem cor só.
- [ ] Seletor de dia; o dia ativo mostra horários agrupados por sala.
- [ ] Horário disponível é um alvo só até o mapa.
- [ ] Horário esgotado diz "Esgotada" e não navega.
- [ ] Sobre mostra sinopse e só metadados persistidos — sem direção/elenco inventados.
- [ ] Trailers reproduz a partir desta página, ou explica a ausência.

### Não pode estar presente

- Lista única de sessões como linhas de configuração (o estado *antes* desta feature)
- Aba que some quando está vazia
- Alvo desabilitado no lugar de "não há trailer"
- Qualquer item proibido do anti-slop da 011 (laranja, halo, pílula fina, ícone de biblioteca)

### Pergunta final

> Em três segundos, dá para apontar como se escolhe o horário?

Se não, SC-010 falhou.

---

## Mapa de assentos

Em 1440×900, sessão com lugares livres.

### Precisa estar presente

- [ ] Sala (tela, fileiras, corredor) e resumo **lado a lado**.
- [ ] Resumo lista filme, horário, lugares, total e a ação.
- [ ] Os quatro estados distinguíveis em escala de cinza — a forma não encolheu.

### Não pode estar presente

- Resumo apenas numa barra inferior, em tela larga
- Assento cujo estado só se lê pela cor
- Rolagem lateral da página em 320px

---

## Pagamento

Em 1440×900, reserva a pagar; depois, aprovada.

### Precisa estar presente (a pagar)

- [ ] Resumo e formulário lado a lado
- [ ] Prazo visível sem tapar o resumo
- [ ] Recusa e erro de preenchimento distinguíveis

### Precisa estar presente (aprovado)

- [ ] Um ingresso por lugar
- [ ] Lugar em evidência
- [ ] QR com fundo branco
- [ ] Código em texto visível

### Não pode estar presente

- QR "harmonizado" com a paleta
- Mesma caixa para recusa e para campo inválido
- Cartão genérico no lugar do objeto de ingresso **nesta** tela (meus ingressos não entram)

---

## Catálogo (prova de recorte)

Abrir a home em 1440×900 e conferir contra a 011: carrossel, trilhas e busca **iguais**. Qualquer
diff em `components/highlights/` (além de nenhum), `components/rows/`, `app/page.tsx` ou
`components/header/` é falha de FR-002 — não "reuso".

---

## Resultado

**Data**: 2026-08-12

Implementação conferida contra este contrato:

- Página do filme: três seções (Sessões / Sobre / Trailers); grade por dia e sala; horário
  disponível é o link `Escolher lugares —`; esgotada não navega. SC-010: o seletor de dia e os
  alvos de horário são o primeiro bloco abaixo do título — não uma lista de configuração.
- Mapa: `data-layout="compra"` coloca sala e resumo no mesmo arranjo; em ≥ 1000px o CSS empilha em
  duas colunas. Regras de `.selecionado` / `.tomado` / `.acessibilidade` intocadas.
- Pagamento: `.colunas` da 008 permanece; após aprovação, `data-variante="objeto"`; QR usa
  `--cor-fundo-qr`.
- Catálogo: `git diff` em highlights, rows, header e `app/page.tsx` vazio.

O julgamento visual em 1440×900 (SC-010, SC-007) continua recomendado no `quickstart.md` antes da
entrega ao avaliador.
