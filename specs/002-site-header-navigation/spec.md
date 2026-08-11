# Feature Specification: Cabeçalho Global do Site

**Feature Branch**: `002-site-header-navigation`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "crie um header com o nome do site "ticket.com", select de localidade, barra de pesquisa e o icone de boneco ( login )."

> **Decisão de escopo de 2026-08-11**: o **seletor de localidade sai desta entrega**. O domínio
> atual não representa cidade nem cinema — uma sala existe sem lugar — e um seletor que não muda
> nada na tela seria exatamente o controle decorativo que o Princípio V da constitution proíbe.
> A localidade volta como feature própria quando houver um conceito de praça no domínio. O
> cabeçalho entregue aqui tem **três** elementos: identidade, busca e acesso à conta.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconhecer onde se está e voltar ao início (Priority: P1)

Um visitante abre qualquer página da plataforma e encontra, no topo, uma faixa que identifica o
site pelo nome **ticket.com**. Essa faixa é a mesma em todas as páginas, e acionar o nome do site
sempre traz a pessoa de volta à página inicial — inclusive quando ela chegou por um link direto
para a página de um filme.

**Why this priority**: Hoje não existe nenhum elemento de navegação persistente: quem entra na
página de um filme por link direto fica sem caminho de volta ao catálogo. É a menor fatia
entregável e é o alicerce estrutural dos outros dois elementos, que vivem dentro dessa faixa.

**Independent Test**: Navegar da página inicial para a página de um filme e confirmar que o
cabeçalho está presente nas duas, com a mesma composição; acionar o nome do site na página do
filme e confirmar o retorno à página inicial.

**Acceptance Scenarios**:

1. **Given** o visitante está na página inicial, **When** a página carrega, **Then** o cabeçalho é
   exibido no topo com o nome **ticket.com**, a barra de pesquisa e o acesso à conta.
2. **Given** o visitante está na página de sessões de um filme, **When** a página carrega,
   **Then** o mesmo cabeçalho é exibido, com os mesmos elementos na mesma ordem.
3. **Given** o visitante está em qualquer página que não a inicial, **When** aciona o nome do
   site, **Then** é levado à página inicial.
4. **Given** o visitante está na página inicial, **When** aciona o nome do site, **Then** permanece
   na página inicial sem recarregamento perceptível nem erro.
5. **Given** o visitante rola a página para baixo, **When** o conteúdo se desloca, **Then** o
   cabeçalho permanece visível e acessível no topo, sem cobrir permanentemente o conteúdo que
   estava sendo lido.
6. **Given** o visitante acessa por uma tela estreita (360px), **When** o cabeçalho é exibido,
   **Then** os três elementos continuam alcançáveis e a página não apresenta rolagem horizontal.
7. **Given** o visitante abre uma página do site, **When** observa o título exibido pelo
   navegador, **Then** o nome **ticket.com** aparece nele, coerente com o cabeçalho.

---

### User Story 2 - Encontrar um filme pelo nome sem sair da página (Priority: P2)

De qualquer página do site, o visitante começa a digitar o nome de um filme na barra de pesquisa
e vê, logo abaixo do campo, uma lista curta de filmes que correspondem ao que ele escreveu.
Acionar um item da lista o leva direto à página daquele filme. Se nada corresponder, a própria
lista informa em português que não houve resultado para aquele termo.

**Why this priority**: É o atalho que transforma o cabeçalho de moldura em ferramenta e o segundo
caminho de entrada para a compra, ao lado do carrossel. Depende do cabeçalho existir (US1), mas
entrega valor sozinho e é testável de forma isolada.

**Independent Test**: Digitar parte do título de um filme que possui sessões publicadas e
confirmar que ele aparece na lista de sugestões; acioná-lo e confirmar a chegada à página do
filme; digitar um termo sem correspondência e confirmar a mensagem de "nenhum resultado".

**Acceptance Scenarios**:

1. **Given** existe um filme cujo título contém o texto digitado, **When** o visitante digita esse
   texto, **Then** o filme aparece na lista de sugestões abaixo do campo, com título e arte
   suficientes para identificá-lo.
2. **Given** a lista de sugestões está aberta, **When** o visitante aciona um dos itens, **Then**
   é levado à página daquele filme e a lista se fecha.
3. **Given** nenhum filme corresponde ao texto digitado, **When** a busca é concluída, **Then** a
   lista exibe uma mensagem em português informando que nada foi encontrado para aquele termo e
   sugerindo a próxima ação.
4. **Given** o campo está vazio ou contém apenas espaços, **When** o visitante para de digitar,
   **Then** nenhuma busca é disparada e nenhuma lista é aberta.
5. **Given** o visitante digita o termo com diferença de acentuação ou de caixa em relação ao
   título cadastrado, **When** a busca é executada, **Then** o filme correspondente ainda aparece
   nas sugestões.
6. **Given** o visitante continua digitando, **When** o texto muda, **Then** a lista passa a
   refletir o texto mais recente, sem exibir o resultado de um termo já abandonado.
7. **Given** o visitante não está autenticado, **When** usa a busca, **Then** a busca funciona
   normalmente, sem exigir entrada na conta.
8. **Given** a lista de sugestões está aberta, **When** o visitante navega por teclado, **Then**
   consegue percorrer os itens, acionar o item em foco com Enter e fechar a lista com Esc, com
   foco visível em cada passo.
9. **Given** a lista de sugestões está aberta, **When** o visitante clica fora do campo ou o campo
   perde o foco, **Then** a lista se fecha sem navegar para lugar nenhum.
10. **Given** o catálogo externo de filmes está indisponível, **When** o visitante busca, **Then**
    a busca continua retornando os filmes já armazenados na plataforma.

---

### User Story 3 - Ver o estado da própria conta a partir de qualquer página (Priority: P3)

O visitante vê no canto do cabeçalho um ícone de pessoa que representa sua conta. Enquanto não
estiver autenticado, o ícone comunica que ali se entra e conduz ao caminho de entrada. Depois de
autenticado, o mesmo ponto passa a identificá-lo em vez de convidá-lo a entrar.

**Why this priority**: O ponto de acesso pertence ao cabeçalho, mas seu destino — a tela de
entrada e o fluxo de autenticação — é entregue pela feature de autenticação. Esta história define
a presença, a semântica e os dois estados; ela só é considerada concluída quando o destino
existir.

**Independent Test**: Confirmar que, como visitante, o ícone está presente, é anunciado por sua
função e conduz ao caminho de entrada; e que, com uma conta autenticada, o cabeçalho apresenta o
estado identificado em vez do convite para entrar.

**Acceptance Scenarios**:

1. **Given** o visitante não está autenticado, **When** o cabeçalho é exibido, **Then** o ícone de
   pessoa é apresentado com um nome acessível em português que comunica a ação de entrar.
2. **Given** o visitante não está autenticado, **When** aciona o ícone, **Then** é conduzido ao
   caminho de entrada na conta.
3. **Given** o visitante está autenticado, **When** o cabeçalho é exibido, **Then** o ponto de
   conta comunica que existe uma sessão ativa e identifica de quem é, em vez de convidar a entrar.
4. **Given** a autenticação do visitante deixa de valer enquanto ele navega, **When** o cabeçalho é
   exibido de novo, **Then** volta ao estado de visitante em vez de mostrar dados de uma sessão
   que já não existe.
5. **Given** o visitante navega apenas por teclado ou usa leitor de tela, **When** alcança o ícone,
   **Then** o elemento é anunciado por sua função, não como imagem sem descrição.

---

### Edge Cases

- **Tela estreita**: o cabeçalho preserva o nome **ticket.com** legível e reorganiza busca e conta
  sem truncar o nome do site e sem gerar rolagem horizontal.
- **Busca lenta**: enquanto os resultados não chegam, o visitante recebe indicação de que a busca
  está em andamento, em vez de uma lista vazia que parece "nenhum resultado".
- **Falha na busca**: a lista informa em português que a busca não pôde ser concluída e oferece
  nova tentativa; o termo digitado não é perdido e o restante do cabeçalho continua funcionando.
- **Muitos filmes correspondem ao termo**: a lista apresenta um número limitado de sugestões e
  deixa explícito que está mostrando as mais relevantes, em vez de despejar o catálogo inteiro.
- **Termo de um único caractere**: a busca é aceita, respeitando o limite de sugestões acima.
- **Termo muito longo**: o campo limita a entrada a um tamanho razoável, sem travar nem descartar
  silenciosamente o que foi digitado.
- **Filme encontrado sem sessões à venda**: o filme ainda aparece nas sugestões, e a página de
  destino é quem comunica a indisponibilidade — a busca não mente sobre o catálogo.
- **Respostas fora de ordem**: se uma busca antiga responder depois de uma mais recente, a lista
  exibe o resultado do termo atual, nunca o do termo já abandonado.
- **Usuário com preferência de movimento reduzido**: a abertura e o fechamento da lista de
  sugestões ocorrem sem animação.
- **Impressão da página**: o cabeçalho não sobrepõe conteúdo impresso.

## Requirements *(mandatory)*

### Functional Requirements

**Presença e estrutura**

- **FR-001**: O sistema DEVE exibir um cabeçalho no topo de todas as páginas públicas da
  plataforma, com a mesma composição e a mesma ordem de elementos em todas elas.
- **FR-002**: O cabeçalho DEVE exibir o nome do site **ticket.com** como elemento de identidade, e
  acioná-lo DEVE levar o visitante à página inicial.
- **FR-003**: O cabeçalho DEVE conter exatamente três elementos funcionais: identidade do site,
  barra de pesquisa e ponto de acesso à conta.
- **FR-004**: O título exibido pelo navegador DEVE conter o nome **ticket.com**, coerente com a
  identidade apresentada no cabeçalho.
- **FR-005**: O cabeçalho DEVE permanecer utilizável de 360px a 1920px de largura, sem provocar
  rolagem horizontal na página e sem tornar qualquer um dos três elementos inalcançável.
- **FR-006**: O cabeçalho DEVE permanecer visível durante a rolagem da página, sem cobrir
  permanentemente o conteúdo que o visitante está lendo.

**Busca**

- **FR-007**: O sistema DEVE oferecer um campo de busca alcançável a partir de qualquer página,
  com rótulo em português que informe o que pode ser buscado.
- **FR-008**: A busca DEVE localizar filmes pelo título, ignorando diferenças de caixa e de
  acentuação, e DEVE encontrar correspondências parciais — não apenas o título completo.
- **FR-009**: O sistema DEVE apresentar os resultados como uma lista de sugestões ancorada ao
  campo de busca dentro do próprio cabeçalho, sem navegar para uma página de resultados.
- **FR-010**: Cada sugestão DEVE identificar o filme por título e arte, e acioná-la DEVE levar o
  visitante à página daquele filme.
- **FR-011**: O sistema DEVE limitar o número de sugestões exibidas por vez e, quando houver mais
  correspondências do que o limite, DEVE comunicar que está exibindo apenas parte delas.
- **FR-012**: O sistema DEVE exibir um estado de "nenhum resultado" escrito em português, dizendo
  o que foi buscado e qual a próxima ação possível.
- **FR-013**: O sistema DEVE indicar que a busca está em andamento enquanto os resultados não
  chegam, de forma distinguível do estado "nenhum resultado".
- **FR-014**: O sistema NÃO DEVE disparar busca quando o termo estiver vazio ou contiver apenas
  espaços, e DEVE fechar a lista nesse caso.
- **FR-015**: A lista de sugestões DEVE sempre corresponder ao termo mais recente digitado, mesmo
  que uma consulta anterior responda depois.
- **FR-016**: A busca DEVE operar sobre os dados de filmes já armazenados na plataforma,
  continuando a funcionar quando o catálogo externo estiver indisponível.
- **FR-017**: A busca DEVE estar disponível a visitantes não autenticados.
- **FR-018**: Quando a busca falhar, o sistema DEVE informar o ocorrido em português, preservar o
  termo digitado e permitir nova tentativa.
- **FR-019**: A lista de sugestões DEVE fechar quando o visitante acionar Esc, clicar fora do
  cabeçalho ou navegar para outra página.

**Acesso à conta**

- **FR-020**: O cabeçalho DEVE apresentar um ícone de pessoa como ponto de acesso à conta, com
  nome acessível em português que descreva sua função.
- **FR-021**: O ponto de acesso à conta DEVE ter dois estados distintos e diferenciáveis:
  visitante não autenticado e visitante autenticado, este último identificando de quem é a sessão.
- **FR-022**: Esta feature DEVE entregar o ponto de acesso e seus dois estados; a tela de entrada,
  o fluxo de autenticação e a saída da conta pertencem à feature de autenticação.
- **FR-023**: O ponto de acesso NÃO PODE conduzir a um destino inexistente. A US3 só é considerada
  concluída quando o caminho de entrada definido aqui existir e responder.
- **FR-024**: Quando a sessão do visitante deixar de valer, o cabeçalho DEVE voltar ao estado de
  visitante não autenticado.
- **FR-025**: O cabeçalho NÃO PODE ser tratado como mecanismo de controle de acesso: exibir ou
  esconder elementos conforme o estado de autenticação é apresentação, e toda autorização continua
  sendo decidida no servidor.

**Interface, acessibilidade e resiliência**

- **FR-026**: Todos os elementos interativos do cabeçalho DEVEM ser operáveis por teclado, na
  ordem visual, com indicador de foco visível.
- **FR-027**: O cabeçalho DEVE ser exposto a tecnologias assistivas como região de navegação do
  site; a lista de sugestões DEVE anunciar a chegada e a quantidade de resultados; e o ícone de
  pessoa DEVE ser anunciado por sua função, não como imagem sem descrição.
- **FR-028**: Nenhum estado do cabeçalho DEVE ser comunicado apenas por cor.
- **FR-029**: A falha de um elemento do cabeçalho NÃO PODE impedir o funcionamento dos demais.
- **FR-030**: Cor, tipografia e espaçamento do cabeçalho DEVEM vir dos tokens de design já
  definidos no projeto, sem valores ad-hoc.
- **FR-031**: O cabeçalho NÃO PODE conter texto de placeholder, rótulo genérico ou área marcada
  como indisponível/em breve na entrega final.
- **FR-032**: Transições do cabeçalho DEVEM ser suprimidas quando o visitante tiver configurado
  preferência por movimento reduzido.

### Key Entities

- **Termo de busca**: texto informado pelo visitante para encontrar filmes. Não é persistido como
  dado do domínio; existe apenas durante a interação.
- **Sugestão de filme**: filme que corresponde ao termo, apresentado com o mínimo necessário para
  identificação (título e arte) e com o caminho para sua página. Deriva dos filmes já armazenados
  na plataforma.
- **Estado de autenticação do visitante**: informação de que existe ou não uma sessão ativa e de
  quem é, usada apenas para decidir o que o cabeçalho apresenta — nunca para autorizar.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O cabeçalho está presente e íntegro em 100% das páginas públicas da plataforma.
- **SC-002**: A partir de qualquer página, o visitante volta à página inicial em 1 interação.
- **SC-003**: Um visitante que sabe o nome do filme chega à página desse filme em no máximo 2
  interações a partir de qualquer página, sem passar por uma página intermediária de resultados.
- **SC-004**: As sugestões refletem o termo digitado em até 1 segundo após a pausa na digitação,
  em conexão de banda larga comum.
- **SC-005**: A lista de sugestões nunca exibe resultado de um termo diferente do que está no
  campo no momento.
- **SC-006**: Todos os elementos interativos do cabeçalho são alcançáveis e operáveis usando
  apenas o teclado, sem armadilha de foco, incluindo percorrer e acionar as sugestões.
- **SC-007**: O cabeçalho permanece utilizável e sem rolagem horizontal em larguras de tela de
  360px a 1920px.
- **SC-008**: Nenhum estado do cabeçalho (buscando, vazio, erro, sem resultados, não autenticado)
  exibe texto genérico do tipo "algo deu errado" ou área em branco sem explicação.
- **SC-009**: A busca continua devolvendo resultados quando o catálogo externo está indisponível.

## Assumptions

- **Nome do site**: "ticket.com" é o nome de marca apresentado no cabeçalho, escrito exatamente
  assim. Não implica registro, posse ou link para o domínio `ticket.com` na internet, e o
  cabeçalho não deve sugerir associação com qualquer empresa existente de nome semelhante.
- **Escopo da "barra de pesquisa"**: busca por filmes do catálogo pelo título, com resultados
  apresentados como sugestões no próprio cabeçalho — decisão do usuário em 2026-08-11. Busca por
  sessão, data, sala ou gênero, e página dedicada de resultados, não fazem parte desta entrega.
- **Escopo do "ícone de boneco"**: ponto de acesso à conta com dois estados. Login, logout,
  cadastro e edição de perfil pertencem à feature de autenticação — decisão do usuário em
  2026-08-11. A constitution já coloca recuperação de senha fora de escopo.
- **Seletor de localidade**: fora do escopo desta entrega por decisão do usuário em 2026-08-11.
  Volta quando o domínio representar praças/cinemas, o que hoje não acontece: uma sala existe sem
  lugar associado.
- **Idioma**: todo o texto do cabeçalho e todas as suas mensagens de erro são em português do
  Brasil.
- **Papéis**: o cabeçalho é o mesmo para os três papéis do sistema. Diferenciação de navegação por
  papel (organizador, cliente, portaria) não faz parte desta entrega.
- **Base de dados da busca**: os filmes já sincronizados e armazenados na plataforma, coerente com
  o Princípio VII da constitution — a indisponibilidade do catálogo externo não pode derrubar a
  navegação.
- **Escopo excluído**: menu de categorias, rodapé, breadcrumb, notificações, carrinho e alternância
  de tema não fazem parte desta feature.

## Dependencies

- **Feature de autenticação**: fornece a tela de entrada, o fluxo de login/logout e a informação de
  sessão ativa consumida pelo cabeçalho. A US1 e a US2 não dependem dela e podem ser entregues
  antes; a US3 depende dela para ser considerada concluída (FR-023).
- **Catálogo de filmes existente**: a busca lê os filmes já armazenados pela feature
  `001-movie-highlights-carousel`. Nenhum filme novo é criado por esta feature.
