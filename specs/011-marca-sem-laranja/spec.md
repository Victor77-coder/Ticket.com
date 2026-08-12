# Feature Specification: Marca sem Laranja — Cor, Tipografia de Marca e Logo

**Feature Branch**: `main` — sem branch própria, como nas 003–010

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Troca a linguagem cromática e cria marca gráfica, emendando a direção
da 006 sem reabrir comportamento."

> **Esta feature emenda a 006, e a emenda tem endereço.** O FR-020 daquela spec diz: *"A paleta DEVE
> permanecer escura com destaque laranja."* Esta feature revoga a segunda metade dessa frase e mantém
> a primeira. O contrato de checagem anti-slop da 006 tem um item chamado **"Laranja de projeção"**,
> e ele deixa de existir com esse nome.
>
> **A 006 é o motivo de esta feature ser barata.** Ela impôs que nenhum valor de cor ficasse fora dos
> tokens, e a disciplina segurou: hoje o laranja existe em **quatro declarações**, todas em um
> arquivo, e **doze arquivos** consomem apenas os nomes. Trocar a cor da marca inteira é trocar
> quatro valores. Se a 006 tivesse falhado, esta feature seria uma caçada a hexadecimais por doze
> arquivos, e o resultado seria uma tela ficando para trás.
>
> **Por isso o trabalho de verdade não é a troca — é a escolha.** O que esta feature entrega é uma
> decisão cromática defensável, um nome com tipografia própria e uma logo que deriva desse nome.
> A aplicação é consequência.
>
> **Nenhum comportamento é reaberto.** APIs, seed, fluxo de reserva, pagamento, emissão, validação e
> os quatro desfechos da portaria ficam exatamente como estão. Se um teste de comportamento quebrar,
> a mudança visual está errada — não o teste.

## O que a 006 fixou e continua valendo

Registrado para que a emenda seja cirúrgica em vez de uma reabertura:

| Da 006 | Nesta feature |
|---|---|
| Sala escura como base | **Mantido** |
| Disciplina de tokens — nenhum valor fora deles | **Mantido, e é o que torna isto viável** |
| Archivo variável na interface e no cartaz | **Mantido**, salvo decisão registrada em contrário |
| Ritmo, espaçamento, raios, durações | **Mantido** |
| Destaque **laranja** (FR-020) | **REVOGADO** — é a emenda |
| Item "Laranja de projeção" no contrato anti-slop | **REVOGADO** — substituído |
| Proibições anti-slop (roxo, creme+serifada, halo, pílula fina) | **Mantidas e ampliadas** |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconhecer de quem é o site (Priority: P1)

Alguém abre a home pela primeira vez. Em dois segundos sabe que aquilo tem dono — um nome com
desenho próprio, uma cor que é daquela marca e de mais nada na tela. Não parece um modelo pronto com
o logotipo trocado.

**Why this priority**: É a razão de a feature existir, e é o critério que o desafio avalia
explicitamente. Sem ela, o que se entrega é uma troca de tinta.

**Independent Test**: Mostrar a home a alguém que não conhece o projeto por dois segundos e pedir que
descreva a marca. A pessoa deve conseguir nomear o site e apontar a cor de ação.

**Acceptance Scenarios**:

1. **Given** a home carregada, **When** alguém a vê por dois segundos, **Then** identifica o nome do
   site sem procurar.
2. **Given** o cabeçalho recortado da imagem, **When** a primeira dobra é avaliada, **Then** ela
   ainda não parece um modelo genérico — a identidade sobrevive à remoção do logotipo.
3. **Given** qualquer tela do sistema, **When** ela é observada, **Then** a cor de ação é a mesma e
   é reconhecível como sendo daquela marca.
4. **Given** a marca exibida, **When** comparada ao restante da interface, **Then** o nome tem
   tratamento tipográfico próprio, distinto do texto comum.

---

### User Story 2 - Nenhum vestígio do laranja (Priority: P1)

A cor antiga não sobrevive em canto nenhum: nem em token, nem em componente, nem num vestígio de
cartaz que ninguém lembrava que existia.

**Why this priority**: Uma troca de identidade pela metade é pior que nenhuma — duas cores de marca
competindo é exatamente o que faz uma interface parecer montada por acidente.

**Independent Test**: Varrer o código do front-end inteiro pelos valores da cor antiga e obter zero
ocorrências; percorrer as dez superfícies e não encontrar nenhum elemento na cor anterior.

**Acceptance Scenarios**:

1. **Given** o código do front-end, **When** é varrido pelos valores da cor antiga, **Then** não há
   nenhuma ocorrência.
2. **Given** os nomes de token de destaque, **When** são inspecionados, **Then** continuam os
   mesmos — o que mudou foram os valores.
3. **Given** qualquer componente, **When** é inspecionado, **Then** não introduziu valor de cor
   próprio para acompanhar a mudança.
4. **Given** as superfícies que usam vestígio de destaque — substituto de cartaz e similares —
   **When** são observadas, **Then** acompanham a paleta nova.

---

### User Story 3 - A cor nova funciona como cor de trabalho (Priority: P1)

A cor não é só bonita na home: ela é o foco do teclado, o botão que conclui a compra, o assento
selecionado, o destaque na portaria. Em todos esses lugares ela é legível e cumpre a função.

**Why this priority**: A cor de destaque deste sistema carrega significado funcional em pelo menos
quatro lugares distintos. Uma escolha que funciona no cabeçalho e falha no assento selecionado
quebra a compra.

**Independent Test**: Percorrer as dez superfícies do baseline e conferir que a cor nova aparece com
contraste suficiente em cada papel que exercia — foco, ação principal, seleção, marca.

**Acceptance Scenarios**:

1. **Given** a cor nova sobre o fundo escuro, **When** o contraste é medido, **Then** atende ao
   mínimo exigido para texto e para elemento de interface.
2. **Given** texto sobre a cor nova, **When** o contraste é medido, **Then** também atende ao
   mínimo — a cor de texto sobre o destaque foi recalibrada, não herdada.
3. **Given** o indicador de foco de teclado, **When** percorre-se qualquer tela só pelo teclado,
   **Then** o foco permanece visível em todos os pontos.
4. **Given** o mapa de assentos, **When** um lugar é selecionado, **Then** ele se distingue dos
   demais **sem depender apenas de cor** — a forma continua carregando o estado.
5. **Given** a tela de portaria, **When** um desfecho é exibido, **Then** os quatro continuam
   distinguíveis sem depender apenas de cor.
6. **Given** o ingresso emitido, **When** é exibido em qualquer superfície, **Then** o fundo do
   código em QR **continua branco**.

---

### User Story 4 - O nome tem desenho, não só fonte (Priority: P1)

O nome do site aparece com uma marca gráfica ao lado — algo que deriva do próprio nome, não um ícone
de ingresso comprado de biblioteca. Em tela estreita, a marca continua reconhecível mesmo quando o
nome inteiro não cabe.

**Why this priority**: É o segundo entregável nomeado da feature. Um wordmark sozinho, ainda que bem
tipografado, não sobrevive ao teste da tela estreita nem ao do favicon.

**Independent Test**: Observar a marca em tela larga e em 320px, e conferir que nas duas ela é
reconhecível e coerente — sem wordmark e logo disputando atenção.

**Acceptance Scenarios**:

1. **Given** o cabeçalho em tela larga, **When** é observado, **Then** marca gráfica e nome formam
   um conjunto — nenhum compete com o outro.
2. **Given** uma tela de 320px, **When** o cabeçalho é observado, **Then** a marca continua
   reconhecível, ainda que em forma reduzida.
3. **Given** a marca gráfica, **When** alguém a descreve, **Then** ela remete ao nome do site, e
   não a um símbolo genérico de cinema.
4. **Given** a marca sobre o fundo escuro, **When** é observada, **Then** tem contraste suficiente
   sem precisar de contorno nem sombra.
5. **Given** um leitor de tela, **When** percorre a marca, **Then** ouve um rótulo coerente que
   nomeia o site.
6. **Given** um usuário de portaria, **When** aciona a marca, **Then** continua indo para a tela
   dele, e não para o catálogo — o destino por papel entregue na 010 é preservado.

---

### User Story 5 - Nada de comportamento mudou (Priority: P1)

Comprar, pagar, receber ingresso, compartilhar e validar continuam funcionando exatamente como
antes. A mudança é visual e só visual.

**Why this priority**: Uma feature de identidade que quebra a compra destrói mais valor do que
qualquer ganho estético. É também o que separa esta feature de uma reabertura da 006.

**Independent Test**: Rodar a suíte inteira de comportamento e conferir que nenhuma asserção de
regra de negócio precisou ser alterada.

**Acceptance Scenarios**:

1. **Given** a suíte de testes das features 001–010, **When** é executada, **Then** as asserções de
   comportamento passam sem alteração.
2. **Given** um teste que precise mudar, **When** a mudança é avaliada, **Then** ela é de seletor
   ou de estilo — nunca de regra de negócio.
3. **Given** o fluxo completo, **When** é percorrido ponta a ponta, **Then** comprar, pagar,
   receber, compartilhar e validar funcionam como antes.
4. **Given** os estados de erro e vazio de todas as telas, **When** são exibidos, **Then** continuam
   presentes e escritos para humanos.

---

### Edge Cases

- **Tela de 320px**: marca reduzida continua reconhecível; nenhuma superfície ganha rolagem lateral.
- **Arte de filme muito clara**: o véu de contraste continua garantindo leitura do título sobre ela.
- **Filme sem cartaz**: o substituto usa a paleta nova, não a antiga.
- **Assento selecionado ao lado de assento tomado**: distinguíveis em escala de cinza.
- **Quatro desfechos da portaria**: distinguíveis em escala de cinza.
- **Foco de teclado sobre superfície elevada**: continua visível.
- **Ingresso com QR sobre a paleta nova**: fundo do código permanece branco.
- **Movimento reduzido preferido pelo sistema**: nada que a feature introduza ignora essa
  preferência.
- **Fonte da marca indisponível**: o nome continua legível com a substituta, sem salto de layout que
  desloque o cabeçalho.
- **Impressão em preto e branco de um ingresso**: continua utilizável.

## Requirements *(mandatory)*

### A emenda ao que a 006 fixou

- **FR-001**: Esta feature **revoga** a exigência de destaque laranja da 006 e mantém a base escura.
  A revogação DEVE estar registrada, com o requisito exato que ela emenda.
- **FR-002**: O contrato de checagem anti-slop da 006 DEVE ganhar um sucessor em que o item de cor
  deixa de nomear o laranja e passa a nomear a cor nova, a tipografia de marca e a logo.
- **FR-003**: As proibições anti-slop existentes DEVEM ser mantidas e ampliadas com "qualquer
  vestígio da cor antiga".

### A cor

- **FR-004**: Nenhum valor da cor antiga pode permanecer no front-end — nem em token, nem em
  componente, nem em asset.
- **FR-005**: Os **nomes** dos tokens de destaque DEVEM ser preservados. O que muda são os valores.
- **FR-006**: Nenhum componente pode introduzir valor de cor próprio para acompanhar a mudança. A
  disciplina de tokens da 006 continua valendo integralmente.
- **FR-007**: A cor nova DEVE ser saturada o bastante para servir simultaneamente a **foco de
  teclado**, **ação principal**, **seleção** e **marca**.
- **FR-008**: A cor nova sobre o fundo escuro DEVE atingir o contraste mínimo de acessibilidade para
  texto e para elemento de interface.
- **FR-009**: A cor de texto **sobre** o destaque DEVE ser recalibrada para a cor nova, e atingir o
  mesmo mínimo. Herdá-la da paleta antiga é violação.
- **FR-010**: O vestígio de destaque — usado em substituto de cartaz e superfícies afins — DEVE
  acompanhar a paleta nova.
- **FR-011**: A cor nova NÃO PODE ser roxo, índigo ou violeta, nem o par creme com serifada
  terracota. Estão vetados por serem a assinatura visual do que o desafio chama de saída de
  ferramenta.

### A tipografia da marca

- **FR-012**: O nome do site DEVE ter tratamento tipográfico próprio, distinto do texto da interface.
- **FR-013**: A escolha DEVE ser **uma família própria para a marca** ou **um corte extremo da
  família existente que a interface nunca usa**. A segunda opção exige justificativa escrita.
- **FR-014**: A fonte da marca DEVE ter licença que permita uso comercial, e a licença DEVE estar
  documentada.
- **FR-015**: A fonte da marca DEVE ser servida pelo próprio domínio, sem requisição a terceiro em
  tempo de visita — mesma regra que a 006 já aplica à família da interface.
- **FR-016**: A tipografia da marca DEVE ser exposta como token e consumida **apenas** pela marca.
  Nenhum texto de interface pode usá-la.
- **FR-017**: A família da interface permanece a atual, salvo decisão registrada em contrário.
- **FR-018**: A troca de fonte NÃO PODE produzir salto de layout perceptível enquanto ela carrega.

### A logo

- **FR-019**: DEVE existir uma marca gráfica que **deriva do nome do site**.
- **FR-020**: A marca gráfica NÃO PODE ser um ícone genérico de ingresso, claquete, pipoca ou
  assento retirado de biblioteca.
- **FR-021**: Marca gráfica e nome DEVEM formar um conjunto — nenhum compete com o outro.
- **FR-022**: DEVE existir uma **variante compacta** para quando o nome inteiro não couber.
- **FR-023**: A marca DEVE ter contraste suficiente sobre o fundo escuro **sem** contorno, sombra ou
  halo.
- **FR-024**: A marca DEVE ter rótulo acessível coerente, que nomeie o site.
- **FR-025**: O **destino** da marca DEVE continuar respeitando o papel de quem a aciona, como a 010
  estabeleceu — a portaria vai para a tela dela, não para o catálogo.
- **FR-026**: A marca substitui a identidade textual atual. Não podem coexistir uma identidade
  antiga e uma nova.

### A aplicação

- **FR-027**: Todas as superfícies do sistema DEVEM usar a paleta nova: cabeçalho, home, filme,
  assentos, pagamento, meus ingressos, ingresso compartilhado, entrada e portaria.
- **FR-028**: Nenhuma superfície pode ficar para trás com a cor antiga.
- **FR-029**: O fundo do código em QR **continua branco**, em todas as superfícies. É exceção
  deliberada e não pode ser alterada por estética.
- **FR-030**: O mapa de assentos DEVE continuar distinguindo disponível, selecionado, tomado e
  indisponível **sem depender apenas de cor**.
- **FR-031**: Os quatro desfechos da portaria DEVEM continuar distinguíveis **sem depender apenas de
  cor**.
- **FR-032**: O foco de teclado DEVE permanecer visível em todas as telas.
- **FR-033**: Os véus de contraste sobre a arte do filme podem acompanhar a base, desde que o
  contraste do texto sobre a arte não piore.
- **FR-034**: Nenhuma superfície pode ganhar rolagem lateral em tela estreita.

### Preservação de comportamento

- **FR-035**: Nenhuma regra de negócio pode ser alterada por esta feature.
- **FR-036**: Nenhuma asserção de comportamento das features 001–010 pode ser removida ou
  enfraquecida. Ajuste de seletor ou de estilo é aceitável quando inevitável; afrouxar verificação
  não é.
- **FR-037**: Nenhum contrato de API, seed, limite de carrossel, regra de trilha ou etapa de fluxo
  pode mudar.
- **FR-038**: A verificação criptográfica do ingresso e os quatro desfechos da portaria permanecem
  intactos.
- **FR-039**: Estados de erro e vazio DEVEM continuar presentes e escritos para humanos em todas as
  telas.

### O registro da decisão

- **FR-040**: A direção cromática escolhida DEVE ser registrada junto de **duas a três direções
  rejeitadas**, incluindo obrigatoriamente por que não manter o laranja e por que não a paleta que
  o desafio associa a saída de ferramenta.
- **FR-041**: DEVE existir um mapa de **onde o destaque aparece hoje** — assento, ação principal,
  foco, portaria e demais papéis —, para que a escolha seja avaliada contra todos os usos e não só
  contra o cabeçalho.
- **FR-042**: O conceito da logo DEVE ser registrado: como ela deriva do nome, e quais variantes
  existem.
- **FR-043**: O README DEVE registrar as fontes usadas, suas licenças, o que foi feito com e sem
  auxílio de IA, e a nota explícita de que esta feature emenda o requisito de paleta da 006.
- **FR-044**: Nenhuma superfície pode conter texto de preenchimento, marcador de posição ou seção
  "em breve".

### Key Entities

- **Cor de destaque** *(existente, revalorada)*: o papel visual que carrega ação, foco, seleção e
  marca. Os nomes permanecem; os valores mudam. É o único ponto do sistema onde a cor da marca é
  definida.
- **Tipografia da marca** *(nova)*: a família — ou o corte extremo — reservada ao nome do site.
  Existe como token e tem exatamente um consumidor.
- **Marca gráfica** *(nova)*: o desenho que deriva do nome, com variante completa e compacta.
- **Contrato de checagem anti-slop** *(existente, sucedido)*: o procedimento repetível que avalia a
  primeira dobra com o cabeçalho recortado. Ganha uma versão em que o item de cor deixa de nomear o
  laranja.

## Success Criteria *(mandatory)*

- **SC-001**: Uma varredura no front-end pelos valores da cor antiga retorna **zero** ocorrências.
- **SC-002**: Os nomes dos tokens de destaque permanecem idênticos aos de antes da feature.
- **SC-003**: Nenhum componente contém valor de cor fora dos tokens — verificável por varredura.
- **SC-004**: A cor nova sobre o fundo escuro atinge o contraste mínimo exigido, e o texto sobre a
  cor nova também — os dois medidos, não estimados.
- **SC-005**: As **dez** superfícies do sistema exibem a paleta nova, sem nenhuma ficando para trás.
- **SC-006**: O nome do site é exibido com tipografia própria em 100% das superfícies onde aparece.
- **SC-007**: A marca gráfica é reconhecível em 320px de largura.
- **SC-008**: Alguém que não conhece o projeto nomeia o site em até **2 segundos** olhando a home.
- **SC-009**: Com o cabeçalho recortado, a primeira dobra é aprovada no contrato de checagem
  anti-slop sucessor — todos os itens obrigatórios presentes, nenhum proibido presente.
- **SC-010**: Os quatro estados do mapa de assentos permanecem distinguíveis em escala de cinza.
- **SC-011**: Os quatro desfechos da portaria permanecem distinguíveis em escala de cinza.
- **SC-012**: O foco de teclado permanece visível em todas as telas percorridas só pelo teclado.
- **SC-013**: O fundo do código em QR permanece branco em todas as superfícies.
- **SC-014**: Nenhuma superfície apresenta rolagem lateral em 320px.
- **SC-015**: A suíte de comportamento das features 001–010 passa sem que nenhuma asserção de regra
  de negócio tenha sido alterada.
- **SC-016**: A licença de cada fonte usada está documentada e permite uso comercial.

## Assumptions

- **A base escura permanece.** Assume-se que a emenda é cromática no destaque, não na fundação. A
  sala escura é o que faz a arte do filme ser a fonte de luz da composição, e trocá-la seria refazer
  a 006 em vez de emendá-la.

- **Os nomes de token não mudam, e isso é o que torna a feature barata.** Assume-se que trocar
  valores em um arquivo é preferível a renomear tokens em doze. Renomear obrigaria a tocar cada
  arquivo consumidor, multiplicando a chance de uma superfície ficar para trás — que é exatamente o
  defeito que FR-028 proíbe.

- **A interface continua na família atual.** Assume-se que a tipografia da interface não é o
  problema que esta feature resolve. A 006 escolheu uma família variável que serve interface e
  cartaz do mesmo arquivo, e essa decisão continua boa. O que faltava era o **nome** ter desenho.

- **A marca gráfica é desenhada, não licenciada.** Assume-se que ela deriva do nome do site, o que a
  torna específica por construção. Um símbolo de biblioteca seria genérico por definição — e é
  justamente o que FR-020 veta.

- **A avaliação de "parece template" continua sendo humana, com procedimento escrito.** Assume-se
  que esse julgamento não é automatizável, e que a resposta correta é o que a 006 já fazia: um
  procedimento repetível, com listas do que precisa e do que não pode estar presente, para que
  "não passou" venha com motivo.

- **Testes visuais automatizados de aparência não entram.** Assume-se que comparação de imagem não é
  proporcional ao escopo: ela travaria qualquer ajuste de estilo futuro e não responde à pergunta
  que importa, que é se a tela tem identidade. Verificação automatizada cobre o que é objetivo —
  ausência da cor antiga, contraste, ausência de valores fora dos tokens.

- **A troca não altera o significado de nenhum estado.** Assume-se que a cor nova ocupa exatamente
  os papéis que a antiga ocupava, sem redistribuir significado. Aproveitar a feature para mudar o
  que a cor comunica misturaria duas decisões e tornaria qualquer regressão difícil de atribuir.

- **Favicon e ícones de aplicativo acompanham a marca.** Assume-se que a variante compacta serve a
  esse uso, já que ela existe por FR-022.

### Escopo excluído

Qualquer alteração de comportamento · APIs, seed, limites e regras de trilha · fluxo de reserva,
pagamento, emissão, compartilhamento e validação · fundo do código em QR · verificação criptográfica
do ingresso · troca da família tipográfica da interface (salvo decisão registrada) · redistribuição
do significado das cores de estado · testes visuais automatizados por comparação de imagem ·
animação ou efeito novo · biblioteca de componentes ou de efeitos pronta · tema claro.

### Dependências

- Disciplina de tokens, ritmo e contrato anti-slop (`006-visual-identity`) — **é a feature emendada**
- Cabeçalho e identidade textual (`002-site-header-navigation`)
- Mapa de assentos com estados não dependentes de cor (`007-seat-selection`)
- Ingresso com QR e fundo branco obrigatório (`008-payment-ticket-issuance`)
- Página compartilhada pública (`009-my-tickets-sharing`)
- Destino da marca por papel e os quatro desfechos (`010-gate-validation`)
