# Quickstart — Telas de Compra

**Feature**: `012-telas-de-compra` · **Data**: 2026-08-12

Percurso manual das três telas e das duas quebras de propósito que esta feature precisa sentir.
A aplicação no ar, catálogo sincronizado e semeado — o mesmo setup do README.

```bash
docker compose up -d
docker compose exec backend python manage.py sync_tmdb --limit 20
docker compose exec backend python manage.py seed_demo
```

Interface: <http://localhost:5003>

---

## 1. Página do filme — grade, não lista

1. Home → **Ver ingressos** no primeiro destaque.
2. Conferir as três seções: Sessões (ativa), Sobre, Trailers.
3. Em Sessões: seletor de dia; horários agrupados por sala.
4. Trocar o dia: a grade muda sem recarregar o filme.
5. Horário esgotado, se houver: diz "Esgotada" e não navega.
6. Horário disponível: **uma** interação até o mapa.
7. Sobre: sinopse completa; classificação, duração, gênero se existirem; **nada** de direção ou
   elenco inventado.
8. Trailers: reproduz, ou explica a ausência. Fechar e voltar a Sessões: o filme continua o mesmo.

Filme sem sessão (trilha Em breve, se houver): Sessões explica; Sobre e Trailers continuam lá.

---

## 2. Mapa — resumo ao lado

1. Em 1440×900: sala à esquerda, resumo à direita — não só uma barra embaixo.
2. Selecionar dois lugares: o resumo lista os dois e o total.
3. Desmarcar um: o resumo acompanha.
4. Confirmar sem seleção: o aviso em português continua.
5. Em escala de cinza (filtro do sistema ou o helper da 007): os quatro estados distinguíveis.
6. Em 320px: resumo empilha abaixo; **sem** rolagem lateral.

---

## 3. Pagamento — ver o que se leva, receber objeto

1. Confirmar lugares (autenticado como `cliente1` / `desafio2026`).
2. Continuar para pagamento.
3. Em 1440×900: resumo e formulário lado a lado; prazo visível.
4. Cartão recusado da 008: a frase do servidor, distinta do erro de campo.
5. Cartão aprovado: um ingresso por lugar, lugar grande, QR **branco**, código em texto.
6. Em 320px: empilha sem rolagem lateral.

---

## 4. O catálogo não se moveu

1. Voltar à home.
2. Carrossel, trilhas e busca iguais aos da 011.
3. `git diff -- frontend/components/highlights frontend/components/rows frontend/app/page.tsx frontend/components/header` deve ser vazio (o import de `TrailerFrame` **a partir** de highlights, na página do filme, não conta como editar highlights).

---

## 5. Quebrar de propósito

Duas quebras. Se o teste correspondente não falhar, ele não está medindo.

| Quebra | O que passa a acontecer | O que tem de falhar |
|---|---|---|
| Omitir `trailers` no detalhe do filme | a aba Trailers não sabe se é vazio ou se o campo faltou | teste do contrato `filme-detalhe.md` |
| Harmonizar `--cor-fundo-qr` com a marca no ingresso-objeto | a catraca deixa de ler; o teste da 008/011 de fundo branco | `tokens.test.ts` (A2 / fundo do QR) e o teste do ingresso |

Não quebrar a constraint de reserva "para ver": esta feature não a toca, e o teste de concorrência
da 007/008 continua sendo a defesa — não se aluga ele para composição.

---

## 6. Suíte

Da raiz, o mesmo trio da 011, contra a linha de base dela:

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
# em frontend/
npx playwright test --workers=2
```

Nenhuma asserção de regra de negócio das 001–011 removida ou afrouxada. Seletor da lista de
sessões no e2e da 007 pode mudar **se** o nome acessível `Escolher lugares —` for preservado
(research R5); se não for, o ajuste é na implementação, não no teste.
