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
