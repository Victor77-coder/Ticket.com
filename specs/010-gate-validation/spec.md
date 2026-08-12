# Feature Specification: Validação de Ingressos na Portaria

**Feature Branch**: `main` — sem branch própria, como nas 003–009

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Validação de ingressos na portaria — câmera, digitação manual e os
quatro desfechos."

> **É a etapa 5 da ordem de construção obrigatória, e é ela que fecha o fluxo.** A constitution
> lista "tela de portaria com câmera, digitação manual e os quatro desfechos de validação" como o
> último passo antes de qualquer refinamento. Depois desta feature o caminho ponta a ponta —
> catálogo → sessão → assento → pagamento → ingresso → **entrada** — existe inteiro. Painel do
> organizador e cancelamento só depois.
>
> **A transição para "utilizado" e a garantia de validação única nascem juntas, e isso já estava
> combinado.** A 008 escreveu dentro do próprio modelo de ingresso que não haveria campo de uso
> "porque a transição e a garantia nascem juntas na feature da portaria — o mesmo cuidado que a 007
> teve com a ocupação de assento e sua constraint". A 009 repetiu a promessa e não exibiu estado de
> uso nenhum. Esta é a feature que cumpre as duas.
>
> **Metade do trabalho já existe e não pode ser refeita.** A 008 emitiu o código assinado e o
> verifica **antes de qualquer consulta ao banco**, em módulo puro, com teste que fixa a ausência de
> consulta. O conteúdo assinado carrega a identidade da sessão desde então, e a 008 registrou o
> motivo por extenso: "para que a portaria possa distinguir 'sessão errada' de 'inválido' na feature
> seguinte". Esta feature **consome** isso. Nenhum formato novo de código, nenhuma chave nova.
>
> **A descoberta que decide o desenho**: o desfecho "sessão errada" é **impossível** sem que alguém
> diga qual é a sessão certa. O código carrega a sessão a que o ingresso pertence — comparar esse
> valor com ele mesmo sempre dá igual. É por isso que a portaria declara a sessão da porta antes de
> ler o primeiro código, e não é conveniência de interface: sem essa declaração, um dos quatro
> desfechos exigidos pelo Princípio III nunca acontece, e a tela entrega três.

## A decisão de produto que a spec fixa *(registro obrigatório)*

**A portaria declara a sessão da porta antes de validar.** Ao abrir o posto, o operador escolhe qual
sessão está recebendo. Toda leitura seguinte é comparada com essa escolha.

**A alternativa — inferir a sessão só pelo conteúdo do código — foi descartada porque não funciona,
não porque é pior.** O código diz "este ingresso é da sessão X". Sem um X esperado vindo de fora,
não existe pergunta a fazer: todo ingresso legítimo estaria na sessão dele, e "sessão errada" seria
um estado que nada produz. Entregar três desfechos onde a constitution exige quatro é o mesmo tipo
de tela pela metade que o Princípio I proíbe.

**A alternativa de inferir por horário** — "este ingresso é de uma sessão que já acabou" — também foi
descartada: é heurística, não decisão. Uma sala pode ter duas sessões próximas, e a porta que recebe
a das 21h30 não tem como distinguir por relógio um ingresso da sessão das 21h00 da mesma sala.

**Consequência aceita**: existe um estado inicial em que a portaria ainda não escolheu a sessão, e
ele precisa de tela própria — é o estado vazio obrigatório desta feature.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir o posto e dizer qual sessão está recebendo (Priority: P1)

O funcionário da portaria entra na conta, abre a tela de validação e escolhe a sessão da porta em
que está — filme, horário e sala. A partir dali, a tela está pronta para ler códigos, e mostra o
tempo todo qual sessão está sendo validada.

**Why this priority**: Sem a sessão declarada, o desfecho "sessão errada" não existe e o Princípio
III fica com três dos quatro desfechos. É também o estado vazio obrigatório da feature.

**Independent Test**: Autenticado como `portaria`, abrir a tela e conferir que ela pede a escolha da
sessão antes de qualquer leitura, e que depois de escolhida a sessão fica visível na tela.

**Acceptance Scenarios**:

1. **Given** a portaria acabou de abrir a tela, **When** nenhuma sessão foi escolhida, **Then** vê
   uma explicação em português do que precisa fazer e a lista de sessões que pode receber.
2. **Given** a lista de sessões, **When** o operador escolhe uma, **Then** a tela passa ao estado de
   leitura e exibe filme, horário e sala da sessão escolhida.
3. **Given** uma sessão escolhida, **When** o operador olha a tela a qualquer momento, **Then**
   continua vendo qual sessão está validando — nunca precisa lembrar.
4. **Given** uma sessão escolhida, **When** o operador precisa trocar de porta, **Then** consegue
   escolher outra sessão sem sair da tela nem encerrar a sessão de trabalho.
5. **Given** o operador recarrega a página, **When** a tela volta, **Then** a sessão escolhida
   continua escolhida — trocar de porta é decisão dele, não efeito de recarregar.
6. **Given** não existe nenhuma sessão que a portaria possa receber agora, **When** a tela é aberta,
   **Then** ela explica isso em português, sem área em branco e sem lista vazia sem contexto.
7. **Given** o catálogo externo está indisponível, **When** a tela é aberta, **Then** a lista de
   sessões aparece normalmente — filme, horário e sala são dados locais.

---

### User Story 2 - Ler o QR e liberar a entrada (Priority: P1)

A pessoa chega com o ingresso no celular. O operador aponta a câmera, o código é lido e a tela diz
**válido**, mostrando o lugar. A pessoa entra.

**Why this priority**: É o fluxo principal e o que fecha a etapa 5 da constitution. É também o único
caminho em que o estado do ingresso muda.

**Independent Test**: Com a sessão escolhida e um ingresso comprado por `cliente1` para aquela
sessão, apontar a câmera para o QR e conferir o desfecho **válido** com o lugar exibido.

**Acceptance Scenarios**:

1. **Given** a câmera autorizada e a sessão escolhida, **When** o QR de um ingresso daquela sessão é
   lido, **Then** a tela mostra **válido** e o lugar a que a pessoa deve ir.
2. **Given** o desfecho válido, **When** o operador olha a tela, **Then** identifica o resultado à
   distância de um braço, sem ler texto pequeno.
3. **Given** um ingresso validado, **When** a validação é registrada, **Then** o instante do uso fica
   guardado.
4. **Given** um desfecho exibido, **When** o próximo código é lido, **Then** o resultado anterior dá
   lugar ao novo, sem confundir os dois.
5. **Given** um QR permanece na frente da câmera por vários segundos, **When** a leitura acontece,
   **Then** aquela apresentação produz **um único** desfecho — a pessoa não vê "válido" seguido de
   "já utilizado".
6. **Given** o catálogo externo está indisponível, **When** um código é validado, **Then** a
   validação funciona normalmente.
7. **Given** um leitor de tela, **When** um desfecho é produzido, **Then** ele é anunciado.

---

### User Story 3 - Digitar o código quando a câmera não serve (Priority: P1)

A câmera foi negada, não existe no aparelho, ou o celular da pessoa está com a tela quebrada. O
operador digita o código que aparece em texto no ingresso e recebe o mesmo desfecho.

**Why this priority**: A constitution é explícita: "a digitação manual do código DEVE existir como
alternativa **sempre disponível**, inclusive quando a câmera for negada ou indisponível". Sem isso, a
portaria para quando a câmera falha.

**Independent Test**: Sem autorizar a câmera, colar o código em texto de um ingresso e conferir que o
desfecho é o mesmo que a leitura por câmera produziria.

**Acceptance Scenarios**:

1. **Given** a tela de leitura, **When** o operador olha para ela, **Then** o campo de digitação está
   **sempre visível** — não é um caminho escondido atrás de uma falha da câmera.
2. **Given** a câmera negada pelo navegador, **When** a tela é exibida, **Then** explica em português
   que a leitura por câmera não está disponível e aponta a digitação como caminho, sem área em branco.
3. **Given** um aparelho sem câmera, **When** a tela é aberta, **Then** o comportamento é o mesmo do
   caso anterior.
4. **Given** o código digitado de um ingresso válido, **When** o operador confirma, **Then** o
   desfecho é idêntico ao da leitura por câmera.
5. **Given** o campo vazio, **When** o operador confirma, **Then** recebe um aviso de preenchimento —
   distinto de **inválido**, porque nada foi apresentado.
6. **Given** um código colado com espaços ou quebra de linha nas pontas, **When** o operador confirma,
   **Then** o código é aceito — copiar de um aplicativo de mensagens costuma trazer isso junto.
7. **Given** o formulário de digitação, **When** o operador usa apenas o teclado, **Then** consegue
   digitar, confirmar e ler o desfecho.

---

### User Story 4 - A segunda apresentação não entra (Priority: P1)

O mesmo ingresso é apresentado de novo — pela mesma pessoa que já entrou, ou por outra com uma
captura de tela. A tela diz **já utilizado** e informa quando foi usado.

**Why this priority**: É a metade da validação única exigida pelo Princípio III. Sem ela, uma captura
de tela do QR vale tantas entradas quantas quiserem.

**Independent Test**: Validar um ingresso, validá-lo de novo, e conferir que o segundo desfecho é
**já utilizado** e que o instante do primeiro uso não muda.

**Acceptance Scenarios**:

1. **Given** um ingresso já validado, **When** é apresentado de novo, **Then** a tela mostra **já
   utilizado**.
2. **Given** o desfecho já utilizado, **When** o operador olha a tela, **Then** vê **quando** o
   ingresso foi usado — é o que lhe permite julgar se é a mesma pessoa voltando ou outra.
3. **Given** um ingresso já validado, **When** é apresentado repetidas vezes, **Then** o instante do
   primeiro uso **nunca** muda.
4. **Given** duas validações **simultâneas** do mesmo ingresso, **When** ambas são processadas,
   **Then** exatamente uma resulta em **válido** e a outra em **já utilizado**.
5. **Given** o desfecho já utilizado, **When** o operador olha a tela, **Then** distingue esse
   desfecho de **inválido** sem ler o texto inteiro — são situações diferentes e exigem reações
   diferentes.

---

### User Story 5 - O código forjado não entra (Priority: P1)

Alguém apresenta um código inventado, alterado num caractere, ou gerado com outro segredo. A tela diz
**inválido**.

**Why this priority**: Princípio III. A 008 tornou o código infalsificável; esta feature é onde essa
propriedade vira consequência prática.

**Independent Test**: Alterar um caractere de um código legítimo, apresentá-lo, e conferir o desfecho
**inválido** — e que a rejeição aconteceu sem consultar o registro de ingressos.

**Acceptance Scenarios**:

1. **Given** um código com qualquer caractere alterado, **When** é apresentado, **Then** o desfecho é
   **inválido**.
2. **Given** um código inventado do zero, **When** é apresentado, **Then** o desfecho é **inválido**.
3. **Given** um código assinado com outro segredo, **When** é apresentado, **Then** o desfecho é
   **inválido**.
4. **Given** qualquer código com assinatura que não confere, **When** é apresentado, **Then** a
   rejeição acontece **antes** de qualquer consulta ao registro de ingressos.
5. **Given** um código bem assinado mas que não corresponde a nenhum ingresso existente, **When** é
   apresentado, **Then** o desfecho também é **inválido** — quem apresenta não recebe pista sobre
   onde o palpite chegou perto.
6. **Given** um desfecho inválido, **When** o operador olha a tela, **Then** entende que **não é para
   deixar entrar** sem precisar interpretar jargão.

---

### User Story 6 - O ingresso da outra sessão não entra por esta porta (Priority: P1)

A pessoa chega com um ingresso legítimo, mas da sessão errada — outro horário, outro filme, ou a
sessão de ontem. A tela diz **sessão errada** e mostra para qual sessão aquele ingresso vale.

**Why this priority**: É o quarto desfecho exigido pelo Princípio III, e o único que depende da
decisão de produto registrada acima. É também o que impede a portaria de queimar um ingresso
legítimo na porta errada.

**Independent Test**: Com a portaria recebendo a sessão A, apresentar um ingresso da sessão B e
conferir o desfecho **sessão errada**, e que o ingresso da sessão B **continua não utilizado**.

**Acceptance Scenarios**:

1. **Given** a portaria recebendo a sessão A, **When** um ingresso da sessão B é apresentado,
   **Then** o desfecho é **sessão errada**.
2. **Given** o desfecho sessão errada, **When** o operador olha a tela, **Then** vê a qual sessão
   aquele ingresso pertence — filme, horário e sala —, para poder orientar a pessoa.
3. **Given** um ingresso apresentado na porta errada, **When** o desfecho é produzido, **Then** o
   ingresso **não** é marcado como utilizado.
4. **Given** o ingresso recusado por sessão errada, **When** é apresentado na porta certa, **Then** é
   **válido** — a recusa anterior não o consumiu.
5. **Given** um ingresso de sessão **cancelada**, **When** é apresentado, **Then** o desfecho é
   **sessão errada** e a tela informa que aquela sessão foi cancelada, para o operador saber
   encaminhar em vez de só negar.
6. **Given** um ingresso já utilizado **e** de outra sessão, **When** é apresentado, **Then** o
   desfecho é **sessão errada** — é essa a informação que muda a ação do operador.

---

### User Story 7 - Só a portaria valida (Priority: P2)

Um cliente, um organizador ou um visitante tenta alcançar a validação. O servidor recusa.

**Why this priority**: Princípio IV. É P2 porque a regra de autorização já está estabelecida desde a
003 e aqui é aplicada a endereços novos — mas sem ela um cliente marca o próprio ingresso como usado.

**Independent Test**: Tentar abrir a tela e chamar a validação autenticado como `cliente1` e como
organizador, e sem sessão nenhuma, conferindo as três recusas do servidor.

**Acceptance Scenarios**:

1. **Given** um usuário com papel de cliente, **When** tenta validar, **Then** o servidor recusa por
   papel e nenhum ingresso muda de estado.
2. **Given** um usuário com papel de organizador, **When** tenta validar, **Then** o servidor recusa
   por papel.
3. **Given** um visitante sem sessão, **When** tenta abrir a tela, **Then** é conduzido à entrada e
   volta para a tela depois de entrar.
4. **Given** um cliente autenticado, **When** tenta abrir a tela, **Then** lê uma explicação de que
   aquela área é da portaria — e **não** é conduzido à entrada, porque entrar de novo não muda o
   papel.
5. **Given** a interface esconde a validação de quem não é portaria, **When** a requisição é feita
   diretamente ao servidor, **Then** a recusa continua acontecendo.
6. **Given** um usuário de portaria, **When** tenta comprar ou reservar, **Then** continua recebendo
   as recusas que 007 e 008 já garantem — esta feature não afrouxa nada.

---

### Edge Cases

- **Duas leituras simultâneas do mesmo ingresso**: exatamente uma marca o uso. A garantia é do banco.
- **O mesmo QR parado na frente da câmera**: uma apresentação, um desfecho. Sem isso, a pessoa veria
  "válido" e logo em seguida "já utilizado" pela leitura repetida do próprio aparelho — um defeito que
  faria a portaria desconfiar de um sistema que está certo.
- **Duas portas validando a mesma sessão ao mesmo tempo**: funcionam de forma independente; cada
  ingresso é usado uma vez, na porta onde foi apresentado primeiro.
- **Perda de conexão no instante da validação**: ou o ingresso está marcado e o desfecho foi exibido,
  ou nada aconteceu — nunca um ingresso marcado sem o operador ter visto o resultado.
- **Código digitado com espaços nas pontas**: aceito.
- **Campo de digitação vazio**: aviso de preenchimento, distinto de **inválido**.
- **Ingresso de sessão cancelada**: **sessão errada**, com a informação do cancelamento.
- **Ingresso de uma sessão que já terminou**, apresentado numa porta que recebe outra sessão:
  **sessão errada**.
- **Câmera negada depois de já ter sido autorizada**: a tela volta ao estado explicativo, e a
  digitação continua funcionando.
- **Nenhuma sessão disponível para receber**: estado explicativo, não lista vazia.
- **Tela estreita**: o desfecho continua legível à distância e o campo de digitação continua
  alcançável.
- **Sessão da porta trocada no meio do turno**: as leituras seguintes valem contra a nova sessão, e a
  tela deixa isso evidente.

## Requirements *(mandatory)*

### A tela e a sessão da porta

- **FR-001**: DEVE existir uma tela de validação com endereço próprio, alcançável **apenas** por
  usuários com papel de portaria.
- **FR-002**: A tela DEVE exigir que o operador **escolha a sessão** que está recebendo antes de
  qualquer leitura.
- **FR-003**: Enquanto nenhuma sessão foi escolhida, a tela DEVE exibir um estado explicativo em
  português com a lista de sessões que podem ser recebidas.
- **FR-004**: A sessão escolhida DEVE ficar visível durante todo o uso da tela.
- **FR-005**: O operador DEVE poder trocar a sessão da porta sem sair da tela.
- **FR-006**: A sessão escolhida DEVE sobreviver a um recarregamento da página.
- **FR-007**: Quando não houver nenhuma sessão que a portaria possa receber, a tela DEVE explicar
  isso em português — nunca uma lista vazia sem contexto.
- **FR-008**: A tela DEVE funcionar com o catálogo externo indisponível.

### Os dois caminhos de entrada do código

- **FR-009**: A leitura por **câmera** DEVE ser o caminho principal.
- **FR-010**: A **digitação manual** do código DEVE estar **sempre visível e disponível**, inclusive
  quando a câmera funciona. Não pode ser um caminho que só aparece depois de uma falha.
- **FR-011**: Câmera negada, indisponível ou inexistente DEVE produzir explicação em português e
  apontar a digitação — nunca área em branco nem mensagem de framework.
- **FR-012**: O código aceito DEVE ser **exatamente** o mesmo código que a 008 emite e que a 009
  exibe em texto e em QR. Nenhum segundo formato pode ser criado.
- **FR-013**: Espaços e quebras de linha nas pontas do código digitado DEVEM ser tolerados.
- **FR-014**: Confirmar com o campo vazio DEVE produzir aviso de preenchimento, **distinto** do
  desfecho **inválido**.
- **FR-015**: Uma mesma apresentação contínua de um código à câmera DEVE produzir **um único**
  desfecho.

### Os quatro desfechos

- **FR-016**: A validação DEVE produzir exatamente um de quatro desfechos: **válido**, **inválido**,
  **já utilizado** ou **sessão errada**.
- **FR-017**: Os quatro DEVEM ser distinguíveis **sem ambiguidade** e **sem depender apenas de cor**.
- **FR-018**: Cada desfecho DEVE ter mensagem própria em português, dizendo o que aconteceu e qual é
  a próxima ação do operador.
- **FR-019**: O desfecho DEVE ser legível à distância de um braço, sem exigir leitura de texto
  pequeno.
- **FR-020**: **Válido** DEVE informar o lugar a que a pessoa deve ir.
- **FR-021**: **Já utilizado** DEVE informar **quando** o ingresso foi usado.
- **FR-022**: **Sessão errada** DEVE informar a qual sessão aquele ingresso pertence — filme, horário
  e sala.
- **FR-023**: **Sessão errada** DEVE informar quando a sessão do ingresso foi **cancelada**, em vez
  de apenas negar.
- **FR-024**: Nenhum quinto desfecho pode ser criado. O cancelamento e demais nuances são informação
  **dentro** de um dos quatro.
- **FR-025**: O desfecho DEVE ser anunciado a tecnologias assistivas.
- **FR-026**: Um desfecho exibido DEVE permanecer até a leitura seguinte, e DEVE ser substituído sem
  ambiguidade quando ela chegar.

### A ordem da decisão

- **FR-027**: A verificação da **assinatura** DEVE acontecer **antes de qualquer consulta ao registro
  de ingressos**.
- **FR-028**: Assinatura que não confere DEVE produzir **inválido**.
- **FR-029**: Código bem assinado que não corresponda a nenhum ingresso DEVE produzir **inválido** —
  o mesmo desfecho da assinatura ruim, para não entregar pista a quem tenta adivinhar.
- **FR-030**: A conferência da **sessão** DEVE acontecer **antes** da conferência de uso.
- **FR-031**: **Sessão errada** NÃO PODE alterar o estado do ingresso.
- **FR-032**: **Inválido** NÃO PODE alterar estado nenhum.
- **FR-033**: **Já utilizado** NÃO PODE alterar o instante do primeiro uso.

### Validação única — o núcleo do Princípio III nesta feature

- **FR-034**: O ingresso DEVE passar a registrar **o instante em que foi utilizado**, e esse registro
  nasce **na mesma entrega** que a garantia de unicidade — nunca antes.
- **FR-035**: Um ingresso NUNCA pode ser marcado como utilizado duas vezes. Esta garantia DEVE ser
  imposta pelo **banco de dados**, por escrita condicional atômica, e **não** por leitura seguida de
  escrita na aplicação.
- **FR-036**: Duas validações **simultâneas** do mesmo ingresso DEVEM resultar em exatamente um
  **válido** e um **já utilizado**.
- **FR-037**: A validação DEVE ser **idempotente**: repetir a operação não muda nada além de repetir
  o desfecho **já utilizado**.
- **FR-038**: A marcação e o desfecho exibido DEVEM ser consistentes: não pode existir ingresso
  marcado sem que o operador tenha visto **válido**.

### Autorização

- **FR-039**: Apenas usuários com papel de **portaria** podem abrir a tela e validar.
- **FR-040**: Cliente e organizador DEVEM receber recusa por papel, **do servidor**.
- **FR-041**: Um cliente ou organizador que alcance a tela DEVE ler uma explicação, e **não** ser
  conduzido à entrada — entrar de novo não muda o papel.
- **FR-042**: Um visitante sem sessão DEVE ser conduzido à entrada e voltar à tela depois de entrar.
- **FR-043**: A recusa DEVE acontecer no servidor. Esconder a tela na interface não conta como
  controle de acesso.
- **FR-044**: O papel de portaria continua **sem** poder comprar, reservar ou pagar.

### Preservação

- **FR-045**: Nenhuma asserção de teste das features 001–009 pode ser removida ou enfraquecida.
- **FR-046**: O formato do código e o segredo de assinatura da 008 NÃO PODEM mudar — há ingressos já
  emitidos.
- **FR-047**: O segredo de assinatura continua sem chegar ao navegador; a verificação é só no
  servidor.
- **FR-048**: A área "Meus ingressos" e a página compartilhada da 009 continuam **sem** exibir estado
  de uso. Esta feature cria o estado; exibi-lo ao cliente é decisão de outra.
- **FR-049**: A disciplina de tokens da 006 DEVE ser mantida.
- **FR-050**: O README DEVE ser atualizado com a tela de portaria e o modelo de sessão da porta.

### Key Entities

- **Ingresso** *(existente, ampliado)*: ganha **o instante do uso**, nulo enquanto não usado. É a
  única alteração de estado desta feature, e ela nasce junto da garantia que a protege.
- **Validação**: o ato de apresentar um código numa porta que recebe uma sessão. Produz um dos quatro
  desfechos. Só um deles escreve.
- **Sessão da porta**: a sessão que aquele posto está recebendo, escolhida pelo operador. É o que
  torna **sessão errada** possível; sem ela, o desfecho não existe.
- **Código do ingresso** *(existente, inalterado)*: o conteúdo assinado da 008, que já carrega a
  identidade do ingresso e a da sessão. Esta feature o consome e não o redefine.

## Success Criteria *(mandatory)*

- **SC-001**: Um operador abre a tela, escolhe a sessão e valida o primeiro ingresso em menos de
  **1 minuto**, seguindo apenas o que a tela diz.
- **SC-002**: A partir da tela pronta, cada validação leva no máximo **3 segundos** entre apresentar
  o código e ver o desfecho.
- **SC-003**: Os quatro desfechos são distinguíveis por alguém que não enxerga cor.
- **SC-004**: O desfecho é identificável a um braço de distância, sem leitura de texto pequeno.
- **SC-005**: A primeira apresentação de um ingresso legítimo na porta certa resulta em **válido** em
  100% dos casos.
- **SC-006**: A segunda apresentação do mesmo ingresso resulta em **já utilizado** em 100% dos casos,
  e o instante do primeiro uso permanece inalterado.
- **SC-007**: Duas validações simultâneas do mesmo ingresso produzem exatamente um **válido** e um
  **já utilizado** — verificável por teste automatizado de concorrência que **falha** se a garantia
  do banco for substituída por leitura seguida de escrita.
- **SC-008**: Código adulterado, código inventado e código assinado com outro segredo produzem
  **inválido**, e a rejeição acontece **sem nenhuma consulta** ao registro de ingressos — verificável
  por teste automatizado.
- **SC-009**: Um ingresso legítimo apresentado na porta de outra sessão produz **sessão errada** e
  **permanece utilizável** na porta certa.
- **SC-010**: A digitação manual produz o mesmo desfecho da câmera para o mesmo código, em 100% dos
  casos.
- **SC-011**: Com a câmera negada, a portaria continua validando pela digitação, sem nenhuma tela em
  branco.
- **SC-012**: Uma apresentação contínua do mesmo QR à câmera produz exatamente **um** desfecho.
- **SC-013**: Cliente, organizador e visitante recebem recusa do servidor, e a recusa persiste quando
  a interface é contornada.
- **SC-014**: A validação permanece funcional com o catálogo externo fora do ar.
- **SC-015**: Nenhum estado da tela exibe texto genérico de erro nem área em branco.
- **SC-016**: As asserções de teste das features 001–009 continuam passando sem alteração.

## Assumptions

- **A escolha da sessão é do operador, e a lista oferecida é a das sessões do dia.** Assume-se que a
  tela oferece as sessões publicadas do dia corrente, ordenadas por horário, **incluindo as que já
  começaram** — gente chega atrasada, e uma lista que esconde a sessão em andamento é uma lista que
  não serve à porta. Sessões canceladas não entram na lista: não há entrada a receber.

- **A sessão da porta é lembrada por posto, não por conta.** Assume-se que a escolha sobrevive ao
  recarregamento no mesmo navegador, e que trocar de porta é uma ação explícita. Ligar a escolha à
  conta faria dois operadores da mesma conta em portas diferentes brigarem pelo mesmo valor.

- **O registro de uso guarda o instante, não quem validou.** Assume-se apenas o momento. Guardar o
  operador seria auditoria, e nenhum dos quatro desfechos depende disso; contador de leituras e
  telemetria estão explicitamente fora de escopo. Se a auditoria virar requisito, o campo entra com a
  feature que o consome — mesma disciplina que manteve o estado de uso fora até agora.

- **Sem modo offline.** Assume-se que a portaria tem rede. Validar offline exigiria decidir o uso no
  aparelho e reconciliar depois, e reconciliação é exatamente onde a validação única se perde — o
  oposto do que o Princípio III exige.

- **Sem som nem vibração no desfecho.** Assume-se sinal visual apenas. Feedback sonoro ajudaria numa
  portaria barulhenta, mas não é verificável na avaliação e não substitui nenhum requisito.

- **A leitura por câmera acontece no navegador, com permissão do usuário.** Assume-se que o operador
  autoriza a câmera uma vez por aparelho. A negação é estado normal e tratado, nunca erro.

- **Uma porta, uma sessão por vez.** Assume-se que um posto recebe uma sessão de cada vez. Receber
  várias simultaneamente enfraqueceria "sessão errada" até o ponto de torná-lo raro — e o desfecho
  existe justamente para ser produzido.

- **O cliente não vê o estado de uso.** Assume-se que "Meus ingressos" e a página compartilhada
  continuam como a 009 as entregou. Exibir "utilizado" ao cliente é decisão de produto que esta
  feature não precisa tomar para fechar o fluxo, e a 009 já registrou a ausência como deliberada.

- **O desfecho permanece até a leitura seguinte.** Assume-se que a tela não apaga o resultado sozinha
  depois de alguns segundos: numa fila, o operador pode olhar tarde, e um resultado que sumiu vira
  uma segunda leitura desnecessária.

### Escopo excluído

Painel do organizador · cancelamento, estorno e devolução ao estoque · assentos em tempo real ·
deploy · nota fiscal · revenda · envio por e-mail · aplicativo nativo · recuperação de senha ·
mudança no formato do código ou na chave de assinatura · contador de leituras e telemetria ·
transferência de titularidade · exibição do estado de uso ao cliente · validação offline ·
auditoria de qual operador validou.

### Dependências

- Código assinado, verificação sem tocar o banco e a identidade da sessão dentro do código
  (`008-payment-ticket-issuance`)
- Ingresso emitido, um por assento (`008`)
- Código em texto e em QR alcançáveis pelo cliente (`009-my-tickets-sharing`)
- Autenticação com os três papéis e a conta `portaria` do seed (`003`, `005`)
- Sessões publicadas com sala e horário (`001`, `005`)
- Disciplina de tokens (`006-visual-identity`)
