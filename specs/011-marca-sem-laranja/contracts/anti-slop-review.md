# Contract — Checagem Anti-Slop da Primeira Dobra *(sucessor)*

**Feature**: `011-marca-sem-laranja` | **Date**: 2026-08-12

> **Este documento SUBSTITUI
> [`specs/006-visual-identity/contracts/anti-slop-review.md`](../../006-visual-identity/contracts/anti-slop-review.md).**
>
> O original permanece onde está, marcado como sucedido. Não foi editado no lugar de propósito: ele é
> o registro de que a paleta um dia foi outra, e o Princípio VI pede rastro, não estado final.
>
> **O que mudou**: o item **"Laranja de projeção"** dá lugar a **"Neon de fachada"**. Entram dois
> itens obrigatórios novos — tipografia de marca e marca gráfica —, porque a 011 promete os dois. A
> lista de proibições ganha "qualquer vestígio da cor antiga". Todo o resto do procedimento é
> idêntico, e continua idêntico por escolha: ele funcionava.

O SC-009 é o **único** critério desta feature que depende de julgamento humano. Todo o resto é
varredura ou medição — ver [`contraste.md`](./contraste.md).

Um critério subjetivo sem regra escrita é o mesmo que critério nenhum. Por isso este documento
existe: para que a revisão seja repetível por outra pessoa, e para que "não passou" venha com motivo.

---

## O procedimento

1. Abrir a home em 1440×900, com o catálogo sincronizado e semeado.
2. Capturar a **primeira dobra** — o que aparece sem rolar.
3. **Recortar o cabeçalho inteiro**, incluindo a marca.
4. Aplicar as listas abaixo à imagem restante.

O recorte é o ponto do exercício: com o logotipo, qualquer interface parece ter identidade.

**Depois**, repetir uma vez **sem** recortar, só para os dois itens de marca — eles vivem no
cabeçalho e não teriam como aparecer na imagem recortada.

---

## Precisa estar presente

### Na imagem com o cabeçalho recortado

Os quatro, sem exceção:

- [ ] **Sala escura.** O fundo é escuro o bastante para que a arte do filme seja a fonte de luz da
      composição.
- [ ] **Neon de fachada.** O destaque aparece em ao menos um elemento de ação, e é a única cor
      saturada da tela.
- [ ] **Tipografia de cartaz.** O título do filme é largo e pesado o suficiente para ler como
      cartaz, não como cabeçalho de aplicação.
- [ ] **Hierarquia inequívoca.** Em três segundos dá para dizer qual é o filme, o que ele é, e qual
      a ação principal.

### Na imagem com o cabeçalho *(itens novos da 011)*

- [ ] **Tipografia de marca.** O nome do site é visivelmente de outra família que o texto da
      interface — não é o mesmo tipo em outro peso.
- [ ] **Marca gráfica.** Existe um desenho ao lado do nome, ele deriva do nome, e não é um símbolo
      de cinema que serviria a qualquer concorrente.

## Não pode estar presente

Qualquer um reprova:

- [ ] Cartão decorativo, chip, selo de promoção ou emblema sobre a arte
- [ ] Gradiente colorido que não seja o véu de contraste
- [ ] Brilho, sombra colorida ou halo em volta de texto, botão **ou da marca**
- [ ] Botão em pílula com borda fina e sem peso — o "pill" genérico
- [ ] Ícone de biblioteca reconhecível fora do estilo do resto
- [ ] Roxo, azul-violeta, creme com serifada terracota
- [ ] **Qualquer vestígio da cor antiga** — um respingo laranja num sistema magenta *(novo na 011)*
- [ ] **Duas identidades convivendo** — marca nova e resto de identidade antiga na mesma tela
      *(novo na 011)*
- [ ] Texto de preenchimento, marcador de posição ou "em breve"
- [ ] Retângulo cinza uniforme onde deveria haver conteúdo

---

## As duas perguntas finais

> **1. Se esta captura aparecesse numa galeria ao lado de cinco catálogos de streaming, dava para
> apontar qual é o nosso?**

> **2. Mostrando a home a alguém por dois segundos, essa pessoa consegue dizer o nome do site?**

Se qualquer resposta for "não", a checagem falhou — mesmo com todos os itens acima marcados. As
listas existem para dar linguagem ao julgamento, não para substituí-lo.

A segunda pergunta é nova na 011, e é o SC-008. Ela não é redundante com a primeira: a primeira
avalia se a interface tem **direção de arte**; a segunda, se a marca **comunica**. Uma tela pode ter
personalidade e ainda assim não dizer de quem é.

---

## Quando falha

Registrar **o que** falhou e **por quê**, e tratar como tarefa da feature. Uma checagem que falha e
não gera correção é teatro.

Se a correção exigir mudar comportamento, contrato ou asserção de regra de negócio, **ela está fora
do escopo** — a 011 declara isso em FR-035 a FR-039. O caminho certo é registrar como achado para uma
feature futura, não alargar esta.

---

## O que esta checagem NÃO avalia

- **Gosto pessoal pela cor ou pela fonte.** As duas foram decididas por eliminação e estão
  registradas com as alternativas e a medida que as descartou (research.md, R1 e R6). Discordar delas
  é assunto de uma emenda, como esta feature foi para a 006 — não de uma reprovação aqui.
- **Contraste, distância de estado ou ausência da cor antiga.** Tudo isso é medido, não julgado, e
  tem contrato próprio em [`contraste.md`](./contraste.md).
- **A página do filme, a busca, a entrada.** O critério é sobre a **primeira dobra da home**, que é o
  que um avaliador vê antes de qualquer outra coisa. As demais superfícies têm conferência própria,
  objetiva, no quickstart.
- **Desempenho, acessibilidade ou comportamento** — todos têm verificação própria.

---

# Resultado — 2026-08-12

Captura da primeira dobra em 1440×900, com o catálogo sincronizado e semeado, avaliada em 2026-08-12.

> As imagens não foram versionadas. Para refazer, capturar de novo seguindo o procedimento acima — o
> registro abaixo é o que foi visto, não a evidência em si.

## Com o cabeçalho recortado

- [x] **Sala escura** — o fundo some atrás da arte de *A Odisseia*, que é a fonte de luz da
      composição.
- [x] **Neon de fachada** — presente em "Ver ingressos" e no indicador ativo do carrossel, e é a
      única cor saturada da tela. As artes dos cartazes são imagens, não paleta.
- [x] **Tipografia de cartaz** — "A Odisseia" sai expandido e pesado, lendo como cartaz e não como
      cabeçalho de aplicação.
- [x] **Hierarquia inequívoca** — em três segundos: o filme, que é aventura de 2h52 com classificação
      14, e que a ação é ver ingressos.

Nenhum item proibido presente. Em particular: **nenhum vestígio da cor antiga** e **nenhuma
identidade dupla** — os dois itens que a 011 acrescentou à lista.

## Com o cabeçalho

- [x] **Tipografia de marca** — o nome sai em Cabinet Grotesk, visivelmente de outra família que o
      Archivo do restante da interface.
- [x] **Marca gráfica** — o `t` com o ponto do `.com`. Deriva do nome, e não é um símbolo de cinema
      que serviria a qualquer concorrente.

Em 320px a variante compacta aparece sozinha e continua reconhecível.

## As duas perguntas finais

**1. Numa galeria ao lado de cinco catálogos de streaming, dá para apontar qual é o nosso?**

**Sim — e a ressalva importa mais que o "sim".** O que distingue é a **cor**: magenta é incomum no
segmento, onde os concorrentes ocupam vermelho, azul e roxo. A tipografia expandida do título ajuda.

Mas **a composição é convencional para o gênero**: arte em tela cheia, título grande à esquerda,
sinopse curta, dois botões, trilha logo abaixo. Se a cor fosse trocada por vermelho, a captura
passaria por qualquer catálogo. A identidade está carregada quase inteiramente pela paleta e pela
tipografia — não pelo layout.

Isso **não reprova** esta feature, cujo escopo é cor, tipografia e marca. Fica registrado como
**achado para uma feature futura**: a composição da primeira dobra é o que ainda não tem autoria.
Alargar a 011 para mexer em layout seria exatamente o que o contrato proíbe em "Quando falha".

**2. Mostrando a home por dois segundos, a pessoa diz o nome do site?**

**Sim.** Marca e nome ficam no canto superior esquerdo, na primeira posição de leitura, com o desenho
puxando o olho antes da palavra.

## Veredito

**Aprovada**, com o achado da pergunta 1 registrado para uma feature de composição.
