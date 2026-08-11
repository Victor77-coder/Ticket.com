# Feature Specification: Trilhas de Filmes na Home

**Feature Branch**: `main` (o projeto trabalha sem branches de feature)

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "feature-movies, agora vamos popular a tela inical com os filmes "em alta", "em cartaz", e "em breve". faca cards em horizontal com os posters dos filmes. se a api fornecer a informacão dos filmes que estão em alta, em cartaz e em breve, pegue da api. se não, busque os filmes da api e pegue informacoes se eles estao em cartaz (atualmente) e se sairão em breve. "em alta" se não tive informacoes, pode selecionar 9 filmes."

> **A condicional do pedido não chega a ser acionada.** O catálogo externo fornece as três
> classificações nativamente: filmes em alta da semana, filmes em cartaz por região e filmes com
> estreia futura por região — este último inclusive devolvendo a janela de datas que considerou.
> Não é preciso derivar nada a partir de datas de lançamento. Em consequência, os "9 filmes" que o
> pedido reservava como plano B viram **limite de exibição** da trilha Em alta, não recurso de
> emergência.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Percorrer o que dá para comprar agora (Priority: P1)

Abaixo do painel de destaques, o visitante encontra uma trilha horizontal chamada **Em cartaz**
com os cartazes dos filmes que têm sessão à venda. Ele desliza a trilha, reconhece um filme pelo
cartaz e o aciona para ver as sessões.

**Why this priority**: É a trilha que sustenta o negócio. O carrossel destaca cinco filmes; esta
trilha mostra **todo** o catálogo comprável, que é o que transforma a home de vitrine em ponto de
partida real da compra.

**Independent Test**: Abrir a home e confirmar que a trilha Em cartaz lista os filmes com sessão
publicada e futura, e que acionar qualquer cartaz leva à página daquele filme com sessões
listadas.

**Acceptance Scenarios**:

1. **Given** existem filmes com sessão publicada e futura, **When** o visitante abre a home,
   **Then** a trilha **Em cartaz** exibe os cartazes desses filmes, ordenados pela sessão mais
   próxima.
2. **Given** a trilha Em cartaz é exibida, **When** o visitante aciona um cartaz, **Then** é
   levado à página daquele filme, com as sessões disponíveis listadas.
3. **Given** um filme já aparece no painel de destaques, **When** ele também tem sessão à venda,
   **Then** ele aparece **também** na trilha Em cartaz — as duas superfícies não se excluem.
4. **Given** um filme perdeu a última sessão futura, **When** a home é carregada, **Then** ele não
   aparece mais na trilha Em cartaz.
5. **Given** nenhum filme tem sessão à venda, **When** a home é carregada, **Then** a trilha Em
   cartaz não é exibida — nunca um título de seção com espaço vazio embaixo.

---

### User Story 2 - Descobrir o que está em alta e o que estreia em breve (Priority: P2)

O visitante rola a home e encontra mais duas trilhas: **Em alta**, com os filmes mais comentados
da semana, e **Em breve**, com os que ainda vão estrear. Ele usa as duas para descobrir títulos
que talvez não conhecesse, mesmo que ainda não possa comprar ingresso para eles.

**Why this priority**: Dá profundidade de catálogo à home e é o que diferencia a plataforma de uma
simples lista de sessões. Depende da mesma estrutura de trilha da US1, mas entrega valor sozinha.

**Independent Test**: Abrir a home e confirmar que as trilhas Em alta e Em breve exibem filmes,
que Em alta traz no máximo 9 e que acionar qualquer cartaz leva à página do filme correspondente.

**Acceptance Scenarios**:

1. **Given** o catálogo tem filmes classificados como em alta, **When** o visitante abre a home,
   **Then** a trilha **Em alta** exibe no máximo **9** cartazes.
2. **Given** o catálogo tem filmes com estreia futura, **When** o visitante abre a home, **Then**
   a trilha **Em breve** exibe esses filmes ordenados pela estreia mais próxima.
3. **Given** um filme aparece em mais de uma trilha, **When** a home é carregada, **Then** ele é
   exibido em todas em que se qualifica — a repetição é aceita.
4. **Given** uma trilha não tem nenhum filme, **When** a home é carregada, **Then** aquela trilha
   é omitida por inteiro, sem deixar título órfão.
5. **Given** nenhuma das trilhas tem filme algum, **When** a home é carregada, **Then** a home
   exibe um estado explicativo em português, e não uma página em branco.

---

### User Story 3 - Navegar as trilhas em qualquer dispositivo (Priority: P2)

O visitante desliza as trilhas com o dedo no celular, com a roda ou os controles no computador, e
percorre tudo apenas pelo teclado quando prefere. Em nenhum caso a página inteira desliza para o
lado.

**Why this priority**: Trilha horizontal quebrada é o defeito mais comum desse padrão, e o
Princípio V da constitution cobra interface autoral justamente onde é fácil entregar o genérico.

**Independent Test**: Percorrer as trilhas por gesto, por controle e só pelo teclado, em telas de
360px e 1920px, confirmando que a página nunca rola horizontalmente.

**Acceptance Scenarios**:

1. **Given** uma trilha tem mais cartazes do que cabem na tela, **When** o visitante desliza
   horizontalmente sobre ela, **Then** a trilha avança e o restante da página permanece parado.
2. **Given** uma trilha em tela larga, **When** há conteúdo além da borda, **Then** controles de
   avançar e retroceder são apresentados; quando tudo cabe, eles não aparecem.
3. **Given** o visitante navega por teclado, **When** o foco entra em uma trilha, **Then** cada
   cartaz é alcançável na ordem visual e a trilha acompanha o foco.
4. **Given** qualquer largura entre 360px e 1920px, **When** a home é exibida, **Then** não há
   rolagem horizontal da página.
5. **Given** o visitante configurou preferência por movimento reduzido, **When** navega pelas
   trilhas, **Then** o deslocamento acontece sem animação.

---

### User Story 4 - Entender por que um filme não tem sessão (Priority: P3)

O visitante aciona um filme que ainda vai estrear. A página o recebe com a mesma composição de
qualquer outro filme — cartaz, título, sinopse, duração, classificação e gênero —, informa a data
de estreia e explica que ainda não há sessões programadas.

**Why this priority**: Fecha o caminho das trilhas Em alta e Em breve, que naturalmente levam a
filmes sem sessão. Sem ela o visitante chega a uma página que só diz "não tem nada" — mas é P3
porque as três trilhas já entregam valor sem ela.

**Independent Test**: Acionar um filme sem sessão a partir da trilha Em breve e confirmar que a
página exibe a composição completa, a data de estreia e a explicação.

**Acceptance Scenarios**:

1. **Given** um filme sem sessão programada e com data de estreia conhecida, **When** o visitante
   abre sua página, **Then** vê a mesma composição dos demais filmes e a mensagem informando a
   data de estreia e a ausência de sessões.
2. **Given** um filme sem sessão e **sem** data de estreia conhecida, **When** o visitante abre
   sua página, **Then** a mensagem informa a ausência de sessões sem inventar data.
3. **Given** um filme com data de estreia no passado e sem sessão, **When** o visitante abre sua
   página, **Then** a página não anuncia estreia futura; informa apenas a ausência de sessões.

---

### Edge Cases

- **Trilha vazia**: omitida por inteiro. Título de seção sem cartazes embaixo é pior do que seção
  nenhuma.
- **Todas as trilhas vazias**: a home exibe estado explicativo em português dizendo que a
  programação ainda não foi publicada.
- **Menos filmes do que cabem na tela**: a trilha exibe os que existirem, alinhados à esquerda,
  sem esticar os cartazes nem exibir espaços fantasma.
- **Filme sem cartaz**: exibe um substituto com o título legível, mantendo a mesma proporção dos
  demais para não desalinhar a trilha.
- **Filme repetido em duas trilhas**: permitido e esperado.
- **Filme em alta que também está em cartaz**: aparece nas duas; a trilha Em cartaz continua sendo
  a única que promete compra.
- **Catálogo externo indisponível**: as trilhas continuam funcionando com o que já está
  armazenado. Só a atualização da classificação fica pendente até a próxima sincronização.
- **Data de estreia no passado, mas sem sessão**: a página não anuncia estreia futura; informa
  apenas a ausência de sessões.
- **Carregamento lento**: cada trilha exibe um estado de carregamento com a mesma altura da trilha
  final, para que a página não salte quando os cartazes chegarem.
- **Trilha mais longa que a memória do visitante**: a posição de rolagem de cada trilha é
  independente das demais e não é restaurada entre visitas.

## Requirements *(mandatory)*

### Composição das trilhas

- **FR-001**: A home DEVE exibir, abaixo do painel de destaques, até três trilhas horizontais
  rotuladas **Em cartaz**, **Em alta** e **Em breve**, nesta ordem.
- **FR-002**: A trilha **Em cartaz** DEVE conter os filmes com ao menos uma sessão publicada e
  futura na plataforma, ordenados pela sessão mais próxima.
- **FR-003**: A trilha **Em alta** DEVE conter os filmes classificados como em alta pelo catálogo
  externo, limitada a **9** filmes.
- **FR-004**: A trilha **Em breve** DEVE conter os filmes com estreia futura segundo o catálogo
  externo, ordenados pela estreia mais próxima.
- **FR-005**: Um filme que se qualifica para mais de uma trilha DEVE aparecer em todas elas.
- **FR-006**: Uma trilha sem nenhum filme DEVE ser omitida por completo, incluindo seu título.
- **FR-007**: Quando nenhuma trilha tiver filmes, a home DEVE exibir um estado explicativo em
  português.

### Cartão do filme

- **FR-008**: Cada cartão DEVE exibir o cartaz do filme como elemento principal.
- **FR-009**: Cada cartão DEVE exibir o título do filme em texto, não apenas dentro da imagem.
- **FR-010**: Cada cartão DEVE conduzir à página do filme correspondente.
- **FR-011**: Um filme sem cartaz DEVE exibir um substituto com o título legível, preservando a
  proporção dos demais cartões.
- **FR-012**: Cada cartão DEVE ter nome acessível que identifique o filme, sem depender do texto
  alternativo da imagem.

### Navegação das trilhas

- **FR-013**: Cada trilha DEVE avançar por gesto de deslize em telas de toque.
- **FR-014**: Cada trilha DEVE oferecer controles visíveis de avançar e retroceder **apenas**
  quando houver conteúdo além da borda visível.
- **FR-015**: A rolagem de uma trilha NÃO PODE provocar rolagem horizontal da página.
- **FR-016**: Cada trilha DEVE ter posição de rolagem independente das demais.
- **FR-017**: Todos os cartões DEVEM ser alcançáveis por teclado, na ordem visual, e a trilha DEVE
  acompanhar o foco.
- **FR-018**: O deslocamento das trilhas DEVE ocorrer sem animação quando o visitante tiver
  configurado preferência por movimento reduzido.
- **FR-019**: Cada trilha DEVE ser anunciada a tecnologias assistivas com seu rótulo e a
  quantidade de filmes que contém.

### Origem e resiliência dos dados

- **FR-020**: A classificação de cada filme como em alta ou de estreia futura DEVE vir do catálogo
  externo e ser armazenada na plataforma.
- **FR-021**: A home NÃO PODE consultar o catálogo externo durante a visita — todas as trilhas são
  montadas a partir dos dados já armazenados.
- **FR-022**: Com o catálogo externo indisponível, as trilhas DEVEM continuar sendo exibidas com
  os dados armazenados.
- **FR-023**: A classificação armazenada DEVE registrar quando foi atualizada, para que dados
  antigos sejam reconhecíveis.

### Página do filme sem sessão

- **FR-024**: A página de um filme sem sessão programada DEVE apresentar a mesma composição da
  página de um filme com sessões: cartaz, título, sinopse, duração, classificação e gênero.
- **FR-025**: Havendo data de estreia conhecida, a página DEVE informá-la.
- **FR-026**: A página DEVE informar, em português, que não há sessões programadas no momento.
- **FR-027**: Não havendo data de estreia conhecida, a página NÃO PODE inventar nem estimar uma.

### Estados e mensagens

- **FR-028**: Cada trilha DEVE exibir um estado de carregamento com a mesma altura da trilha
  final, evitando deslocamento do conteúdo da página.
- **FR-029**: Toda mensagem desta feature DEVE ser escrita em português, dizendo o que aconteceu e
  qual a próxima ação possível.
- **FR-030**: Nenhum estado desta feature pode exibir texto genérico de erro nem área em branco
  sem explicação.

### Key Entities

- **Filme**: já existe na plataforma. Ganha a informação de **classificação de catálogo** — se
  está em alta e se tem estreia futura — e a data em que essa informação foi atualizada.
- **Trilha**: agrupamento nomeado de filmes exibido na home. Três existem: Em cartaz, Em alta e Em
  breve. Não é uma entidade persistida; é o resultado de uma regra de seleção.

## Success Criteria *(mandatory)*

- **SC-001**: A partir da home, o visitante alcança a página de qualquer filme exibido em uma
  trilha em 1 interação.
- **SC-002**: A trilha Em alta nunca exibe mais de 9 filmes.
- **SC-003**: 100% dos filmes da trilha Em cartaz conduzem a uma página com ao menos uma sessão
  comprável no momento em que foram listados.
- **SC-004**: As trilhas permanecem completas e navegáveis quando o catálogo externo está
  indisponível.
- **SC-005**: Em larguras de 360px a 1920px, a página nunca apresenta rolagem horizontal.
- **SC-006**: Todos os cartões de todas as trilhas são alcançáveis usando apenas o teclado, sem
  armadilha de foco.
- **SC-007**: A home fica utilizável — primeira trilha visível e navegável — em até 2 segundos em
  conexão de banda larga comum.
- **SC-008**: Nenhuma trilha vazia é exibida com título e sem conteúdo, verificável esvaziando
  cada classificação.
- **SC-009**: Um filme sem sessão exibe data de estreia quando ela existe, e nunca uma data
  inventada quando não existe.

## Assumptions

- **"Em cartaz" significa comprável, não "em exibição nos cinemas"** — decisão do usuário em
  2026-08-11. Num site de ingressos, uma trilha rotulada Em cartaz que leva a filmes sem sessão à
  venda é promessa quebrada, e contraria a regra que o painel de destaques já segue. Em alta e Em
  breve continuam vindo do catálogo externo.
- **A condicional do pedido não se aplica** — o catálogo externo fornece as três classificações
  nativamente, então não é preciso derivá-las de datas de lançamento. Os "9 filmes" viram limite
  de exibição da trilha Em alta.
- **Repetição entre trilhas é aceita** — um filme em alta que também está em cartaz aparece nas
  duas. Suprimir a repetição faria trilhas mudarem de conteúdo conforme a ordem de renderização,
  que é pior de entender e de testar.
- **O painel de destaques permanece** — esta feature acrescenta trilhas abaixo dele, sem
  substituí-lo. Filmes destacados também aparecem na trilha Em cartaz.
- **Janela de "em breve"** — assume-se a janela que o próprio catálogo externo considera ao
  classificar estreias futuras, sem impor uma segunda regra por cima.
- **Frequência de atualização** — a classificação é atualizada quando a sincronização com o
  catálogo externo é executada, não automaticamente. Catálogo desatualizado é possível e
  reconhecível pela data de atualização registrada.

### Escopo excluído

Pedido de aviso sobre estreia ("Lembre-me") — descartado pelo usuário em 2026-08-11 depois de a
limitação ser apontada: o sistema registraria o interesse mas não entregaria aviso algum, e um
botão que promete aviso sem nunca avisar é a interface enganosa que o Princípio V proíbe.
Entregá-lo de verdade exigiria envio de e-mail ou notificação, fora do escopo do desafio.

Também fora: filtros ou ordenação das trilhas, paginação para além do limite de cada trilha, e
qualquer alteração no painel de destaques.

### Dependências

- Painel de destaques e página do filme (`001-movie-highlights-carousel`)
- Cabeçalho global (`002-site-header-navigation`)

Esta feature **não** depende de autenticação: todas as trilhas e a página do filme são públicas.
