# Feature Specification: Escolha de Assentos

**Feature Branch**: `main` (o projeto trabalha sem branches de feature)

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "escolha de assentos (mapa da sala) para uma sessão à venda"

> **Esta é a feature que atravessa a fronteira do Princípio II.** Desde a `001`, o arquivo
> `backend/apps/screening/models.py` carrega um aviso: nenhuma escrita de ocupação de assento
> entra no projeto sem a constraint `UNIQUE(sessão, assento)` que a protege. Esta feature é a que
> cria as duas coisas **juntas** — o modelo e a constraint —, porque separá-las era exatamente o
> que o princípio proíbe.
>
> O teste de concorrência não é diferencial aqui. É **prova obrigatória**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver a sala e entender o que está livre (Priority: P1)

O cliente autenticado escolhe uma sessão na página do filme e chega ao mapa da sala. Vê a tela no
topo, as fileiras identificadas por letra, e reconhece de imediato quais lugares estão livres,
quais já foram tomados e quais são reservados para acessibilidade.

**Why this priority**: Sem enxergar a sala não há escolha. É a tela que transforma "comprar
ingresso" em "escolher onde sentar", que é a diferença entre esta plataforma e uma lista de
preços.

**Independent Test**: Autenticado como `cliente1`, abrir uma sessão publicada e futura e conferir
que o mapa exibe todos os lugares da sala, com os estados distinguíveis sem depender de cor.

**Acceptance Scenarios**:

1. **Given** uma sessão publicada e futura, **When** o cliente abre seu mapa, **Then** vê todos
   os lugares da sala, organizados em fileiras identificadas, com a posição da tela indicada.
2. **Given** o mapa exibido, **When** o cliente observa um lugar livre, **Then** ele é
   distinguível de um lugar ocupado **por forma e por rótulo**, não apenas por cor.
3. **Given** lugares reservados para acessibilidade, **When** o mapa é exibido, **Then** eles são
   identificados como tais e não podem ser selecionados no fluxo comum.
4. **Given** um lugar já tomado por outra pessoa, **When** o cliente tenta selecioná-lo, **Then**
   nada acontece e o motivo fica claro.
5. **Given** a sessão está com todos os lugares tomados, **When** o cliente abre o mapa, **Then**
   vê um estado explicativo em português dizendo que a sessão esgotou.
6. **Given** o catálogo externo está indisponível, **When** o cliente abre o mapa, **Then** o mapa
   funciona normalmente — os dados da sala e da sessão são locais.

---

### User Story 2 - Reservar os lugares escolhidos (Priority: P1)

O cliente seleciona um ou mais lugares livres, confere o total, e confirma. O sistema segura
aqueles lugares para ele por um prazo, mostra qual é esse prazo, e o encaminha para o pagamento.

**Why this priority**: É o núcleo da feature e o ponto onde o Princípio II é exercido. Compartilha
P1 com a US1 porque ver sem poder reservar não entrega nada.

**Independent Test**: Selecionar dois lugares livres, confirmar, e conferir que a reserva aparece
confirmada com prazo de expiração e que os dois lugares passam a constar como tomados para outra
pessoa.

**Acceptance Scenarios**:

1. **Given** o mapa aberto, **When** o cliente aciona um lugar livre, **Then** ele passa a
   selecionado, e acionar de novo o desmarca.
2. **Given** um ou mais lugares selecionados, **When** o cliente confirma, **Then** a reserva é
   criada e ele vê quais lugares ficaram com ele e até quando.
3. **Given** a reserva criada, **When** o cliente a observa, **Then** encontra um caminho claro
   para prosseguir ao pagamento.
4. **Given** nenhum lugar selecionado, **When** o cliente tenta confirmar, **Then** o sistema
   informa que é preciso escolher ao menos um lugar.
5. **Given** o cliente selecionou o número máximo permitido, **When** tenta selecionar mais um,
   **Then** o sistema informa o limite e não adiciona.
6. **Given** dois clientes escolheram o mesmo lugar, **When** ambos confirmam ao mesmo tempo,
   **Then** **exatamente um** obtém a reserva e o outro recebe explicação clara de que aquele
   lugar acabou de ser tomado.
7. **Given** um lugar foi tomado entre a abertura do mapa e a confirmação, **When** o cliente
   confirma, **Then** nenhum lugar da seleção é reservado, e ele é informado de qual deixou de
   estar livre.
8. **Given** a sessão foi cancelada ou já começou, **When** o cliente tenta reservar, **Then** a
   reserva é recusada com explicação.

---

### User Story 3 - Entrar para poder reservar (Priority: P2)

Um visitante sem sessão ativa navega até o mapa, escolhe onde quer sentar e tenta confirmar. É
conduzido à entrada e, ao concluir, volta ao mesmo mapa.

**Why this priority**: Fecha o caminho do visitante, que é como a maioria chega. Depende da US2
existir, mas é separável.

**Independent Test**: Sem sessão ativa, abrir o mapa, tentar reservar, entrar com `cliente1` e
conferir que o retorno é para o mapa daquela sessão.

**Acceptance Scenarios**:

1. **Given** um visitante sem sessão ativa, **When** abre o mapa de uma sessão, **Then** consegue
   ver a sala e os lugares livres.
2. **Given** o visitante sem sessão, **When** tenta confirmar uma reserva, **Then** é conduzido à
   entrada com explicação do motivo.
3. **Given** o visitante entrou com sucesso, **When** a entrada conclui, **Then** ele retorna ao
   mapa daquela mesma sessão.
4. **Given** um usuário com papel de organizador ou de portaria, **When** tenta reservar, **Then**
   o sistema recusa — a recusa acontece no servidor, não por esconder o botão.

---

### User Story 4 - Recuperar o lugar de quem não pagou (Priority: P2)

Um cliente reservou e não concluiu o pagamento. Passado o prazo, aqueles lugares voltam a ficar
livres para outra pessoa.

**Why this priority**: Sem expiração, o primeiro visitante distraído tira o lugar de circulação
para sempre. É o que impede o estoque de morrer.

**Independent Test**: Criar uma reserva, forçar seu vencimento, e conferir que outro cliente
consegue reservar os mesmos lugares.

**Acceptance Scenarios**:

1. **Given** uma reserva cujo prazo venceu, **When** outro cliente abre o mapa, **Then** aqueles
   lugares constam como livres.
2. **Given** uma reserva cujo prazo venceu, **When** outro cliente a reserva, **Then** obtém os
   lugares sem conflito.
3. **Given** uma reserva vencida, **When** o cliente original tenta prosseguir para o pagamento,
   **Then** é informado de que a reserva expirou e pode escolher de novo.
4. **Given** uma reserva dentro do prazo, **When** outro cliente tenta os mesmos lugares,
   **Then** eles continuam indisponíveis para ele.

---

### Edge Cases

- **Sessão esgotada**: o mapa mostra a sala cheia e um estado explicativo, nunca uma tela vazia.
- **Sessão inexistente ou não publicada**: mensagem de não encontrada, sem revelar que existe em
  rascunho.
- **Sessão que começou durante a navegação**: a confirmação é recusada com explicação.
- **Cliente com reserva ativa na mesma sessão**: ver a suposição registrada — o comportamento
  precisa ser previsível, não acidental.
- **Seleção parcialmente tomada**: nenhum lugar é reservado. Reservar "o que sobrou" entregaria
  algo diferente do que a pessoa escolheu.
- **Confirmação acionada duas vezes**: cria uma reserva só.
- **Sala com capacidade que não fecha a fileira**: a última fileira fica incompleta, sem inventar
  lugares que não existem.
- **Perda de conexão na confirmação**: ou a reserva existe por inteiro, ou não existe — nunca
  meia reserva.
- **Navegação apenas por teclado**: cada lugar é alcançável e acionável por teclado, e sua
  identificação e estado são anunciados.
- **Tela estreita**: o mapa continua legível e a sala inteira permanece alcançável.

## Requirements *(mandatory)*

### Navegação

- **FR-001**: A listagem de sessões da página do filme DEVE conduzir ao mapa da sessão escolhida.
- **FR-002**: Apenas sessões publicadas e futuras DEVEM ter mapa acessível.
- **FR-003**: Uma sessão inexistente, em rascunho, cancelada ou já iniciada DEVE resultar em
  mensagem de não encontrada, sem revelar seu estado interno.

### O mapa

- **FR-004**: O mapa DEVE representar todos os lugares da sala, derivados de sua capacidade.
- **FR-005**: O mapa DEVE indicar a posição da tela e identificar cada fileira.
- **FR-006**: Cada lugar DEVE ter identificação única e legível dentro da sala.
- **FR-007**: O mapa DEVE distinguir quatro estados: **livre**, **selecionado**, **tomado** e
  **acessibilidade**.
- **FR-008**: Os estados NÃO PODEM ser distinguíveis apenas por cor — cada um DEVE ter forma ou
  rótulo próprio.
- **FR-009**: Lugares de acessibilidade DEVEM ser identificados e NÃO PODEM ser selecionados no
  fluxo comum.
- **FR-010**: O mapa DEVE ser exibido a visitantes sem sessão ativa.
- **FR-011**: Todo lugar DEVE ser alcançável e acionável por teclado, com identificação e estado
  anunciados a tecnologias assistivas.

### Seleção

- **FR-012**: O cliente DEVE poder selecionar e desmarcar lugares livres.
- **FR-013**: O sistema DEVE impor um limite máximo de lugares por reserva e informá-lo ao ser
  atingido.
- **FR-014**: Lugares tomados ou de acessibilidade NÃO PODEM ser selecionados.
- **FR-015**: A seleção DEVE exibir a quantidade escolhida e o valor total.

### Reserva — o núcleo do Princípio II

- **FR-016**: Um mesmo lugar de uma mesma sessão NUNCA pode estar tomado por duas reservas. Esta
  garantia DEVE ser imposta pelo banco de dados, não apenas pela aplicação.
- **FR-017**: A transição de livre para tomado DEVE ocorrer dentro de uma transação; a leitura
  que antecede a escrita DEVE bloquear as linhas envolvidas.
- **FR-018**: A reserva DEVE ser criada por inteiro ou não ser criada — nunca parcialmente.
- **FR-019**: Quando qualquer lugar da seleção deixar de estar livre, **nenhum** é reservado, e o
  cliente é informado de qual causou a recusa.
- **FR-020**: A reserva DEVE ter prazo de validade explícito, informado ao cliente.
- **FR-021**: Passado o prazo, os lugares DEVEM voltar a ficar livres para outros clientes.
- **FR-022**: Uma reserva vencida NÃO PODE ser usada para prosseguir ao pagamento.
- **FR-023**: Confirmar duas vezes a mesma seleção NÃO PODE criar duas reservas.

### Autorização

- **FR-024**: Apenas usuários com papel de cliente podem criar reserva.
- **FR-025**: A recusa por papel DEVE acontecer no servidor. Esconder o botão na interface não
  conta como controle de acesso.
- **FR-026**: Um visitante sem sessão que tente reservar DEVE ser conduzido à entrada e retornar
  ao mesmo mapa ao concluir.
- **FR-027**: Um cliente NÃO PODE ver nem alterar reserva de outro cliente.

### Prosseguir

- **FR-028**: Após reservar, o cliente DEVE encontrar caminho claro para o pagamento.
- **FR-029**: Nenhum ingresso é emitido nesta feature.

### Estados e mensagens

- **FR-030**: Sessão esgotada, lugar recém-tomado, sessão cancelada ou iniciada, e reserva
  vencida DEVEM ter mensagem própria em português, dizendo o que houve e a próxima ação.
- **FR-031**: Nenhum estado pode exibir texto genérico de erro nem área em branco.
- **FR-032**: O mapa DEVE funcionar com o catálogo externo indisponível.

### Preservação

- **FR-033**: Nenhuma asserção de teste das features 001–006 pode ser alterada.
- **FR-034**: Nenhum contrato de API existente pode mudar de forma.
- **FR-035**: A disciplina de tokens da feature 006 DEVE ser mantida: nenhum valor de cor,
  espaçamento, tipografia, raio ou duração fora dos tokens.

### Key Entities

- **Lugar**: posição física numa sala, com identificação única ali (fileira e número) e um tipo —
  comum ou acessibilidade. Pertence à sala e é o mesmo em todas as sessões dela.
- **Reserva**: intenção de compra de um cliente para uma sessão, com prazo de validade. Agrupa um
  ou mais lugares e é a unidade que segue para o pagamento.
- **Ocupação**: o vínculo entre uma reserva e um lugar. É onde a garantia de FR-016 vive: não
  podem existir duas ocupações do mesmo lugar na mesma sessão.

## Success Criteria *(mandatory)*

- **SC-001**: A partir de um filme com sessão, o cliente chega ao mapa em 1 interação.
- **SC-002**: Duas reservas simultâneas do mesmo lugar resultam em exatamente uma bem-sucedida e
  nenhuma duplicata no banco — verificável por teste automatizado de concorrência.
- **SC-003**: Nenhuma sequência de operações produz o mesmo lugar tomado duas vezes na mesma
  sessão.
- **SC-004**: Uma reserva vencida libera seus lugares, e outro cliente consegue reservá-los.
- **SC-005**: Usuários com papel de organizador ou portaria recebem recusa ao tentar reservar, e a
  recusa vem do servidor.
- **SC-006**: Um cliente não consegue acessar reserva de outro cliente.
- **SC-007**: Os quatro estados do lugar são distinguíveis por alguém que não percebe cor.
- **SC-008**: O mapa inteiro é operável apenas com o teclado, sem armadilha de foco.
- **SC-009**: Uma seleção com qualquer lugar indisponível não reserva nenhum.
- **SC-010**: O mapa permanece funcional com o catálogo externo fora do ar.
- **SC-011**: Nenhum estado exibe texto genérico de erro nem área em branco.
- **SC-012**: As asserções de teste das features 001–006 continuam passando sem alteração.

## Assumptions

- **Disposição da sala**: assume-se fileiras de **10 lugares**, identificadas por letra (A, B, C…)
  e numeradas de 1 a 10, com corredor central entre o quinto e o sexto. A capacidade determina
  quantas fileiras existem — 60 lugares dão 6 fileiras, 40 dão 4. Capacidade que não fecha a
  fileira deixa a última incompleta, sem inventar lugares.

- **Acessibilidade**: decisão do usuário em 2026-08-11 sobre o quarto estado. Assume-se **3
  lugares por sala**, na última fileira, marcados e fora da venda comum. É convenção de sala real
  e dá ao quarto estado um significado testável — antes ele não teria nenhum, porque as
  capacidades semeadas fecham a grade exata.

- **Prazo da reserva: 10 minutos**, decisão do usuário. É o padrão de mercado e folgado para um
  pagamento simulado.

- **Limite por reserva**: assume-se **6 lugares**, convenção comum em cinema. Impede que uma
  pessoa trave a sala inteira sem impedir a compra de um grupo.

- **Reserva ativa duplicada**: assume-se que um cliente com reserva ativa numa sessão pode criar
  outra na mesma sessão, desde que para lugares diferentes. Impedir exigiria decidir o que fazer
  com a reserva anterior, e descartá-la silenciosamente seria pior do que permitir duas.

- **A liberação por vencimento é por consulta, não por processo agendado**: um lugar cuja reserva
  venceu conta como livre a partir do instante do vencimento, sem depender de rotina periódica.
  Isso evita uma janela em que o lugar está vencido mas ainda aparece tomado.

- **Cancelamento pelo cliente fica fora**: só a expiração devolve o lugar. Cancelar por vontade
  própria é outra feature.

### Limitação assumida da demonstração

Com prazo fixo de 10 minutos, **o avaliador não verá a expiração acontecer** — teria de esperar
parado. O comportamento fica provado por teste automatizado, não por demonstração.

A alternativa oferecida — prazo configurável por ambiente, encurtável para segundos — foi
descartada pelo usuário. A limitação DEVE constar nas limitações conhecidas do README, com a
indicação de qual teste prova o comportamento.

### Escopo excluído

Pagamento simulado e emissão de ingresso · QR assinado, "Meus ingressos" e link de
compartilhamento · tela de portaria e validação · painel do organizador para criar salas e
sessões · atualização do mapa em tempo real · cancelamento pelo cliente · nota fiscal · e-mail ·
venda por quantidade sem escolha de lugar.

### Dependências

- Autenticação com os três papéis (`003-user-authentication`)
- Página do filme listando sessões futuras (`001`, `004`)
- Seed com sessões publicadas (`005`)
- Disciplina de tokens (`006`)
