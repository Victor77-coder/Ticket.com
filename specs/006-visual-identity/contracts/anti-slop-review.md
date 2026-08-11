# Contract — Checagem Anti-Slop da Primeira Dobra

**Feature**: `006-visual-identity` | **Date**: 2026-08-11

O SC-003 é o **único** critério desta feature que depende de julgamento humano. Todo o resto é
varredura.

Um critério subjetivo sem regra escrita é o mesmo que critério nenhum — por isso este documento
existe: para que a revisão seja repetível por outra pessoa, e para que "não passou" venha com
motivo.

---

## O procedimento

1. Abrir a home em 1440×900, com o catálogo sincronizado e semeado.
2. Capturar a **primeira dobra** — o que aparece sem rolar.
3. **Recortar o cabeçalho inteiro**, incluindo o nome ticket.com.
4. Aplicar as listas abaixo à imagem restante.

O recorte é o ponto do exercício: com o logotipo, qualquer interface parece ter identidade.

---

## Precisa estar presente

Os quatro, sem exceção:

- [ ] **Sala escura.** O fundo é escuro o bastante para que a arte do filme seja a fonte de luz da
      composição.
- [ ] **Laranja de projeção.** O destaque aparece em ao menos um elemento de ação, e é a única cor
      saturada da tela.
- [ ] **Tipografia de cartaz.** O título do filme é largo e pesado o suficiente para ler como
      cartaz, não como cabeçalho de aplicação.
- [ ] **Hierarquia inequívoca.** Em três segundos dá para dizer qual é o filme, o que ele é, e
      qual a ação principal.

## Não pode estar presente

Qualquer um reprova:

- [ ] Cartão decorativo, chip, selo de promoção ou emblema sobre a arte
- [ ] Gradiente colorido que não seja o véu de contraste
- [ ] Brilho, sombra colorida ou halo em volta de texto ou botão
- [ ] Botão em pílula com borda fina e sem peso — o "pill" genérico
- [ ] Ícone de biblioteca reconhecível fora do estilo do resto
- [ ] Roxo, azul-violeta, creme com serifada terracota
- [ ] Texto de preenchimento, marcador de posição ou "em breve"
- [ ] Retângulo cinza uniforme onde deveria haver conteúdo

---

## A pergunta final

> **Se esta captura aparecesse numa galeria ao lado de cinco catálogos de streaming, dava para
> apontar qual é o nosso?**

Se a resposta for "não", a checagem falhou — mesmo com todos os itens acima marcados. As listas
existem para dar linguagem ao julgamento, não para substituí-lo.

---

## Quando falha

Registrar **o que** falhou e **por quê**, e tratar como tarefa da feature. Uma checagem que falha
e não gera correção é teatro.

Se a correção exigir mudar comportamento, contrato ou asserção de teste, **ela está fora do
escopo** — a feature declara isso em FR-026 a FR-030. O caminho certo é registrar como achado
para uma feature futura, não alargar esta.

---

## O que esta checagem NÃO avalia

- Gosto pessoal por uma fonte ou por um tom de laranja — a paleta está congelada por FR-020 e a
  tipografia foi decidida pelo usuário.
- A página do filme, a busca, a entrada — o SC-003 é sobre a **primeira dobra da home**, que é o
  que um avaliador vê antes de qualquer outra coisa.
- Desempenho, acessibilidade ou comportamento — todos têm verificação própria e objetiva.

---

# Resultado — 2026-08-11

Captura da primeira dobra em 1440×900 com o cabeçalho recortado, avaliada em 2026-08-11.

> A imagem não foi versionada. Para refazer a checagem, capturar de novo seguindo o procedimento
> acima — o resultado abaixo é o registro do que foi visto, não a evidência em si.

## Precisa estar presente — 4 de 4

- [x] **Sala escura** — a arte do filme é a fonte de luz da composição; o resto recua.
- [x] **Laranja de projeção** — presente em "Ver ingressos" e no indicador ativo, e é a única cor
      saturada da tela.
- [x] **Tipografia de cartaz** — "A ODISSEIA" saiu claramente expandido e pesado. O eixo `wdth`
      pegou; era o único ponto onde a teoria podia não virar prática.
- [x] **Hierarquia inequívoca** — em três segundos: qual filme, o que é, e qual a ação principal.

## Não pode estar presente — 1 reprovação

- [x] **Botão em pílula com borda fina e sem peso** — o botão **Trailer** é exatamente o padrão
      que esta lista proíbe: contorno, sem preenchimento, cantos totalmente arredondados.

Os demais itens da lista passaram: sem cartão decorativo, sem gradiente colorido além do véu, sem
brilho, sem ícone de biblioteca, sem roxo ou creme, sem placeholder, sem retângulo cinza.

## Achado fora das listas

- **As setas do carrossel mantiveram o círculo com borda.** A R7 removeu a moldura das setas das
  **trilhas** e a implementação seguiu a R7 ao pé da letra — mas as setas que aparecem na primeira
  dobra são as do **carrossel**, que ficaram como estavam. A própria R7 chama esse círculo de "o
  traço mais reconhecível de carrossel de catálogo genérico".

  É inconsistência da implementação, não da decisão: a regra estava certa e foi aplicada em metade
  dos lugares.

## A pergunta final

> Numa galeria ao lado de cinco catálogos de streaming, dava para apontar qual é o nosso?

**Sim** — a tipografia expandida e o laranja sobre a sala escura carregam a identidade sozinhos.

Mas a checagem **reprova**: dois elementos da primeira dobra ainda são o vocabulário genérico que
a feature existe para eliminar, e um deles está literalmente na lista de proibidos.

## Correções

| # | Achado | Escopo |
|---|---|---|
| 1 | Setas do carrossel com círculo e borda | **Dentro** da 006 — completa a R7 |
| 2 | Botão Trailer em pílula contornada | **Dentro** da 006 — item da lista de proibidos |
| 3 | Sinopse cortada no meio da palavra ("com seres míticos, c…") | **Fora** — bug pré-existente da 001, ver abaixo |

O terceiro achado não é visual: `synopsis_short` usa corte por **caractere** onde o próprio
comentário do código promete corte "na fronteira de palavra". O defeito existe desde a `001` e só
ficou visível agora, com uma sinopse real longa. Corrigi-lo muda conteúdo servido, não estilo —
por isso vai como correção de defeito, não como parte desta feature.
