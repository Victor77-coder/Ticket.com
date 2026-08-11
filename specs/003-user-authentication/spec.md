# Feature Specification: Autenticação e Acesso à Conta

**Feature Branch**: `main` (o projeto trabalha sem branches de feature)

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "realize agora a feature de autenticacão e adicione o icone de login no header."

> **Nota de escopo — o ícone já existe.** A feature `002-site-header-navigation` já entregou o
> componente de acesso à conta com o ícone de pessoa desenhado e testado, mas deliberadamente
> **não o montou** no cabeçalho: o FR-023 daquela feature proíbe um ponto de acesso que conduza a
> um destino inexistente, e a rota de entrada pertence a esta feature. Portanto o pedido "adicione
> o ícone de login no header" se traduz em **entregar o destino e montar o que já existe** —
> desbloqueando as tarefas T037 e T038 de `002-site-header-navigation`. Nenhum ícone novo é
> desenhado aqui.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entrar na conta (Priority: P1)

Um visitante navegando pelo site aciona o ícone de pessoa no cabeçalho. Ele chega a uma tela de
entrada, informa suas credenciais e é reconhecido pelo sistema. Ao terminar, volta exatamente
para a página onde estava, e o cabeçalho passa a identificá-lo em vez de convidá-lo a entrar.

**Why this priority**: É o que desbloqueia o cabeçalho (T037/T038 da feature 002) e a precondição
de toda funcionalidade futura — reservar, comprar e validar ingresso dependem de saber quem é a
pessoa. Sem isso, os três papéis exigidos pelo desafio existem só no banco.

**Independent Test**: A partir da home, acionar o ícone de conta, entrar com as credenciais de
`cliente1` do seed, e confirmar que o retorno é para a home com o cabeçalho identificando o
usuário.

**Acceptance Scenarios**:

1. **Given** um visitante não autenticado em qualquer página, **When** aciona o ponto de acesso à
   conta no cabeçalho, **Then** é conduzido à tela de entrada.
2. **Given** a tela de entrada, **When** o visitante informa credenciais válidas, **Then** a
   sessão é iniciada e ele é levado de volta à página de onde partiu.
3. **Given** o visitante chegou à tela de entrada digitando o endereço diretamente, **When**
   entra com sucesso, **Then** é levado à página inicial.
4. **Given** credenciais inválidas, **When** o visitante tenta entrar, **Then** o sistema informa
   a falha em português, sem revelar se o erro foi no identificador ou na senha, e mantém o que
   ele digitou no campo de identificação.
5. **Given** um campo obrigatório vazio, **When** o visitante tenta enviar, **Then** o sistema
   aponta qual campo falta antes de qualquer tentativa de autenticação.
6. **Given** um visitante já autenticado, **When** acessa a tela de entrada, **Then** é levado à
   página inicial em vez de ver o formulário novamente.
7. **Given** qualquer papel (organizador, cliente ou portaria), **When** entra com sucesso,
   **Then** o comportamento de retorno é o mesmo — nenhum papel é conduzido a uma área que ainda
   não existe.

---

### User Story 2 - Sair da conta (Priority: P1)

Um usuário autenticado decide encerrar a sessão. A partir do ponto de conta no cabeçalho, ele
encerra o acesso e o cabeçalho volta ao estado de visitante.

**Why this priority**: Compartilha P1 com a US1 porque entrar sem poder sair é um beco sem saída —
exatamente o que o Princípio I da constitution proíbe. Também é requisito prático de avaliação: o
avaliador precisa alternar entre as quatro contas do seed.

**Independent Test**: Autenticado como `cliente1`, encerrar a sessão pelo cabeçalho e confirmar
que o ponto de conta volta a convidar a entrar e que recarregar a página não restaura a sessão.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado, **When** aciona o ponto de conta no cabeçalho, **Then**
   enxerga a opção de encerrar a sessão junto da sua identificação.
2. **Given** a opção de encerrar visível, **When** o usuário a aciona, **Then** a sessão termina e
   o cabeçalho volta ao estado de visitante.
3. **Given** a sessão encerrada, **When** o usuário recarrega ou navega para outra página,
   **Then** continua como visitante — nada da sessão anterior é restaurado.
4. **Given** a sessão encerrada, **When** o usuário aciona o botão "voltar" do navegador, **Then**
   nenhuma informação da sessão anterior é reapresentada.

---

### User Story 3 - Permanecer reconhecido durante a navegação (Priority: P2)

Depois de entrar, o usuário navega entre a home, a página de um filme e a busca. Em todas elas o
cabeçalho continua identificando-o, sem que ele precise entrar de novo. Quando a sessão deixa de
valer, o cabeçalho volta ao estado de visitante sem quebrar a página.

**Why this priority**: É o que transforma o login em sessão útil. Depende da US1, mas tem valor
verificável próprio e cobre o FR-024 da feature 002, que já previu a expiração.

**Independent Test**: Entrar, navegar por três páginas distintas confirmando a identificação no
cabeçalho, e então invalidar a sessão e confirmar que o cabeçalho volta ao estado de visitante
sem erro visível.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado, **When** navega entre páginas do site, **Then** o cabeçalho
   o identifica em todas, sem pedir credenciais de novo.
2. **Given** um usuário autenticado, **When** fecha e reabre o navegador dentro do prazo de
   validade, **Then** continua autenticado.
3. **Given** uma sessão que deixou de valer, **When** o usuário carrega qualquer página, **Then**
   o cabeçalho volta ao estado de visitante e a página continua utilizável.
4. **Given** uma sessão que deixou de valer, **When** o usuário aciona uma ação que exige conta,
   **Then** é conduzido à tela de entrada com explicação em português do motivo.

---

### Edge Cases

- **Identificador inexistente vs. senha errada**: as duas situações produzem exatamente a mesma
  mensagem e o mesmo tempo de resposta perceptível. Diferenciá-las revelaria quais contas existem.
- **Tentativas repetidas**: após um número definido de falhas seguidas vindas da mesma origem, o
  sistema passa a recusar novas tentativas por um período, informando em português quando poderá
  tentar de novo.
- **Conta desativada**: recebe a mesma mensagem de credencial inválida, sem revelar que a conta
  existe mas está inativa.
- **Destino de retorno manipulado**: o retorno após a entrada só aceita endereços internos ao
  próprio site. Um endereço externo é ignorado e o usuário vai para a página inicial.
- **Envio duplicado do formulário**: acionar "entrar" duas vezes não cria duas sessões nem produz
  erro visível.
- **Sessão encerrada em outra aba**: a aba que ainda exibe o estado autenticado volta ao estado de
  visitante na próxima navegação, sem quebrar.
- **JavaScript indisponível**: a tela de entrada continua funcional — é um formulário, não uma
  interação dependente de script.
- **Navegação apenas por teclado**: o percurso completo (ícone → campos → enviar → sair) é
  alcançável por teclado, com foco visível e ordem previsível.
- **Gerenciador de senhas**: os campos são reconhecidos por gerenciadores de senha do navegador.

## Requirements *(mandatory)*

### Functional Requirements

**Entrada**

- **FR-001**: O sistema DEVE oferecer uma tela de entrada acessível por um endereço estável,
  alcançável a partir do ponto de conta do cabeçalho.
- **FR-002**: A tela de entrada DEVE pedir um identificador e uma senha, e nada além disso.
- **FR-003**: O sistema DEVE iniciar uma sessão quando as credenciais corresponderem a uma conta
  ativa.
- **FR-004**: O sistema DEVE recusar credenciais que não correspondam a uma conta ativa,
  apresentando **a mesma** mensagem em português independentemente de o identificador não existir,
  a senha estar errada ou a conta estar desativada.
- **FR-005**: O sistema DEVE preservar o identificador digitado após uma tentativa recusada, e
  NUNCA preservar a senha.
- **FR-006**: O sistema DEVE validar campos obrigatórios antes de tentar autenticar, apontando
  qual campo falta.
- **FR-007**: O sistema DEVE limitar tentativas seguidas de entrada malsucedidas vindas da mesma
  origem, informando em português quando novas tentativas serão aceitas.
- **FR-008**: O sistema DEVE redirecionar um usuário já autenticado que acesse a tela de entrada,
  em vez de reapresentar o formulário.

**Retorno após a entrada**

- **FR-009**: Após entrada bem-sucedida, o sistema DEVE conduzir o usuário de volta à página de
  onde ele partiu.
- **FR-010**: Quando não houver página de origem conhecida, o sistema DEVE conduzir à página
  inicial.
- **FR-011**: O sistema DEVE aceitar como destino de retorno **apenas** endereços internos ao
  próprio site; qualquer outro valor é descartado em favor da página inicial.
- **FR-012**: O destino de retorno DEVE ser o mesmo para os três papéis — nenhum papel é conduzido
  a uma área inexistente.

**Saída**

- **FR-013**: O sistema DEVE oferecer, a partir do ponto de conta do cabeçalho, uma forma de
  encerrar a sessão.
- **FR-014**: Ao encerrar, o sistema DEVE invalidar a sessão de modo que nenhuma navegação
  posterior a restaure.
- **FR-015**: Após encerrar, o cabeçalho DEVE voltar ao estado de visitante em todas as páginas.

**Sessão**

- **FR-016**: A sessão DEVE persistir entre páginas e entre reaberturas do navegador, dentro de um
  prazo de validade definido.
- **FR-017**: A sessão DEVE expirar após o prazo de validade, e a expiração NÃO PODE produzir erro
  visível: a página continua utilizável e o cabeçalho volta ao estado de visitante.
- **FR-018**: O identificador de sessão NÃO PODE ficar acessível a scripts executados na página.
- **FR-019**: O sistema DEVE proteger as ações de entrar e sair contra requisições forjadas de
  outros sites.

**Identidade e papéis**

- **FR-020**: O sistema DEVE expor, para a sessão ativa, um nome de exibição e o papel do usuário.
- **FR-021**: O papel DEVE ser um entre organizador, cliente e portaria.
- **FR-022**: Toda decisão de autorização DEVE ser tomada no servidor. O papel exposto à interface
  serve para escolher o que apresentar, NUNCA para conceder acesso.
- **FR-023**: A resposta que descreve a sessão ativa NÃO PODE conter senha, hash de senha, nem
  dados de outros usuários.

**Cabeçalho (desbloqueio da feature 002)**

- **FR-024**: O ponto de acesso à conta DEVE ser montado no cabeçalho, conduzindo à tela de
  entrada quando não houver sessão.
- **FR-025**: Com sessão ativa, o ponto de conta DEVE identificar o usuário e dar acesso à saída.
- **FR-026**: A diferença entre o estado de visitante e o estado autenticado NÃO PODE ser
  comunicada apenas por cor.

**Mensagens e acessibilidade**

- **FR-027**: Toda mensagem desta feature DEVE ser escrita em português, dizendo o que aconteceu e
  qual a próxima ação possível.
- **FR-028**: Erros de entrada DEVEM ser anunciados a tecnologias assistivas e associados ao campo
  correspondente quando forem de campo.
- **FR-029**: Todo o percurso DEVE ser operável por teclado, com foco visível.
- **FR-030**: Os campos DEVEM ser identificáveis por gerenciadores de senha do navegador.

### Key Entities

- **Usuário**: pessoa com acesso ao sistema. Já existe no modelo de dados, com identificador,
  nome, credencial e papel (organizador, cliente ou portaria). Esta feature não cria o conceito —
  passa a usá-lo.
- **Sessão**: vínculo temporário entre um navegador e um usuário. Tem início, prazo de validade e
  fim explícito. É o que permite reconhecer alguém entre páginas sem pedir credenciais de novo.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir de qualquer página, um visitante conclui a entrada em no máximo 3
  interações e volta à página de origem.
- **SC-002**: As quatro contas semeadas (organizador, dois clientes e portaria) entram com sucesso
  usando exatamente as credenciais publicadas no README.
- **SC-003**: Um usuário autenticado é identificado pelo cabeçalho em 100% das páginas do site.
- **SC-004**: Encerrar a sessão devolve o cabeçalho ao estado de visitante, e nenhuma navegação
  posterior — inclusive o botão "voltar" — restaura o estado autenticado.
- **SC-005**: Tentativas com identificador inexistente e com senha errada produzem mensagem
  idêntica, verificável comparando as duas respostas.
- **SC-006**: Nenhuma resposta do sistema contém senha ou hash de senha, verificável por inspeção
  automatizada.
- **SC-007**: O percurso completo — ícone, campos, envio, saída — é operável apenas com o teclado,
  sem armadilha de foco.
- **SC-008**: Uma sessão expirada nunca produz página quebrada nem mensagem genérica do tipo
  "algo deu errado".
- **SC-009**: As tarefas T037 e T038 de `002-site-header-navigation` passam a ser executáveis e
  são concluídas.

## Assumptions

- **Sem auto-cadastro**: decisão do usuário em 2026-08-11. As contas são as quatro do seed. O
  desafio não pede criação de conta e exclui explicitamente recuperação de senha, então nenhuma
  das duas entra no escopo.
- **Retorno único para todos os papéis**: decisão do usuário em 2026-08-11. Áreas específicas de
  organizador e de portaria chegam com as features que lhes dão conteúdo real — criar landings
  vazias agora contrariaria o Princípio V da constitution, que proíbe seção "em breve".
- **Identificador de entrada**: assume-se o nome de usuário, que é o que o seed publica no README.
- **Prazo de validade da sessão**: assume-se algo em torno de duas semanas — longo o bastante para
  o avaliador percorrer o desafio sem reentrar, curto o bastante para não ser sessão eterna. Valor
  exato a definir no plano.
- **Limite de tentativas**: assume-se algo em torno de cinco falhas seguidas antes do bloqueio
  temporário. Valor exato a definir no plano.
- **Escopo excluído**: cadastro, recuperação de senha, troca de senha, autenticação por terceiros,
  verificação em duas etapas, e as áreas por papel. Nada disso é pedido pelo desafio.
- **Dependência**: esta feature pressupõe o cabeçalho entregue por `002-site-header-navigation` e
  o modelo de usuário com papel entregue por `001-movie-highlights-carousel`.
