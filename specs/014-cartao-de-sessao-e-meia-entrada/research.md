# Research: Cartão de Sessão e Meia-Entrada

**Feature**: 014 | **Date**: 2026-08-13

Nenhum `NEEDS CLARIFICATION` sobrou da spec: as duas decisões de escopo foram tomadas com o autor
antes da redação. O que este documento resolve são as decisões **de construção**.

---

## R1 — Onde vive o valor cobrado por lugar

**Decisão**: `ReservedSeat` ganha **duas** colunas: `ticket_type` (`inteira` | `meia`) e
`unit_price` (decimal). Ambas escritas na criação da reserva, dentro da transação que já existe, e
**nunca editadas depois**.

**Rationale**: o valor cobrado é um **fato do momento da venda**, não uma função do estado atual da
sessão. Guardá-lo é o que faz uma compra fechada parar de depender do presente.

Guardar as duas colunas parece redundante — o tipo determina o valor, dado o preço da sessão. Não é:
o tipo é o que a **portaria** confere (o operador pede documento de meia), e o valor é o que a
**contabilidade** da compra soma. Derivar um do outro na leitura recria a dependência que a coluna
existe para cortar.

**Alternativas consideradas**:

- **Só `ticket_type`, valor derivado na leitura.** Rejeitada: `valor = screening.price / 2` executado
  na leitura significa que mudar o preço da sessão reescreve o total de uma compra já paga. Hoje a
  013 impede editar sessão publicada, então o defeito não apareceria — mas a proteção estaria na
  regra de outra feature, não aqui.
- **Só `unit_price`, tipo inferido comparando com `screening.price`.** Rejeitada: inferir tipo por
  comparação de valores torna a portaria dependente de aritmética de ponto decimal para dizer se
  pede documento. E uma sessão de preço zero tornaria inteira e meia indistinguíveis.
- **Uma tabela de tipos de ingresso.** Rejeitada por agora: dois valores fixos não são um catálogo.
  Ela nasce quando existir preço por assento (VIP) ou categoria de meia — ambos fora de escopo.

---

## R2 — O total deixa de ser multiplicação e vira soma

**Decisão**: `total_da_reserva(reserva)` passa a ser `SUM(unit_price)` sobre os lugares da reserva.
`services/precos.py` é o dono único da derivação (`valor_do_lugar`), e o total é agregação.

**Rationale — e esta é a parte que o plano ganha de graça**: a regra `preço × quantidade` está hoje
escrita **três vezes**:

| Onde | Forma |
|---|---|
| `services/pagamentos.py:194` | `reserva.screening.price * reserva.seats.count()` |
| `serializers.py:143` (`get_total`) | `reserva.screening.price * len(self._assentos(reserva))` |
| `frontend/components/seats/SeatSelection.tsx:147` | `ids.size * Number(mapa.preco)` |

Ensinar meia-entrada a três cópias é como a divergência entra. Somar uma coluna gravada **elimina as
duas primeiras**: nenhuma delas precisa saber que tipos existem, porque o valor já está decidido na
linha. A terceira é do navegador e continua existindo como **prévia** — ver R5.

**Alternativas consideradas**:

- **Ensinar as três cópias.** Rejeitada pelo motivo acima, e porque a checagem de fim de feature
  (`T-DONO`) ficaria impossível de expressar.
- **Guardar o total na `Reservation`.** Rejeitada: total gravado na reserva e valores gravados nos
  lugares são duas verdades sobre a mesma soma. O `Payment.amount` já congela o total no instante da
  cobrança, que é onde congelar importa.

---

## R3 — O arredondamento da metade

**Decisão**: metade do preço da sessão, **arredondada para baixo em centavos** (`ROUND_DOWN` sobre
duas casas). R$ 25,01 → meia de R$ 12,50.

**Rationale**: três razões, nesta ordem.

1. **Em favor de quem compra.** Um centavo a mais cobrado de uma meia é o tipo de detalhe que só
   aparece em reclamação.
2. **Determinístico e testável.** `ROUND_HALF_EVEN`, o padrão do `Decimal`, faz R$ 25,01 e R$ 25,03
   arredondarem para lados diferentes — correto estatisticamente, incompreensível numa tabela de
   preços exibida ao cliente.
3. **Exibido é igual a cobrado por construção**, porque o valor arredondado é o que vai para a
   coluna (R1). Não existe caminho em que a tela mostre um e a cobrança faça outro.

**Alternativa considerada**: **arredondar para cima**, prática de algumas bilheterias. Rejeitada: não
há regra legal exigindo, e a spec já declara que a meia é 50%.

---

## R4 — O painel de assentos não ganha endpoint

**Decisão**: o painel consome `GET /api/v1/sessoes/<id>/mapa/`, o mesmo do mapa de seleção.

**Rationale**: a resposta já traz exatamente o que o painel precisa — `fileiras[]` com `situacao` por
assento, `sala.nome`, `esgotada` e `preco`. Um endpoint "resumido" seria uma segunda leitura da
ocupação viva, e a `CLAUDE.md` do projeto é explícita: *"Ocupação viva continua sendo
`Reservation.OCUPANDO`, consumida, nunca reescrita."*

A objeção legítima é **peso**: o painel baixa o mapa inteiro para desenhar uma prévia. Numa sala de
60 lugares isso é irrelevante, e a alternativa custa uma superfície nova que precisaria de teste de
contrato próprio e poderia divergir do mapa — que é o defeito que o painel existe para não ter.

**Alternativas consideradas**:

- **Endpoint de resumo (`livres`/`total`).** Rejeitada: não desenharia a sala, que é o pedido.
- **Embutir a ocupação no detalhe do filme.** Rejeitada: tornaria a página do filme dependente da
  ocupação de todas as sessões para exibir qualquer coisa, e a página do filme é rota de catálogo.

---

## R5 — O contrato de reserva cresce por adição

**Decisão**: o corpo de `POST /api/v1/reservas/` ganha o campo **opcional** `meias: [int]`, um
subconjunto de `assentos`. Ausente ou vazio = tudo inteira.

**Rationale**: `assentos: [int]` mantém o significado que tem desde a 007. Nenhum chamador existente
precisa mudar, e o e2e da 007 — que a 012 foi proibida de afrouxar — continua válido sem edição.

E o padrão é seguro **por construção**, não por validação: quem não menciona `meias` compra inteira.
O FR-016 ("nenhum caminho cobra menos por omissão") deixa de depender de alguém lembrar de conferir.

**Validação necessária**: todo id em `meias` DEVE estar em `assentos`. Um id fora da lista é pedido
malformado (400), nunca ignorado em silêncio — ignorar faria a tela e o servidor discordarem sobre o
que foi comprado.

**Alternativas consideradas**:

- **`assentos: [{id, tipo}]`.** Rejeitada: quebra o contrato da 007.
- **Aceitar as duas formas no mesmo campo.** Rejeitada: um campo com duas formas é um campo que todo
  leitor precisa desambiguar, e o serializer precisaria de lógica de detecção.

---

## R6 — O navegador prevê, o servidor decide

**Decisão**: `frontend/lib/meia.ts` implementa a mesma derivação (metade, para baixo) como função
pura, usada **apenas para o resumo antes de reservar**. Depois de criada a reserva, todo valor
exibido vem do servidor.

**Rationale**: a alternativa honesta seria não exibir total nenhum até reservar, e isso é pior:
a pessoa marca duas meias e não vê o efeito antes de se comprometer.

O que impede a divergência de virar defeito de cobrança: a prévia **nunca** é enviada. `FR-019` já
manda ignorar total vindo do cliente. E `tests/meia.test.ts` compara a saída do espelho com uma
tabela de casos fixos — a mesma tabela que `test_precos.py` usa no back-end. Os dois lados
concordarem é verificado, não presumido.

---

## R7 — O tipo não entra no código assinado

**Decisão**: o código do QR continua sendo assinatura sobre `public_id` + `screening_id`. O tipo é
lido do banco **depois** da verificação.

**Rationale**: o Princípio III exige que a assinatura seja verificada antes de qualquer consulta —
e ela continua sendo. O tipo não é credencial: ele não decide entrada, decide se o operador pede
documento. Assiná-lo criaria duas verdades sobre o mesmo fato (a do código e a da coluna) e um
caminho novo de invalidação — um ingresso cujo tipo mudasse no banco passaria a ter código inválido.

**Consequência aceita**: quem forjasse um código não ganharia nada declarando-se meia, porque o
código forjado já é rejeitado antes de o tipo ser lido.

---

## R8 — O que o cartão pega da referência, e o que não pega

**Decisão**: pegar a **arquitetura de informação** (cabeçalho identificando o local da sessão, régua
separando, ações no topo à direita, horários como alvos compactos em grade). Não pegar cor,
tipografia, ícones, cantos, nem os elementos sem lastro no domínio.

**Rationale**: o desafio diz "não copie; use como ponto de partida", e o Princípio V proíbe saída
não editada. A distinção operacional que este projeto adota: **arranjo é vocabulário do domínio,
acabamento é assinatura**. Toda grade de cinema do mundo agrupa horários sob um cabeçalho de local —
isso não pertence a ninguém. O magenta, a Cabinet Grotesk, o ritmo de espaçamento e o preço no
horário são o que faz o cartão ser desta plataforma.

**O que fica de fora, com motivo** (FR-005): nome e endereço de cinema (não modelados), selo de
áudio (o TMDb não fornece por sessão), favoritar (recurso de conta inexistente), e a ação "Detalhes"
(a página do filme já tem abas Sobre e Trailers desde a 012 — um terceiro caminho para a mesma
informação seria duplicação de navegação).

---

## R9 — Os painéis são construídos à mão

**Decisão**: nenhuma biblioteca de modal. Um componente `Sobreposicao` resolve as quatro exigências
do FR-010/FR-014: fechar por `Esc`, fechar por controle visível, prender o foco enquanto aberto,
devolver o foco à origem.

**Rationale**: o projeto não tem biblioteca de UI, e trazer uma para dois painéis contradiz a
disciplina de tokens que a 006 estabeleceu — componentes de terceiro chegam com espaçamento, raio e
transição próprios, que é exatamente o que `tokens.test.ts` reprova.

`<dialog>` nativo foi considerado e **é a base**: ele já entrega foco preso e `Esc`. O componente
existe para padronizar a devolução de foco e a redação dos estados de espera e erro.

---

## Riscos residuais

| Risco | Probabilidade | Mitigação |
|---|---|---|
| A prévia do navegador divergir do servidor em algum preço | Baixa | Tabela de casos compartilhada entre `test_precos.py` e `meia.test.ts` |
| O teste de vazamento ser afrouxado em vez de atualizado | Média | `T-VAZAMENTO`: a permissão do tipo tem de vir com razão escrita dentro do teste |
| O cartão sair parecido demais com a referência | Média | R8 + a checagem anti-slop no fim, como na 011 |
| A P4 não caber no prazo | **Alta** | A P4 é a última e sai inteira. P1–P3 não dependem dela |
