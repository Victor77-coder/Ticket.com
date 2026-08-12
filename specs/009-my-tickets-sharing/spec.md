# Feature Specification: Meus Ingressos e Compartilhamento por Link

**Feature Branch**: `main` *(sem branch própria — ver "Nota de processo")*

**Created**: 2026-08-12

**Status**: Draft

**Input**: User description: "Área 'Meus ingressos' e compartilhamento de ingresso por link."

> **O ingresso já existe e é inalcançável.** A 008 emitiu o ingresso com QR assinado e o mostrou na
> confirmação da compra. A suposição registrada lá foi explícita: "a **lista** de todos os ingressos
> do cliente ('Meus ingressos') e o link de compartilhamento continuam fora, na feature seguinte".
> Esta é essa feature. Hoje o cliente que sai da confirmação não tem caminho de volta ao próprio
> ingresso — o direito de entrar na sala existe no banco e não tem endereço.
>
> Esta feature fecha a etapa 4 da ordem de construção obrigatória da constitution ("Ingresso com QR
> assinado, área 'Meus ingressos' e link de compartilhamento") e destrava a etapa 5, a portaria.
>
> **O link é credencial ao portador, e isso é assumido, não contornado.** A página compartilhada
> exibe o QR, porque compartilhar ingresso é entregar o direito de entrar — é para isso que a pessoa
> manda o ingresso a quem vai com ela, e uma página compartilhada sem o QR seria decorativa. A
> consequência aceita é que quem tem o link tem o ingresso, e dela nascem duas exigências que não
> são opcionais: o link precisa ser **não adivinhável** e o dono precisa poder **revogá-lo e gerar
> outro**.
>
> **O token do link é distinto do código do QR, e a distinção é estrutural.** São dois segredos com
> ciclos de vida diferentes: revogar um link não pode invalidar o ingresso na portaria, e o ingresso
> não pode depender de link nenhum para valer na catraca. Usar o mesmo segredo para as duas coisas
> amarraria a revogação de um convite à destruição de uma entrada paga.
>
> **A prova de não vazamento é obrigatória.** O Princípio III é explícito: "o link de
> compartilhamento de ingresso DEVE conceder apenas visualização do ingresso — ele nunca expõe a
> conta do comprador, o histórico de compras ou qualquer dado de pagamento". O teste que inspeciona
> a resposta pública inteira é o mesmo espírito do que a 001 já faz com o catálogo público, e é
> requisito, não diferencial.

## Nota de processo

O hook `before_specify` do Spec Kit criaria a branch `009-my-tickets-sharing`. Este projeto trabalha
na `main`, sem branches de feature nem PRs, por decisão registrada do autor diante do prazo de 7
dias. O diretório da spec segue a numeração sequencial normalmente; apenas a branch não é criada.

## O que esta feature deliberadamente NÃO tem

**Nenhum estado "já utilizado".** A transição para utilizado e a garantia de que um ingresso não é
validado duas vezes nascem **juntas** na feature da portaria, pela mesma razão que a 007 criou
`ReservedSeat` e sua constraint na mesma migração, e que a 008 criou pagamento e emissão na mesma
transação. A 008 já registrou a ausência dentro do próprio modelo de ingresso, e a ausência continua
deliberada aqui.

Exibir nesta feature um selo de "utilizado" que nada escreve seria tela pela metade — exatamente o
que o Princípio I proíbe. A lista e a página compartilhada mostram o ingresso como ele é hoje:
emitido, com lugar e com código.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Voltar ao próprio ingresso (Priority: P1)

O cliente comprou ontem e fechou o navegador. Hoje ele entra na conta, abre "Meus ingressos" e vê,
no topo, o ingresso da sessão que acontece primeiro — com filme, dia, hora, sala e lugar. Os
ingressos de sessões que já passaram continuam ali, separados, mais abaixo.

**Why this priority**: É a razão de existir da feature. Sem endereço permanente, o ingresso emitido
pela 008 é inalcançável depois que a confirmação sai da tela, e a etapa 4 da constitution fica
aberta.

**Independent Test**: Autenticado como `cliente1`, com ingressos de uma sessão futura e de uma
sessão passada, abrir "Meus ingressos" e conferir que o ingresso da próxima sessão é o primeiro da
lista e que o da sessão passada aparece separado dele.

**Acceptance Scenarios**:

1. **Given** um cliente com ingressos emitidos, **When** abre "Meus ingressos", **Then** vê todos os
   seus ingressos, um por lugar comprado.
2. **Given** ingressos de várias sessões futuras, **When** a lista é exibida, **Then** o da sessão
   que acontece primeiro aparece no topo, e os demais em ordem crescente de horário.
3. **Given** ingressos de sessões futuras e passadas, **When** a lista é exibida, **Then** os dois
   grupos são visivelmente distintos e o cliente entende, sem adivinhar, qual é qual.
4. **Given** ingressos de sessões passadas, **When** o cliente os observa, **Then** continuam
   completos e acessíveis — nada é escondido, apenas ordenado depois.
5. **Given** um ingresso qualquer da lista, **When** o cliente o observa, **Then** identifica filme,
   dia, hora, sala e lugar sem abrir nada.
6. **Given** um cliente autenticado em qualquer página, **When** procura seus ingressos, **Then**
   chega à área a partir da navegação global, sem decorar endereço.
7. **Given** o cliente acabou de pagar, **When** está na confirmação da compra, **Then** existe
   caminho dali para "Meus ingressos".
8. **Given** o catálogo externo está indisponível, **When** a lista é aberta, **Then** ela funciona
   normalmente — filme, sessão, sala e lugar são dados locais.

---

### User Story 2 - Estado vazio de quem ainda não comprou (Priority: P1)

Um cliente que nunca comprou abre "Meus ingressos". Em vez de uma área em branco, lê uma frase que
explica que ele ainda não tem ingressos e é levado ao catálogo para escolher uma sessão.

**Why this priority**: Portão de qualidade da constitution — "estados de erro e vazio implementados e
escritos para humanos" — e Princípio I, que proíbe entregar tela pela metade. Um dos dois clientes
do seed começa exatamente neste estado, então é o que o avaliador vê primeiro se entrar com a conta
errada.

**Independent Test**: Autenticado como um cliente sem nenhuma compra, abrir "Meus ingressos" e
conferir que existe texto escrito para humanos e um caminho para o catálogo.

**Acceptance Scenarios**:

1. **Given** um cliente sem nenhum ingresso, **When** abre a área, **Then** vê uma mensagem em
   português dizendo que ainda não tem ingressos e qual é a próxima ação.
2. **Given** o estado vazio, **When** o cliente age sobre ele, **Then** é conduzido ao catálogo de
   filmes em sessão.
3. **Given** o estado vazio, **When** ele é observado, **Then** não há área em branco, texto de
   placeholder nem mensagem genérica de erro.
4. **Given** um cliente que só tem ingressos de sessões passadas, **When** abre a área, **Then** não
   vê o estado vazio — o estado vazio é para quem não tem ingresso nenhum.

---

### User Story 3 - Mostrar o QR na portaria (Priority: P1)

O cliente chega ao cinema com o celular na mão. Abre o ingresso da sessão, aponta a tela para o
leitor, e o código é lido de primeira. Se o QR não carregar, o código continua ali em texto, para ser
digitado.

**Why this priority**: É o uso final do ingresso, e o que a feature da portaria vai exercitar. Um QR
que não é lido na tela de um celular transforma a etapa 5 inteira em teoria.

**Independent Test**: Abrir o ingresso em uma janela de 320px de largura e ler o QR da tela com um
aplicativo leitor de QR de terceiro, conferindo que o conteúdo lido é o mesmo código que aparece em
texto ao lado.

**Acceptance Scenarios**:

1. **Given** um ingresso aberto, **When** um leitor de QR de terceiro aponta para a tela, **Then** o
   código é lido corretamente.
2. **Given** uma tela estreita de celular, **When** o ingresso é exibido, **Then** o QR permanece com
   tamanho e contraste suficientes para leitura, sem exigir zoom manual.
3. **Given** o QR exibido, **When** o cliente observa o ingresso, **Then** o código também está
   disponível em texto legível, para digitação manual.
4. **Given** a imagem do QR não carrega, **When** o ingresso é exibido, **Then** o texto do código
   permanece disponível e o cliente entende o que fazer.
5. **Given** dois ingressos da mesma compra, **When** ambos são exibidos, **Then** cada um mostra o
   seu próprio lugar e o seu próprio código, distintos entre si.
6. **Given** um leitor de tela, **When** percorre o ingresso, **Then** o QR tem descrição textual que
   informa a que lugar ele pertence.

---

### User Story 4 - Mandar o ingresso para quem vai comigo (Priority: P1)

O cliente comprou dois lugares e vai com outra pessoa. Ele abre o ingresso do acompanhante, pede um
link, copia e manda pelo aplicativo de mensagens. A outra pessoa abre o link no celular dela, sem
conta nenhuma, e vê aquele ingresso com o QR — pronto para a portaria.

**Why this priority**: É o requisito de compartilhamento do desafio, e a segunda metade da feature.
Sem ele, quem vai junto depende do celular do comprador na fila.

**Independent Test**: Autenticado como `cliente1`, gerar o link de um ingresso, abrir esse link em
uma sessão de navegação sem autenticação e conferir que o ingresso é exibido com o QR.

**Acceptance Scenarios**:

1. **Given** um ingresso do próprio cliente, **When** ele pede o link de compartilhamento, **Then**
   recebe um endereço completo, pronto para copiar e enviar.
2. **Given** o link gerado, **When** uma pessoa sem conta o abre, **Then** vê o ingresso com filme,
   sessão, sala, lugar e o QR.
3. **Given** o link aberto por quem não tem conta, **When** a pessoa aponta um leitor de QR para a
   tela, **Then** o código é lido — é o mesmo ingresso, não uma representação decorativa.
4. **Given** um ingresso que já tem link ativo, **When** o dono pede o link de novo, **Then** recebe
   o **mesmo** link, e não um segundo link válido em paralelo.
5. **Given** um cliente com vários ingressos, **When** gera o link de um deles, **Then** o link
   corresponde àquele ingresso e a nenhum outro.
6. **Given** um endereço de compartilhamento inventado, **When** alguém tenta abri-lo, **Then** não
   encontra ingresso nenhum.

---

### User Story 5 - A página compartilhada não conta nada além do ingresso (Priority: P1)

Quem recebe o link vê o ingresso. Não vê o nome de quem comprou, não vê os outros ingressos da mesma
compra, não vê quanto foi pago nem qualquer dado de cartão, e não descobre nada sobre a conta do
dono.

**Why this priority**: Princípio III, texto direto. O link é o único endereço público desta feature,
e é onde um vazamento aconteceria. A prova é requisito da constitution, não refinamento.

**Independent Test**: Gerar o link de um ingresso de uma compra de três lugares feita por `cliente1`
e inspecionar a resposta pública inteira, conferindo que não contém nome, e-mail ou identificador do
comprador, nenhum dos outros dois ingressos, nenhum valor e nenhum dado de pagamento.

**Acceptance Scenarios**:

1. **Given** a página compartilhada de um ingresso, **When** seu conteúdo inteiro é inspecionado,
   **Then** não aparece o nome nem o e-mail de quem comprou.
2. **Given** uma compra de três lugares, **When** o link de um dos ingressos é aberto, **Then** os
   outros dois ingressos não aparecem, nem são alcançáveis a partir dali.
3. **Given** a página compartilhada, **When** seu conteúdo é inspecionado, **Then** não aparece valor
   pago, forma de pagamento nem qualquer resquício de dado de cartão.
4. **Given** a página compartilhada, **When** quem a abre tenta chegar à conta do dono, **Then** não
   existe caminho — nem link, nem identificador reaproveitável.
5. **Given** a página compartilhada, **When** quem a abre é um visitante sem conta, **Then** ela não
   pede autenticação e não conduz a nenhuma entrada.
6. **Given** a página compartilhada, **When** um mecanismo de busca a encontra, **Then** ela instrui a
   não indexar — um endereço-credencial não pode virar resultado de busca.

---

### User Story 6 - Cancelar um link que foi longe demais (Priority: P1)

O cliente mandou o link no grupo errado. Ele abre o ingresso, revoga o link, e o endereço antigo
deixa de mostrar qualquer coisa. O ingresso continua valendo — o código do QR é o mesmo de antes. Se
ele quiser, gera um link novo e manda para a pessoa certa.

**Why this priority**: É a contrapartida obrigatória da decisão de exibir o QR na página pública. Um
link ao portador sem revogação é uma credencial que não se pode cancelar. E é aqui que a distinção
entre os dois segredos deixa de ser teoria: revogar o convite não pode queimar a entrada.

**Independent Test**: Gerar o link de um ingresso, conferir que abre, revogar, conferir que o mesmo
endereço não exibe mais o ingresso, e conferir que o código do QR daquele ingresso continua sendo o
mesmo e continua verificando.

**Acceptance Scenarios**:

1. **Given** um link ativo, **When** o dono o revoga, **Then** o endereço antigo deixa de exibir o
   ingresso.
2. **Given** um link revogado, **When** alguém o abre, **Then** lê uma mensagem em português dizendo
   que aquele link não vale mais e o que fazer — nunca uma tela de erro genérica.
3. **Given** um link revogado, **When** o código do QR daquele ingresso é verificado, **Then**
   continua sendo o mesmo código de antes e continua sendo aceito.
4. **Given** um link revogado, **When** o dono gera outro, **Then** recebe um endereço **diferente**
   do anterior.
5. **Given** um link revogado e um link novo do mesmo ingresso, **When** o antigo é aberto de novo,
   **Then** continua sem exibir nada — revogado é para sempre.
6. **Given** um ingresso que nunca teve link, **When** alguém tenta adivinhar um endereço de
   compartilhamento para ele, **Then** não existe endereço a adivinhar.
7. **Given** um ingresso com link ativo, **When** o dono abre esse ingresso, **Then** vê que existe um
   link ativo e tem as duas ações disponíveis: copiar e revogar.

---

### User Story 7 - Cada um vê e mexe só no que é seu (Priority: P2)

Outro cliente, um organizador ou um usuário de portaria tenta listar, abrir, compartilhar ou revogar
o ingresso de alguém. O servidor recusa em todos os casos.

**Why this priority**: Princípio IV. A 008 já garante que um cliente não vê ingressos de outro; esta
feature cria três novas superfícies — a lista, a geração e a revogação — e cada uma precisa da mesma
recusa. É P2 porque a decisão de autorização é a mesma já estabelecida, aplicada a endereços novos.

**Independent Test**: Com ingressos de `cliente1` emitidos, tentar listá-los, abri-los, gerar link e
revogar link autenticado como `cliente2`, como organizador e como portaria, e conferir a recusa do
servidor em todas as combinações.

**Acceptance Scenarios**:

1. **Given** ingressos de `cliente1`, **When** `cliente2` abre "Meus ingressos", **Then** vê apenas os
   seus, e nenhum de `cliente1`.
2. **Given** um ingresso de `cliente1`, **When** `cliente2` tenta abri-lo diretamente, **Then** o
   servidor recusa.
3. **Given** um ingresso de `cliente1`, **When** `cliente2` tenta gerar um link para ele, **Then** o
   servidor recusa e nenhum link é criado.
4. **Given** um link ativo de um ingresso de `cliente1`, **When** `cliente2` tenta revogá-lo, **Then**
   o servidor recusa e o link continua ativo.
5. **Given** qualquer ingresso, **When** um usuário com papel de organizador tenta listar, gerar ou
   revogar, **Then** o servidor nega por papel.
6. **Given** qualquer ingresso, **When** um usuário com papel de portaria tenta listar, gerar ou
   revogar, **Then** o servidor nega por papel.
7. **Given** um visitante sem sessão ativa, **When** tenta abrir "Meus ingressos", **Then** é
   conduzido à entrada e nenhum ingresso é exibido.
8. **Given** a interface esconde as ações para quem não é dono, **When** a requisição é feita
   diretamente ao servidor, **Then** a recusa continua acontecendo — esconder o botão nunca é o
   controle de acesso.

---

### Edge Cases

- **Cliente sem nenhum ingresso**: estado vazio escrito para humanos, com saída para o catálogo.
- **Cliente só com ingressos passados**: lista normal, sem estado vazio.
- **Ingresso de sessão que começou há poucos minutos**: continua acessível e com QR legível; ele
  apenas deixa de ser contado como "próximo".
- **Ingresso de sessão cancelada depois da compra**: continua acessível, e a lista informa que a
  sessão foi cancelada em vez de exibi-lo como se nada tivesse acontecido.
- **Vários ingressos da mesma sessão**: aparecem lado a lado, cada um com seu lugar e seu código —
  nunca fundidos num único cartão com um QR só.
- **Endereço de compartilhamento inventado**: mesma resposta de um link revogado — nada é exibido, e a
  mensagem não revela se aquele endereço já existiu.
- **Link revogado aberto por quem já tinha visto o ingresso antes**: deixa de exibir, sem exceção por
  ter funcionado antes.
- **Dois pedidos de link simultâneos para o mesmo ingresso**: resulta em **um único** link ativo, não
  dois.
- **Pedido de link e revogação simultâneos**: o desfecho é um dos dois estados coerentes — link ativo
  ou nenhum link ativo —, nunca um link ativo que o dono não consegue ver nem revogar.
- **Link compartilhado de ingresso de sessão já passada**: abre normalmente; o valor de uso já
  acabou, mas esconder criaria um estado que nada escreve.
- **Tela estreita**: lista, ingresso e página compartilhada permanecem completos e o QR permanece
  legível.
- **Navegação apenas por teclado**: percorrer a lista, copiar o link e revogar são todos alcançáveis e
  acionáveis por teclado, e o resultado de cada ação é anunciado a tecnologias assistivas.
- **Área aberta com o catálogo externo fora do ar**: funciona — filme, sessão, sala e lugar são dados
  locais desde a 001.

## Requirements *(mandatory)*

### A área "Meus ingressos"

- **FR-001**: DEVE existir uma área do cliente, com **endereço estável**, que lista todos os
  ingressos emitidos para ele.
- **FR-002**: A área DEVE ser alcançável a partir da navegação global para clientes autenticados.
- **FR-003**: A confirmação de compra da 008 DEVE conduzir à área.
- **FR-004**: A lista DEVE mostrar **um item por ingresso** — ou seja, um por lugar comprado —, nunca
  um item por compra.
- **FR-005**: Cada item DEVE identificar filme, dia, hora, sala e lugar sem exigir interação.
- **FR-006**: A lista DEVE distinguir visualmente ingressos de sessões que **ainda vão acontecer** dos
  de sessões que **já aconteceram**, e a distinção NÃO PODE depender apenas de cor.
- **FR-007**: Entre os ingressos futuros, o da sessão que acontece primeiro DEVE ser o primeiro
  exibido; os demais seguem em ordem crescente de horário de sessão.
- **FR-008**: Entre os ingressos passados, o mais recente DEVE vir primeiro.
- **FR-009**: Ingressos de sessões passadas NÃO PODEM ser escondidos nem removidos — continuam
  acessíveis, com seu código.
- **FR-010**: A fronteira entre futuro e passado DEVE ser decidida pelo **servidor**, a partir do
  horário da sessão. O relógio do navegador não decide.
- **FR-011**: Um ingresso de sessão **cancelada** DEVE ser exibido com essa informação, em português,
  em vez de aparecer como um ingresso comum.
- **FR-012**: A área DEVE ter **estado vazio** para o cliente sem nenhum ingresso, com texto em
  português dizendo o que aconteceu e qual a próxima ação, e caminho para o catálogo.
- **FR-013**: O estado vazio NÃO PODE aparecer para quem tem ingressos apenas de sessões passadas.
- **FR-014**: A área DEVE funcionar com o catálogo externo indisponível.

### O ingresso e o QR

- **FR-015**: Cada ingresso DEVE ter **endereço próprio e estável**, acessível ao dono, onde o QR e as
  ações de compartilhamento vivem.
- **FR-016**: O QR exibido DEVE ser legível por um leitor de QR de terceiro apontado para a tela,
  inclusive em largura de tela de celular.
- **FR-017**: O conteúdo lido do QR DEVE ser exatamente o código assinado emitido pela 008 — nenhuma
  nova forma de código é criada nesta feature.
- **FR-018**: O código DEVE estar disponível também em **texto legível** ao lado do QR, porque a
  constitution exige digitação manual como alternativa sempre disponível na portaria.
- **FR-019**: Se a imagem do QR não carregar, o texto do código DEVE permanecer disponível.
- **FR-020**: O QR DEVE ter descrição textual que informe a que lugar ele pertence.
- **FR-021**: Ingressos distintos DEVEM exibir códigos distintos — a garantia é da 008 e não pode ser
  desfeita por agrupamento na interface.
- **FR-022**: Nenhum estado desta feature pode exibir estado de "utilizado" ou equivalente. Essa
  transição nasce na feature da portaria.

### O link de compartilhamento

- **FR-023**: O dono de um ingresso DEVE poder gerar um link que exiba **aquele** ingresso a quem não
  tem conta.
- **FR-024**: O endereço gerado DEVE ser entregue completo e pronto para copiar e enviar.
- **FR-025**: O token do link DEVE ser **não adivinhável**: não pode ser identificador sequencial, não
  pode ser identificador cru do ingresso, da reserva ou do pagamento, e não pode ser derivado de dado
  do pedido.
- **FR-026**: O token do link DEVE ser **distinto do código do QR** e não pode ser derivado dele nem
  permitir deduzi-lo.
- **FR-027**: Conhecer um ou mais tokens NÃO PODE permitir deduzir o token de outro ingresso.
- **FR-028**: Um ingresso DEVE ter **no máximo um link ativo** por vez. Pedir o link quando já existe
  um ativo DEVE devolver o mesmo endereço, não criar um segundo.
- **FR-029**: Dois pedidos simultâneos de link para o mesmo ingresso DEVEM resultar em **um único**
  link ativo. Esta garantia DEVE ser imposta pelo banco de dados, não apenas pela aplicação.
- **FR-030**: O dono DEVE poder **revogar** o link ativo.
- **FR-031**: Um link revogado NUNCA volta a valer, em nenhuma circunstância.
- **FR-032**: Após revogar, o dono DEVE poder gerar um link **novo e diferente** do revogado.
- **FR-033**: Revogar ou gerar link NÃO PODE alterar o código do QR do ingresso, nem torná-lo
  inválido — os dois ciclos de vida são independentes.
- **FR-034**: Um ingresso sem link gerado NÃO PODE ter endereço público algum.
- **FR-035**: A interface do dono DEVE mostrar se existe link ativo e oferecer copiar e revogar.

### A página compartilhada

- **FR-036**: A página do link DEVE ser pública: acessível sem autenticação, sem conduzir a nenhuma
  entrada e sem pedir conta.
- **FR-037**: A página DEVE exibir **apenas**: filme, sessão (dia e hora), sala, lugar e o QR.
- **FR-038**: A página NÃO PODE expor nome, e-mail ou qualquer identificação de quem comprou.
- **FR-039**: A página NÃO PODE expor os demais ingressos da mesma compra, nem qualquer caminho até
  eles.
- **FR-040**: A página NÃO PODE expor valor pago, forma de pagamento ou qualquer dado de cartão.
- **FR-041**: A página NÃO PODE expor identificadores reaproveitáveis da conta, da reserva ou do
  pagamento.
- **FR-042**: A ausência de vazamento DEVE ser provada por teste automatizado que inspeciona a
  resposta pública **inteira**, no mesmo espírito do teste que a 001 aplica ao catálogo público.
- **FR-043**: Um token inexistente, revogado ou substituído DEVE produzir a **mesma** resposta, com
  mensagem em português dizendo que o link não vale mais e qual a próxima ação. A resposta NÃO PODE
  revelar se aquele token um dia existiu.
- **FR-044**: A página DEVE instruir mecanismos de busca a não indexá-la.
- **FR-045**: A página DEVE funcionar com o catálogo externo indisponível.

### Autorização

- **FR-046**: Apenas usuários com papel de **cliente** podem acessar a área "Meus ingressos".
- **FR-047**: Um cliente DEVE ver exclusivamente os próprios ingressos.
- **FR-048**: Apenas o **dono** do ingresso pode abri-lo, gerar seu link e revogá-lo.
- **FR-049**: Organizador e portaria DEVEM receber recusa por papel em listar, abrir, gerar e revogar.
- **FR-050**: Toda recusa DEVE acontecer no servidor. Esconder a ação na interface não conta como
  controle de acesso.
- **FR-051**: Um visitante sem sessão ativa que tente abrir a área ou um ingresso DEVE ser conduzido à
  entrada, sem que nenhum dado de ingresso seja exibido.

### Estados, mensagens e acessibilidade

- **FR-052**: Estado vazio, link revogado, link inexistente, sessão cancelada e recusa por papel
  DEVEM ter mensagem própria em português, dizendo o que houve e a próxima ação.
- **FR-053**: Nenhum estado pode exibir texto genérico de erro nem área em branco.
- **FR-054**: O resultado de gerar, copiar e revogar link DEVE ser anunciado a tecnologias
  assistivas.
- **FR-055**: Lista, ingresso e página compartilhada DEVEM ser percorríveis e acionáveis apenas por
  teclado.
- **FR-056**: Lista, ingresso e página compartilhada DEVEM permanecer completos e legíveis em tela
  estreita, com o QR legível.

### Preservação

- **FR-057**: Nenhuma asserção de teste das features 001–008 pode ser removida ou enfraquecida. Se a
  inclusão do novo ponto de entrada na navegação global exigir ajuste em uma asserção de inventário
  de itens do cabeçalho da 002, o ajuste DEVE ser **aditivo** — acrescentar o item esperado, nunca
  afrouxar a verificação.
- **FR-058**: Nenhum contrato de API existente pode mudar de forma.
- **FR-059**: A disciplina de tokens da 006 DEVE ser mantida: nenhum valor de cor, espaçamento,
  tipografia, raio ou duração fora dos tokens.
- **FR-060**: O segredo de assinatura do ingresso continua sem chegar ao front-end, e nada nesta
  feature pode expô-lo.
- **FR-061**: O README DEVE ser atualizado com a área "Meus ingressos", o comportamento do link de
  compartilhamento e a decisão registrada de que o link é credencial ao portador.

### Key Entities

- **Ingresso** *(existente, 008)*: inalterado no que é. Ganha **alcance**: endereço próprio e estável
  para o dono, e presença numa lista ordenada. Nenhum campo novo de estado de uso.
- **Link de compartilhamento**: a autorização de leitura pública de **um** ingresso, identificada por
  um token opaco e não adivinhável, com estado ativo ou revogado. No máximo um ativo por ingresso; os
  revogados são preservados para que um token revogado nunca possa voltar a valer nem ser
  reatribuído. Vive e morre sem tocar o código do QR.
- **Visão pública do ingresso**: o recorte exibível a quem tem o link — filme, sessão, sala, lugar e
  código. É definido por inclusão explícita, não por exclusão: o que não está nesta lista não sai.

## Success Criteria *(mandatory)*

- **SC-001**: Um cliente autenticado, partindo de qualquer página, chega ao ingresso da próxima
  sessão em no máximo **2 interações**.
- **SC-002**: Com ingressos de várias sessões, o da próxima sessão é o primeiro exibido em 100% dos
  casos — verificável por teste automatizado.
- **SC-003**: Ingressos futuros e passados são distinguíveis sem depender de cor, e os passados
  continuam completos e acessíveis.
- **SC-004**: Um cliente sem nenhum ingresso vê texto escrito para humanos e alcança o catálogo em
  1 interação. Nenhuma área em branco em nenhum estado.
- **SC-005**: Um leitor de QR de terceiro lê o código da tela em uma janela de **320px** de largura,
  e o conteúdo lido é idêntico ao código exibido em texto.
- **SC-006**: O código continua legível em texto quando a imagem do QR não carrega.
- **SC-007**: O dono gera o link e o tem pronto para enviar em no máximo **2 interações** a partir do
  ingresso.
- **SC-008**: Pedir o link duas vezes seguidas devolve o mesmo endereço; dois pedidos simultâneos
  produzem exatamente **um** link ativo — verificável por teste automatizado de concorrência que
  **falha** se a garantia do banco for removida.
- **SC-009**: Um link revogado deixa de exibir o ingresso na primeira abertura seguinte, sem
  necessidade de qualquer outra ação.
- **SC-010**: Revogar um link não altera o código do QR do ingresso: o mesmo código continua sendo
  aceito na verificação — verificável por teste automatizado que compara o código antes e depois.
- **SC-011**: Um link novo gerado após uma revogação é diferente do revogado, e o revogado continua
  sem valer.
- **SC-012**: O token do link não coincide com o código do QR, não é derivável dele e não é
  sequencial — verificável por teste automatizado.
- **SC-013**: A resposta pública de um link, inspecionada por inteiro, não contém nome, e-mail ou
  identificador do comprador, nenhum outro ingresso da mesma compra, nenhum valor e nenhum dado de
  pagamento — verificável por teste automatizado obrigatório.
- **SC-014**: Token inexistente e token revogado produzem respostas indistinguíveis entre si.
- **SC-015**: A página compartilhada abre sem autenticação e nunca conduz à entrada.
- **SC-016**: Outro cliente, organizador e portaria recebem recusa do servidor ao tentar listar,
  abrir, gerar e revogar — nas 12 combinações —, e a recusa persiste quando a interface é contornada.
- **SC-017**: A área, o ingresso e a página compartilhada funcionam com o catálogo externo fora do ar.
- **SC-018**: Lista, ingresso e página compartilhada são operáveis apenas por teclado, e o resultado
  de gerar, copiar e revogar é anunciado a tecnologias assistivas.
- **SC-019**: As asserções de teste das features 001–008 continuam passando; qualquer ajuste no
  inventário de navegação da 002 é aditivo.

## Assumptions

- **A fronteira entre futuro e passado é o início da sessão.** Assume-se que um ingresso é "futuro"
  enquanto a sessão não começou. A alternativa — considerar futuro até o fim da exibição — exigiria a
  duração do filme, que é opcional no catálogo desde a 001 e pode ser nula, o que deixaria a
  fronteira indefinida para parte do acervo. O custo da escolha é pequeno e não esconde nada: quem
  chega atrasado encontra o ingresso no grupo dos passados, completo e com o QR intacto. Quando a
  portaria existir, é ela quem decide validade por horário; a lista apenas ordena.

- **Um link ativo por ingresso, e a segunda chamada é idempotente.** Assume-se que pedir o link de um
  ingresso que já tem link ativo devolve o mesmo endereço. Permitir vários links ativos multiplicaria
  credenciais ao portador que o dono teria de revogar uma a uma, e a tela de revogação viraria uma
  lista — complexidade nova sem benefício de produto. "Gerar outro" é explicitamente revogar e criar,
  em duas ações que o dono enxerga.

- **O link não tem prazo próprio.** Assume-se que o link vale até ser revogado. Um prazo criaria um
  segundo motivo de "este link não funciona" para o avaliador distinguir do primeiro, e a utilidade
  do link já acaba sozinha quando a sessão passa. A revogação é o controle, e é suficiente porque é
  imediata e definitiva.

- **Tokens revogados nunca são reaproveitados.** Assume-se que a linha do link revogado é preservada,
  e não apagada, justamente para que o token não possa ser gerado de novo por acaso e para que a
  resposta a um token revogado seja a mesma de um inexistente sem depender de sorte.

- **Um ingresso por linha, sem agrupamento por compra.** Assume-se que a lista não agrupa ingressos
  por reserva. Cada ingresso é uma credencial de entrada distinta, e é assim que ele é usado na fila:
  uma pessoa, um lugar, um código. Ingressos da mesma sessão ficam adjacentes pela própria ordenação,
  o que já entrega a proximidade visual sem inventar um nível de hierarquia.

- **Sem paginação nesta feature.** Assume-se que o volume de ingressos de um cliente do seed cabe
  numa página. Paginar antes de existir volume seria complexidade especulativa; se o volume aparecer,
  a ordenação já definida em FR-007 e FR-008 é o que a paginação futura preservaria.

- **Sem cancelamento, estorno ou transferência de titularidade.** Assume-se que compartilhar é exibir,
  não transferir: o ingresso continua pertencendo a quem comprou. Revenda entre usuários está
  explicitamente fora de escopo pelo Princípio I, e estorno é item posterior ao fluxo completo.

- **Sem envio por e-mail e sem anexo para carteira digital.** O envio de ingresso por e-mail é item
  explicitamente proibido pelo Princípio I. O compartilhamento é o link, e é o mecanismo pedido.

- **A imagem do QR continua sendo derivada do código, não o código.** Assume-se o mesmo entendimento
  registrado na 008: o conteúdo assinado é a fonte da verdade e a imagem é uma representação dele. É
  por isso que o texto aparece junto e que a página compartilhada pode exibir o QR sem inventar nada.

- **O comportamento pós-entrada segue o que a 003 já faz.** Assume-se que o visitante conduzido à
  entrada ao tentar abrir a área retoma a navegação conforme o comportamento de sessão já entregue,
  sem que esta feature invente um mecanismo próprio de retorno.

### Escopo excluído

Estado "já utilizado" e a transição que o escreve · tela de portaria, leitura por câmera e os quatro
desfechos de validação · painel do organizador · cancelamento, estorno e devolução ao estoque ·
transferência de titularidade e revenda · envio de ingresso por e-mail · carteira digital · nota
fiscal · paginação e filtros na lista de ingressos · prazo de validade do link · múltiplos links
ativos por ingresso · registro de quantas vezes um link foi aberto.

### Dependências

- Ingresso emitido com código assinado e confirmação de compra (`008-payment-ticket-issuance`)
- Reserva com `UNIQUE(sessão, assento)` e ocupação por reserva paga (`007-seat-selection`)
- Autenticação com os três papéis e seed dos quatro usuários (`003-user-authentication`, `005`)
- Cabeçalho e navegação global (`002-site-header-navigation`)
- Dados de filme e sessão persistidos localmente (`001-movie-highlights-carousel`)
- Disciplina de tokens (`006-visual-identity`)
