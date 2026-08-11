# Phase 0 — Research: Ajuste da Vitrine

**Feature**: `005-seed-and-carousel-tuning` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado. Nenhum `NEEDS CLARIFICATION`
permanece aberto ao fim desta fase.

---

## R1. Como garantir três filmes específicos no carrossel

**Decision**: **ordenar a lista do seed**, colocando A Odisseia, Homem-Aranha e Minions nas três
primeiras posições. Nenhuma lógica de curadoria entra no código de produto.

**Rationale**: o `seed_demo` já agenda as sessões pela posição do filme na lista:

```
starts_at = agora + offset + 30min × índice
```

Quem está em primeiro tem a sessão mais próxima. E o carrossel ordena por `next_screening_at`
ascendente. Os dois mecanismos já existem e já se encaixam — o que falta é só decidir a ordem.

Isso mantém a regra do carrossel intacta: continua sendo "os N com sessão mais próxima", sem
saber que existe curadoria. Toda a escolha vive no cenário de demonstração, que é onde ela deve
viver.

**Alternatives considered**:

- **Campo `is_featured` em `Movie`** — migração, novo campo a manter em sincronia com o TMDb, e
  uma segunda regra de ordenação no seletor. Tudo isso para representar algo que a ordem do seed
  já resolve.
- **Lista fixa de slugs no seletor do carrossel** — colocaria dados de demonstração dentro do
  código de produto. O carrossel passaria a conhecer nomes de filmes, o que é exatamente o tipo
  de acoplamento que fica esquecido e vira bug em produção.

**Fragilidade registrada**: a ordem da lista é o mecanismo, e isso não é óbvio lendo
`_pick_movies`. Uma refatoração inocente — ordenar alfabeticamente, por exemplo — mudaria a
vitrine sem que ninguém percebesse. Exige comentário no código e teste que fixe a ordem.

---

## R2. Como encontrar os filmes pelo nome

**Decision**: `title__unaccent__icontains`, com desempate determinístico por `-release_date, pk`
e o título escolhido impresso na saída do comando.

**Rationale**:

- O pedido cita fragmentos ("homem aranha", "minions"), não títulos exatos. O catálogo tem
  *Homem-Aranha: Um Novo Dia* e *Minions & Monstros*. `icontains` cobre o sufixo; `unaccent`
  cobre o hífen ausente e a diferença de acento.
- A extensão `unaccent` já está instalada desde a busca do cabeçalho (feature 002) — nenhuma
  dependência nem migração nova.
- O desempate é obrigatório: sem ele, dois filmes casando com "minions" produziriam vitrines
  diferentes entre execuções, e o SC-005 cairia de forma intermitente.
- Imprimir o escolhido (FR-012) é o que torna o resultado conferível sem abrir o banco.

**Alternatives considered**:

- **Fixar por `tmdb_id`** — imune a renomeação e sem ambiguidade, mas ilegível: uma lista de
  números não diz a ninguém quais filmes estão na vitrine, e o pedido do usuário foi em nomes.
- **Fixar por slug** — o slug é derivado do título na primeira sincronização e não muda depois,
  então seria estável. Mas depende de o filme já ter sido importado com aquele título exato, o
  que é a mesma fragilidade com menos legibilidade.
- **Casamento exato de título** — quebraria com "homem aranha" contra "Homem-Aranha: Um Novo Dia".

---

## R3. O que acontece quando um filme nomeado não existe

**Decision**: o seed informa quais faltaram, na saída, e conclui com os demais. Nunca falha nem
interrompe.

**Rationale**: FR-011. O catálogo externo pode renomear um filme ou parar de listá-lo, e o seed
só enxerga o que a sincronização trouxe. Um comando que quebra porque um título mudou é pior do
que uma vitrine com um filme a menos — quem está montando o ambiente perde tempo com um erro que
não é dele.

A degradação também cobre o caso mais comum na prática: rodar `seed_demo` antes de `sync_tmdb`,
com o catálogo vazio.

---

## R4. Quantos filmes o seed coloca à venda

**Decision**: **12** — os 4 nomeados mais 8 escolhidos pelo critério que já existe.

**Rationale**: o pedido foi "aumente o seed", sem número. Doze resolve três coisas ao mesmo tempo:

- A trilha **Em cartaz** ganha substância — 12 filmes fazem uma faixa que rola, contra 5 que
  cabem na tela.
- A trilha **Em alta** deixa de ser quase idêntica a Em cartaz. Três dos quatro nomeados já estão
  marcados como em alta no catálogo, e a trilha exige sessão desde a emenda da feature 004.
- O carrossel de 3 vira claramente um **recorte**, não a lista inteira. Com 5 filmes à venda e
  carrossel de 3, a diferença quase não aparece.

Também satisfaz SC-004 com folga: 12 é o quádruplo de 3, e o critério pede o dobro.

**Consequência assumida**: o seed passa de ~15 para ~36 sessões. Irrelevante em tempo de
execução, e ainda cabe nas duas salas sem colidir com `UNIQUE(sala, horário)` — o deslocamento de
30 minutos por índice garante horários distintos.

---

## R5. Onde mudar o limite do carrossel

**Decision**: a constante `HIGHLIGHTS_LIMIT` em `selectors.py`, de 5 para 3.

**Rationale**: é o único lugar. `get_highlighted_movies` usa a constante como default, e a
extração feita na feature 004 deixou a regra de elegibilidade compartilhada com a trilha Em
cartaz — que **não** tem limite e portanto não é afetada.

**Consequência conhecida**: dois testes fixam o número 5 e vão falhar. Atualizá-los é parte da
mudança, não regressão — eles codificavam a regra antiga. O commit precisa dizer isso, senão
parece que a suíte quebrou.

**Alternatives considered**: tornar o limite configurável por variável de ambiente. Descartado —
generalização sem demanda, e um número de destaque que muda em tempo de execução é mais difícil
de testar do que de ajustar.

---

## R6. Estratégia de testes

O `seed_demo` nunca teve teste próprio: era verificado indiretamente, rodando o comando. Com
regras de seleção e de ordem, passa a merecer.

| Alvo | Tipo | Por quê |
|---|---|---|
| Os quatro nomeados recebem sessão publicada e futura | back-end | FR-004 |
| A Odisseia, Homem-Aranha e Minions são os três de sessão mais próxima | back-end | FR-005, SC-002 — é o mecanismo inteiro da feature |
| Moana tem sessão e **não** está entre os três primeiros | back-end | FR-006, SC-003 |
| O seed coloca à venda mais filmes do que os quatro nomeados | back-end | FR-007, SC-004 |
| Filme nomeado ausente: avisa e conclui | back-end | FR-011, SC-006 — a degradação que impede o comando de quebrar |
| Duas execuções produzem a mesma vitrine | back-end | FR-013, SC-005 |
| O carrossel devolve no máximo 3 | back-end | FR-001, SC-001 |

**Rationale**: concentra no mecanismo (a ordem) e na degradação (a ausência), que são as duas
coisas que quebram silenciosamente. O resto do carrossel já tem cobertura da feature 001 e não
precisa ser reescrito por causa do número.
