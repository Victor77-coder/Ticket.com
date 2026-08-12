# Contrato — `CASA_DO_PAPEL` com dois fatos

Este contrato governa `frontend/lib/papeis.ts` e `frontend/middleware.ts`. É pequeno e é onde a
feature quebra mais fácil: o middleware **nega por padrão**, então registrar o organizador errado
não dá erro — dá um organizador trancado fora do catálogo, e a suíte atual passaria.

## O que muda

O registro de cada papel deixa de ter três campos e passa a ter quatro:

```ts
Partial<Record<Papel, { href: string; rotulo: string; pousa: boolean; telaUnica: boolean }>>
```

| Papel | `href` | `rotulo` | `pousa` | `telaUnica` |
|---|---|---|---|---|
| `customer` | `/meus-ingressos` | Meus ingressos | `false` | `false` |
| `gate` | `/portaria` | Validar ingressos | `true` | `true` |
| `organizer` | `/programacao` | **Programação** | `true` | `false` |

## Por que dois campos, e não um

O docstring atual afirma que `telaUnica` é "UM fato com TRÊS consequências, e elas andam juntas de
propósito". Isso era verdade enquanto a portaria era o único papel confinado. **O organizador é o
contraexemplo que divide a afirmação**:

| Fato | Portaria | Organizador |
|---|---|---|
| pousa na tela dele ao entrar | sim | **sim** |
| não alcança nenhuma outra página | sim | **não** |
| o cabeçalho não oferece o que ele não pode usar | sim | **não** |

O organizador **precisa** do catálogo público: é ali que ele confere que a sessão que publicou
apareceu à venda (FR-004). O segundo e o terceiro fatos continuam ligados entre si — só o primeiro
se destacou.

**A tabela continua UMA.** O que o docstring protege é ter um lugar só onde o menu da conta e o
destino pós-entrada leem a mesma verdade. Isso não muda; muda o número de colunas.

## Comportamento das funções

| Função | Lê | Muda? |
|---|---|---|
| `destinoAposEntrada(papel, retorno)` | `pousa` | **Sim** — antes lia `telaUnica` |
| `temTelaUnica(papel)` | `telaUnica` | Não |
| `devolverParaCasa(papel, caminho)` | `telaUnica` | Não |

**Invariante que não pode ser quebrada**: `devolverParaCasa("organizer", <qualquer caminho>)`
devolve `null`. O middleware continua confinando **apenas** quem tem `telaUnica: true`. Se um dia
`devolverParaCasa` passar a consultar `pousa`, o organizador perde a home e a portaria não muda —
o sintoma aparece longe da causa.

**Invariante preservada**: um destino pedido explicitamente continua vencendo a casa do papel.
`destinoAposEntrada` só consulta a tabela quando `caminhoDeRetorno === "/"`, que é o que
`caminhoDeRetornoSeguro` devolve para "não houve pedido". Um organizador conduzido à entrada ao
tentar abrir `/filmes/duna-parte-dois` volta para lá, não para o painel (FR-003, US1 cenário 2).

## Os testes que mudam de afirmação

Estes dois existem hoje afirmando o contrário do que a feature entrega. Eles são **atualizados**,
nunca removidos (FR-005) — apagá-los deixaria a regra nova sem prova.

**`frontend/tests/auth.test.tsx:236`**

```
"o organizador não é bloqueado — ele ainda não tem tela própria"
  devolverParaCasa("organizer", "/") === null      ← CONTINUA VERDADE
  temTelaUnica("organizer") === false              ← CONTINUA VERDADE
```

Só o **nome** muda, para deixar de dizer "ainda não tem tela própria". As duas asserções
permanecem, e passam a valer mais: agora ele tem tela e mesmo assim não é bloqueado.

**`frontend/tests/auth.test.tsx:294`**

```
"não oferece destino de trabalho ao organizador, que ainda não tem painel"
  getAllByRole("menuitem") tem 1 item (só "Sair")   ← DEIXA DE SER VERDADE
```

Vira o inverso: o organizador entra na lista parametrizada que já cobre cliente e portaria —

```
["customer",  "Meus ingressos",    "/meus-ingressos"],
["gate",      "Validar ingressos", "/portaria"],
["organizer", "Programação",       "/programacao"],
```

O comentário daquele bloco ("um item que leva a uma recusa por papel é pior do que item nenhum")
sai, porque a premissa dele deixou de valer — o destino agora existe e aceita o organizador.

## Testes novos exigidos

1. `destinoAposEntrada("organizer", "/") === "/programacao"` — o pouso (FR-003).
2. `destinoAposEntrada("organizer", "/filmes/x") === "/filmes/x"` — o destino pedido vence.
3. `destinoAposEntrada("customer", "/") === "/"` — o cliente **não** regrediu para "Meus ingressos"
   ao ganharmos o campo `pousa`. É a regressão mais provável desta mudança: um cliente novo
   aterrissaria no estado vazio em vez do catálogo.
4. `devolverParaCasa("organizer", …)` devolve `null` para a home, um filme, uma busca e
   `/meus-ingressos` — o organizador circula (FR-004).
5. `devolverParaCasa("gate", …)` continua devolvendo `/portaria` para tudo — a portaria não foi
   afetada pela mudança de forma da tabela.

## Proibições

- **Não** acrescentar `/programacao` a uma lista de páginas permitidas ou proibidas no middleware.
  A negação por padrão é o que faz a página criada amanhã nascer coberta; uma lista esquece.
- **Não** usar o middleware para negar `/programacao` a cliente e portaria. Ele é produto, não
  segurança (o próprio arquivo diz isso). A recusa é o `403` do Django, apresentado pela página.
- **Não** guardar o papel em cookie legível pelo navegador para evitar a consulta do middleware. É
  a otimização já avaliada e rejeitada por criar um segundo lugar para a verdade morar.
