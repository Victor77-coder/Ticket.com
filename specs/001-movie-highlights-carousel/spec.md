# Feature Specification: Carrossel de Highlights de Filmes

**Feature Branch**: `001-movie-highlights-carousel`

**Created**: 2026-08-10

**Status**: Draft

**Input**: User description: "crie o carrossel com os highlights de cada filme disponivel na api externa ( são 5 ) com o botão de "ver ingressos" e "trailer" ( ao apertar neste botão, o trailer deve abrir dentro do proprio highlight ), a porta do banco de dados a ser utilizada deve ser 5438 e a porta do localhost deve ser a 5000."

> **Emenda de 2026-08-10**: a porta da interface web passou de 5000 para **5003**. O macOS
> mantém o AirPlay Receiver escutando na 5000 por padrão, e o serviço `ControlCenter` intercepta
> as requisições antes do Docker, respondendo 403. Decisão do usuário após o conflito ser
> diagnosticado.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Descobrir os filmes em cartaz na entrada do site (Priority: P1)

Um visitante abre a página inicial da plataforma e é recebido por um painel grande e rotativo
que apresenta, um de cada vez, os 5 filmes em cartaz. Cada painel mostra a arte do filme, o
título, a classificação, a duração, o gênero e uma sinopse curta — informação suficiente para
que a pessoa decida se aquele filme interessa antes de clicar em qualquer coisa.

**Why this priority**: É a primeira coisa que qualquer avaliador ou cliente vê ao abrir a
aplicação. Sem ela não existe ponto de entrada para o fluxo de compra, e é a superfície onde a
"interface autoral" exigida pelo Princípio V da constitution fica mais visível.

**Independent Test**: Abrir a página inicial sem estar autenticado e confirmar que os 5 filmes
aparecem, que é possível avançar e voltar entre eles, e que cada painel exibe todos os dados
descritos acima.

**Acceptance Scenarios**:

1. **Given** existem 5 filmes em cartaz com sessões publicadas, **When** o visitante abre a
   página inicial, **Then** o carrossel exibe o primeiro filme com arte, título, classificação,
   duração, gênero e sinopse curta.
2. **Given** o carrossel está exibindo o primeiro filme, **When** o visitante aciona o controle
   de avançar, **Then** o segundo filme é exibido e o indicador de posição atualiza para 2 de 5.
3. **Given** o carrossel está exibindo o último filme, **When** o visitante aciona o controle de
   avançar, **Then** o carrossel volta ao primeiro filme (navegação circular).
4. **Given** o visitante não interage com o carrossel, **When** transcorre o intervalo de
   rotação automática, **Then** o carrossel avança sozinho para o próximo filme.
5. **Given** o carrossel está rotacionando sozinho, **When** o visitante posiciona o ponteiro
   sobre o painel ou navega por teclado até um de seus controles, **Then** a rotação automática
   pausa e só retoma quando o foco e o ponteiro saírem da área.
6. **Given** o visitante acessa por um dispositivo móvel, **When** desliza horizontalmente sobre
   o painel, **Then** o carrossel avança ou retrocede conforme a direção do gesto.

---

### User Story 2 - Assistir ao trailer sem sair da página (Priority: P2)

Ao ver um filme que desperta interesse, o visitante aciona o botão "Trailer". O trailer começa
a ser reproduzido dentro do próprio painel do carrossel — ocupando o espaço da arte do filme,
sem abrir uma janela sobreposta e sem levar o visitante para fora da plataforma. Ele pode
encerrar a reprodução e voltar ao painel normal a qualquer momento.

**Why this priority**: É o que transforma o carrossel de uma vitrine estática em uma ferramenta
real de decisão de compra. Depende do painel existir (US1), mas entrega valor sozinho.

**Independent Test**: Acionar "Trailer" em um filme que possua trailer e confirmar que o vídeo
reproduz dentro do painel; encerrar e confirmar que o painel volta ao estado original.

**Acceptance Scenarios**:

1. **Given** o filme exibido possui trailer disponível, **When** o visitante aciona "Trailer",
   **Then** o trailer inicia a reprodução dentro da área do próprio painel, substituindo a arte
   do filme, sem abrir janela sobreposta e sem redirecionar para outro site.
2. **Given** o trailer está em reprodução, **When** a reprodução começa, **Then** a rotação
   automática do carrossel é suspensa e permanece suspensa enquanto o vídeo estiver ativo.
3. **Given** o trailer está em reprodução, **When** o visitante aciona o controle de fechar,
   **Then** o vídeo para, o painel volta a exibir a arte do filme e a rotação automática é
   retomada.
4. **Given** o trailer está em reprodução, **When** o visitante navega para outro filme do
   carrossel, **Then** o trailer anterior para de tocar e o novo painel abre no estado de arte.
5. **Given** o filme exibido não possui trailer disponível, **When** o painel é exibido,
   **Then** o botão "Trailer" não é apresentado, e o botão "Ver ingressos" ocupa o painel
   sozinho sem deixar espaço vazio no layout.
6. **Given** o trailer falha ao carregar, **When** o erro ocorre, **Then** o painel exibe uma
   mensagem em português explicando que o trailer está indisponível e oferece o retorno à arte
   do filme, mantendo "Ver ingressos" acessível.

---

### User Story 3 - Ir do highlight direto para a compra (Priority: P1)

O visitante decide comprar e aciona "Ver ingressos" no painel do filme. Ele é levado à página
daquele filme, onde vê as sessões disponíveis e pode iniciar a reserva.

**Why this priority**: É a razão de o carrossel existir. Um highlight que não conduz à compra
seria exatamente a "tela pela metade" que o Princípio I da constitution proíbe. Compartilha a
prioridade P1 com a US1 porque as duas juntas formam a menor fatia entregável de valor.

**Independent Test**: Acionar "Ver ingressos" em cada um dos 5 filmes e confirmar que cada um
leva à página do filme correto, com ao menos uma sessão disponível listada.

**Acceptance Scenarios**:

1. **Given** o carrossel exibe um filme, **When** o visitante aciona "Ver ingressos", **Then**
   ele é levado à página daquele filme específico, com as sessões disponíveis listadas.
2. **Given** o trailer está em reprodução no painel, **When** o visitante aciona "Ver
   ingressos", **Then** o trailer para e a navegação para a página do filme acontece.
3. **Given** o visitante não está autenticado, **When** aciona "Ver ingressos", **Then** ele
   consegue ver as sessões do filme sem precisar entrar na conta — a autenticação só é exigida
   no momento de reservar.

---

### Edge Cases

- **Menos de 5 filmes qualificados**: o carrossel exibe quantos existirem, ajustando o indicador
  de posição ao total real. Com apenas 1 filme, os controles de avançar/retroceder e a rotação
  automática não são apresentados.
- **Nenhum filme qualificado**: o carrossel é substituído por um estado vazio escrito em
  português, que explica que não há filmes em cartaz no momento — nunca por um painel em branco,
  esqueleto infinito ou mensagem genérica de erro.
- **Mais de 5 filmes qualificados**: apenas 5 são destacados, seguindo o critério de ordenação
  definido em FR-002.
- **Catálogo externo indisponível**: como os dados do filme já estão armazenados na plataforma,
  o carrossel continua funcionando normalmente. Apenas a reprodução do trailer pode ficar
  indisponível, e nesse caso vale o cenário 6 da US2.
- **Imagem de arte ausente ou que falha ao carregar**: o painel exibe um plano de fundo de
  fallback com o título legível, preservando o contraste do texto e dos botões.
- **Sessões esgotadas durante a navegação**: o filme permanece no carrossel, mas o botão passa a
  indicar que não há ingressos disponíveis, sem quebrar o layout do painel.
- **Conexão lenta**: enquanto o conteúdo carrega, o carrossel exibe um estado de carregamento
  com as mesmas dimensões do painel final, para que o restante da página não salte quando o
  conteúdo chegar.
- **Usuário com preferência de movimento reduzido**: a rotação automática e as transições
  animadas são desativadas; a navegação manual continua funcionando.
- **Navegação apenas por teclado**: todos os controles (avançar, retroceder, ir para um índice,
  "Trailer", "Ver ingressos", fechar trailer) são alcançáveis por teclado, com foco visível.

## Requirements *(mandatory)*

### Functional Requirements

**Composição do carrossel**

- **FR-001**: O sistema DEVE exibir na página inicial um carrossel com no máximo 5 filmes em
  destaque, um painel visível por vez.
- **FR-002**: O sistema DEVE selecionar os filmes destacados entre aqueles que possuem ao menos
  uma sessão publicada e futura, ordenando pela sessão disponível mais próxima no tempo e
  limitando o resultado a 5.
- **FR-003**: Cada painel DEVE exibir arte de destaque, título, classificação indicativa,
  duração, gênero e uma sinopse curta do filme.
- **FR-004**: Cada painel DEVE exibir exatamente dois botões de ação: "Ver ingressos" e
  "Trailer", com "Ver ingressos" visualmente identificável como a ação principal.
- **FR-005**: O sistema DEVE indicar visualmente qual painel está ativo e quantos painéis
  existem no total.

**Navegação**

- **FR-006**: O visitante DEVE poder avançar e retroceder entre os painéis por controles
  visíveis, por gesto de deslize em telas de toque e pelas setas do teclado.
- **FR-007**: O visitante DEVE poder saltar diretamente para um painel específico pelo indicador
  de posição.
- **FR-008**: A navegação DEVE ser circular: avançar no último painel leva ao primeiro, e
  retroceder no primeiro leva ao último.
- **FR-009**: O carrossel DEVE avançar automaticamente em intervalo fixo enquanto não houver
  interação.
- **FR-010**: A rotação automática DEVE pausar quando o ponteiro estiver sobre o carrossel,
  quando qualquer controle interno receber foco de teclado, ou quando um trailer estiver em
  reprodução — e retomar quando essas condições cessarem.
- **FR-011**: O sistema DEVE desativar a rotação automática e as transições animadas quando o
  visitante tiver configurado preferência por movimento reduzido.

**Trailer**

- **FR-012**: Ao acionar "Trailer", o sistema DEVE reproduzir o trailer dentro da área do painel
  do filme correspondente, sem abrir janela sobreposta e sem navegar para fora da plataforma.
- **FR-013**: O sistema DEVE oferecer um controle explícito para encerrar o trailer e retornar o
  painel ao estado de arte do filme.
- **FR-014**: O sistema DEVE interromper a reprodução do trailer ao navegar para outro painel ou
  ao sair do carrossel.
- **FR-015**: O sistema DEVE ocultar o botão "Trailer" para filmes sem trailer disponível,
  reorganizando o painel para não deixar lacuna visual.
- **FR-016**: No máximo um trailer DEVE estar em reprodução por vez em toda a página.
- **FR-017**: O trailer NÃO DEVE iniciar reprodução automaticamente — só após ação explícita do
  visitante — e DEVE iniciar com som apenas se o visitante o acionou diretamente.

**Caminho para a compra**

- **FR-018**: Ao acionar "Ver ingressos", o sistema DEVE levar o visitante à página do filme
  exibido no painel ativo, com as sessões disponíveis listadas.
- **FR-019**: O carrossel DEVE ser acessível a visitantes não autenticados; nenhuma ação do
  carrossel pode exigir login.
- **FR-020**: Quando um filme destacado não tiver mais ingressos disponíveis, o sistema DEVE
  comunicar isso no próprio painel em vez de conduzir a uma página sem sessões compráveis.

**Estados e resiliência**

- **FR-021**: O sistema DEVE exibir um estado de carregamento com as mesmas dimensões do painel
  final, evitando deslocamento do conteúdo da página quando os dados chegarem.
- **FR-022**: O sistema DEVE exibir um estado vazio explicativo em português quando não houver
  nenhum filme qualificado para destaque.
- **FR-023**: O carrossel DEVE continuar exibindo os filmes destacados mesmo quando o catálogo
  externo estiver indisponível, usando os dados já armazenados na plataforma.
- **FR-024**: Toda mensagem de erro apresentada pelo carrossel DEVE ser escrita em português,
  dizendo o que aconteceu e qual a próxima ação possível.

**Acessibilidade**

- **FR-025**: Todos os controles do carrossel DEVEM ser operáveis por teclado, com indicador de
  foco visível.
- **FR-026**: A mudança de painel DEVE ser anunciada a tecnologias assistivas, e as imagens de
  arte DEVEM ter texto alternativo descritivo.
- **FR-027**: O texto sobreposto à arte do filme DEVE manter contraste legível independentemente
  da imagem de fundo.

### Key Entities

- **Filme em destaque**: representa um filme apresentado no carrossel. Reúne os dados de
  identidade e apresentação (título, sinopse curta, arte de destaque, classificação indicativa,
  duração, gênero), a referência ao trailer quando existir, e o vínculo com as sessões que o
  tornam elegível ao destaque. Os dados de apresentação ficam armazenados na plataforma, não são
  buscados no catálogo externo a cada visita.
- **Trailer**: recurso de vídeo associado a um filme. Pode não existir. É o que habilita ou
  oculta o botão "Trailer" no painel.
- **Sessão**: exibição agendada de um filme, com data, hora e disponibilidade. Determina se um
  filme é elegível ao destaque (FR-002) e é o destino do botão "Ver ingressos".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um visitante que abre a página inicial identifica os filmes em cartaz e alcança a
  página de sessões de um deles em no máximo 2 interações.
- **SC-002**: O conteúdo do primeiro painel fica visível e legível em até 2 segundos após a
  abertura da página inicial, em conexão de banda larga comum.
- **SC-003**: O trailer começa a ser reproduzido em até 3 segundos após o visitante acionar o
  botão "Trailer".
- **SC-004**: 100% dos filmes destacados conduzem a uma página de filme com ao menos uma sessão
  comprável no momento em que foram destacados.
- **SC-005**: Todos os controles do carrossel são alcançáveis e operáveis usando apenas o
  teclado, sem armadilha de foco.
- **SC-006**: O carrossel permanece funcional e navegável quando o catálogo externo está
  indisponível, degradando apenas a reprodução do trailer.
- **SC-007**: O layout do carrossel permanece utilizável e sem rolagem horizontal indesejada em
  larguras de tela de 360px a 1920px.
- **SC-008**: Nenhum estado do carrossel (carregando, vazio, erro, sem trailer, esgotado) exibe
  texto genérico do tipo "algo deu errado" ou área em branco sem explicação.

## Assumptions

- **Origem e quantidade dos 5 filmes**: o pedido menciona "5 filmes disponíveis na API externa".
  Assume-se que os 5 destaques são os filmes já trazidos do catálogo externo (TMDb) para dentro
  da plataforma e que possuem sessões publicadas — não uma consulta ao vivo ao catálogo externo
  a cada visita. Essa leitura concilia o pedido com o Princípio VII da constitution (a queda do
  catálogo externo não pode derrubar o fluxo de venda) e com o Princípio I (nenhum destaque pode
  levar a uma página sem sessões). Os dados de seed devem, portanto, conter ao menos 5 filmes
  com sessões publicadas.
- **Reprodução "dentro do próprio highlight"**: interpretado como o trailer ocupando a área do
  painel ativo, substituindo a arte do filme, sem janela sobreposta (modal) e sem sair da
  plataforma. O trailer é hospedado por terceiro (o catálogo externo fornece a referência), mas
  a moldura de reprodução fica contida no painel.
- **Intervalo de rotação automática**: assume-se algo em torno de 7 segundos por painel — tempo
  suficiente para ler a sinopse curta sem prender o visitante. Valor exato a definir no plano.
- **Autenticação**: o carrossel é público. A exigência de login ocorre apenas ao reservar, já
  coberta por outra feature.
- **Idioma**: toda a interface e as mensagens de erro deste carrossel são em português do
  Brasil.
- **Escopo excluído**: este spec não cobre a página de detalhe do filme, a listagem de sessões,
  a seleção de assentos nem o checkout. O carrossel apenas conduz até a página do filme.

### Restrições de Ambiente

Estas portas foram determinadas pelo usuário e valem para todo o ambiente de desenvolvimento do
projeto, não apenas para esta feature. Devem ser refletidas na configuração, no `.env.example`
e nas instruções do README.

- **Banco de dados**: porta **5438**.
- **Aplicação acessada pelo navegador (`localhost`)**: porta **5003**. Assume-se que se refere à
  interface web que o visitante e o avaliador abrem no navegador. O serviço de back-end
  permanece em sua porta própria, a ser fixada no plano.
