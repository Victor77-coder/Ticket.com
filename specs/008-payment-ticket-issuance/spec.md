# Feature Specification: Pagamento Simulado e Emissão do Ingresso

**Feature Branch**: `008-payment-ticket-issuance`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "Pagamento simulado da reserva e emissão do ingresso com QR assinado."

> **Esta é a feature que fecha o buraco deixado pela 007.** A 007 levou o cliente até a reserva
> com prazo de dez minutos, protegida por `UNIQUE(sessão, assento)`. O fluxo morre ali: não existe
> estado pago, não existe pagamento e não existe ingresso — `backend/apps/screening/models.py`
> registra na primeira linha que "Ticket permanece fora: emissão de ingresso é a próxima feature".
> Esta é essa feature.
>
> **Aprovação e emissão são a mesma feature, e isso não é conveniência.** O Princípio II diz que
> "pagamento aprovado DEVE emitir o ingresso; não existe estado intermediário durável em que o
> assento esteja preso sem dono". Entregar a cobrança sem a emissão cria exatamente esse estado:
> um assento pago cujo dono não tem nada na mão. É a mesma razão pela qual a 007 teve de criar
> `ReservedSeat` e sua constraint na mesma migração.
>
> Como na 007, o teste de concorrência **não é diferencial**. É prova obrigatória, e precisa
> **falhar** se a garantia do banco for removida. Somam-se a ele, pelo Princípio III, as provas de
> que um QR adulterado e um QR assinado com outro segredo são rejeitados.

## Leitura do Princípio II sobre a recusa *(registro obrigatório)*

O Princípio II afirma: **"Pagamento recusado DEVE liberar o assento"**. Esta feature **não** libera
o assento no instante da recusa. A leitura que sustenta isso, registrada aqui em vez de
implementada em silêncio:

- A cláusula existe para impedir que um assento fique **preso sem dono e sem prazo** — o estado
  intermediário durável que a frase seguinte do próprio princípio proíbe.
- Após uma recusa, o assento **continua com dono** (a mesma reserva, do mesmo cliente) e
  **continua com prazo correndo** (o vencimento original de dez minutos, inalterado). Nenhum dos
  dois defeitos que o princípio previne acontece.
- Quem devolve o assento ao estoque é o **vencimento**, exatamente como já acontece hoje para
  quem abandona a reserva sem tentar pagar — por consulta, sem rotina agendada, conforme a
  suposição já registrada na 007.
- Liberar na recusa seria pior para o cliente e não melhoraria a integridade: quem digitou o
  cartão errado perderia o lugar para outra pessoa entre uma tentativa e a seguinte.

**Se esta leitura não se sustentar em revisão, o caminho é emendar a constitution — não
implementar a divergência em silêncio.** O Princípio II é NÃO NEGOCIÁVEL e uma divergência não
registrada seria bug de processo pelas próprias regras de Governance.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pagar e receber o ingresso (Priority: P1)

O cliente acaba de reservar seus lugares. Ele revisa o que está comprando — filme, sessão, sala,
lugares, valor total — e o tempo que ainda tem. Informa os dados do cartão fictício, confirma, e o
sistema aprova. Na mesma tela ele passa a ver seus ingressos, um por lugar, cada um com seu código
em QR.

**Why this priority**: É o fluxo principal e o par indissociável exigido pelo Princípio II.
Também é o que fecha a etapa 3 da ordem de construção obrigatória e destrava a etapa 4.

**Independent Test**: Autenticado como `cliente1`, reservar dois lugares, pagar com o cartão
aprovado documentado no README, e conferir que a confirmação exibe **dois** ingressos, cada um com
seu lugar e seu QR distinto.

**Acceptance Scenarios**:

1. **Given** uma reserva viva do próprio cliente, **When** ele abre o pagamento, **Then** vê
   filme, sessão, sala, lugares reservados, valor unitário, valor total e o prazo restante.
2. **Given** a revisão exibida, **When** o cliente informa um cartão aprovado e confirma,
   **Then** o pagamento é aprovado e a confirmação aparece na mesma jornada, sem passo extra.
3. **Given** o pagamento aprovado de uma reserva com três lugares, **When** a confirmação é
   exibida, **Then** existem **três** ingressos, um por lugar, cada um com código em QR próprio.
4. **Given** os ingressos emitidos, **When** o cliente observa um deles, **Then** identifica a
   qual filme, sessão, sala e lugar ele pertence.
5. **Given** a reserva foi paga, **When** qualquer outra pessoa consulta a disponibilidade da
   sessão, **Then** aqueles lugares constam como tomados e **não voltam** a ficar livres no
   horário em que a reserva teria vencido.
6. **Given** o pagamento aprovado, **When** o cliente recarrega a página de confirmação, **Then**
   vê os mesmos ingressos, sem emitir novos.
7. **Given** o catálogo externo está indisponível, **When** o cliente paga, **Then** o pagamento e
   a emissão funcionam normalmente — os dados de filme e sessão são locais.

---

### User Story 2 - Entender a recusa e tentar de novo (Priority: P1)

O cliente informa um cartão que o sistema recusa. Ele lê, em português, qual foi o motivo — e não
um código nem uma frase genérica —, vê que seus lugares continuam com ele e quanto tempo ainda
resta, e tenta de novo com outro cartão.

**Why this priority**: A constitution é explícita — "o caminho de recusa não é opcional" e ambos
os caminhos DEVEM ser exercitáveis pelo avaliador. Sem esta história, metade do requisito de
pagamento não existe.

**Independent Test**: Com uma reserva viva, pagar com cada um dos três cartões de recusa
documentados e conferir três mensagens **distintas** em português; em seguida pagar com o cartão
aprovado e conferir que os ingressos são emitidos normalmente.

**Acceptance Scenarios**:

1. **Given** uma reserva viva, **When** o cliente paga com um cartão de recusa documentado,
   **Then** vê uma mensagem em português dizendo o que houve e qual é a próxima ação.
2. **Given** os três cartões de recusa documentados, **When** cada um é usado, **Then** a mensagem
   é **diferente** em cada caso e corresponde ao motivo daquele cartão.
3. **Given** um pagamento recusado, **When** o cliente observa a tela, **Then** seus lugares
   continuam reservados e o prazo restante continua sendo o **mesmo** vencimento original.
4. **Given** um pagamento recusado, **When** o cliente tenta de novo com um cartão aprovado dentro
   do prazo, **Then** o pagamento é aprovado e os ingressos são emitidos.
5. **Given** um pagamento recusado, **When** qualquer pessoa consulta a sessão, **Then** os
   lugares seguem indisponíveis até o vencimento original da reserva.
6. **Given** várias recusas seguidas, **When** o cliente finalmente é aprovado, **Then** é emitido
   **um único** conjunto de ingressos.
7. **Given** o cliente informa dados de cartão mal formados, **When** confirma, **Then** recebe um
   aviso de preenchimento — distinto de uma recusa — e nenhum pagamento é registrado como
   tentativa de cobrança.

---

### User Story 3 - Não pagar o que já venceu (Priority: P2)

O cliente demorou na tela de pagamento e o prazo da reserva venceu. Ao confirmar, ele é informado
de que a reserva expirou e é conduzido de volta ao mapa para escolher de novo.

**Why this priority**: É o que impede que a expiração da 007 vire ficção. Sem isso, um lugar
liberado para outra pessoa poderia ser cobrado e emitido para quem chegou tarde.

**Independent Test**: Criar uma reserva, forçar seu vencimento, tentar pagar e conferir que a
cobrança é recusada, que nenhum ingresso é emitido e que a mensagem explica o que fazer.

**Acceptance Scenarios**:

1. **Given** uma reserva vencida, **When** o cliente tenta pagar, **Then** o pagamento é recusado
   com explicação em português e nenhum ingresso é emitido.
2. **Given** uma reserva vencida cujos lugares já foram tomados por outro cliente, **When** o
   cliente original tenta pagar, **Then** a recusa é clara e não altera a reserva do outro.
3. **Given** o prazo vence com a tela de pagamento aberta, **When** o cliente confirma, **Then** a
   recusa vem do servidor — o contador na tela não é o que decide.
4. **Given** uma reserva já paga, **When** o cliente tenta pagá-la outra vez, **Then** o sistema
   informa que ela já foi paga e o leva aos ingressos existentes, sem emitir novos.
5. **Given** uma reserva cancelada, **When** o cliente tenta pagá-la, **Then** o pagamento é
   recusado com explicação.

---

### User Story 4 - Pagar só o que é seu (Priority: P2)

Um organizador, um usuário de portaria ou outro cliente tenta pagar uma reserva que não lhe
pertence. O servidor recusa.

**Why this priority**: Princípio IV. Sem a recusa no servidor, o ingresso emitido não prova nada
sobre quem comprou, e o QR passa a valer para quem souber montar a requisição.

**Independent Test**: Com a reserva de `cliente1` viva, tentar pagá-la autenticado como
`cliente2`, como organizador e como portaria, e conferir três recusas do servidor.

**Acceptance Scenarios**:

1. **Given** uma reserva de `cliente1`, **When** `cliente2` tenta pagá-la, **Then** o servidor
   recusa e nenhum ingresso é emitido.
2. **Given** uma reserva qualquer, **When** um usuário com papel de organizador tenta pagá-la,
   **Then** o servidor responde negando por papel.
3. **Given** uma reserva qualquer, **When** um usuário com papel de portaria tenta pagá-la,
   **Then** o servidor responde negando por papel.
4. **Given** um visitante sem sessão ativa, **When** tenta pagar, **Then** é conduzido à entrada e
   nenhuma cobrança é registrada.
5. **Given** ingressos emitidos para `cliente1`, **When** `cliente2` tenta vê-los, **Then** o
   servidor recusa.
6. **Given** a interface esconde o botão de pagar para papéis não-cliente, **When** a requisição é
   feita diretamente ao servidor, **Then** a recusa continua acontecendo — esconder o botão nunca
   é o controle de acesso.

---

### User Story 5 - Um QR que não dá para forjar (Priority: P2)

O código de cada ingresso é assinado pelo servidor. Um código inventado, alterado por um caractere
ou assinado com outro segredo não é aceito, e a verificação acontece antes de qualquer consulta ao
banco.

**Why this priority**: Princípio III. A feature da portaria vai depender inteiramente disto; se o
código nascer forjável aqui, a validação seguinte valida nada. É P2 porque a leitura na catraca é
da próxima feature — o que precisa nascer certo agora é o conteúdo assinado.

**Independent Test**: Tomar o código de um ingresso emitido, alterar um caractere, e conferir que
a verificação rejeita; gerar um código com outro segredo e conferir que também rejeita, sem que o
banco tenha sido consultado.

**Acceptance Scenarios**:

1. **Given** um ingresso emitido, **When** seu código é verificado, **Then** é aceito e identifica
   o ingresso e a sessão a que pertence.
2. **Given** um código com qualquer caractere alterado, **When** é verificado, **Then** é
   rejeitado.
3. **Given** um código assinado com um segredo diferente, **When** é verificado, **Then** é
   rejeitado.
4. **Given** um código qualquer inválido, **When** é verificado, **Then** a rejeição acontece
   **antes** de qualquer consulta ao banco de dados.
5. **Given** dois ingressos da mesma reserva, **When** seus códigos são comparados, **Then** são
   diferentes e nenhum permite deduzir o outro.
6. **Given** o código de um ingresso, **When** ele é inspecionado, **Then** não é um identificador
   sequencial nem adivinhável.

---

### Edge Cases

- **Dois pagamentos simultâneos da mesma reserva**: exatamente um conjunto de ingressos é emitido.
  A garantia é do banco, não de checagem prévia.
- **Confirmação acionada duas vezes por impaciência**: mesmo desfecho — um conjunto só.
- **Reserva que vence entre a leitura da tela e a confirmação**: recusada pelo servidor.
- **Sessão cancelada depois da reserva e antes do pagamento**: pagamento recusado com explicação.
- **Sessão que começou entre a reserva e o pagamento**: pagamento recusado com explicação.
- **Cliente recarrega a confirmação**: vê os mesmos ingressos, nunca duplicatas.
- **Cliente volta ao pagamento de uma reserva já paga**: é levado aos ingressos existentes.
- **Perda de conexão durante a cobrança**: ou a reserva está paga com todos os ingressos emitidos,
  ou nada aconteceu — nunca uma reserva paga com menos ingressos do que lugares.
- **Reserva de um lugar só**: gera exatamente um ingresso, e a tela não trata isso como caso raro.
- **Tela estreita**: o QR permanece legível e o resumo da compra permanece completo.
- **Navegação apenas por teclado**: o formulário inteiro é preenchível e submissível por teclado,
  e o resultado — aprovação ou recusa — é anunciado a tecnologias assistivas.
- **QR sem imagem carregada**: o código continua disponível em texto, para que a portaria possa
  digitá-lo conforme exige a constitution.

## Requirements *(mandatory)*

### Navegação e revisão

- **FR-001**: A confirmação de reserva da 007 DEVE conduzir ao pagamento daquela reserva.
- **FR-002**: A revisão DEVE exibir filme, sessão, sala, lugares reservados, valor unitário, valor
  total e o prazo restante da reserva.
- **FR-003**: O valor total DEVE ser calculado pelo servidor a partir do preço da sessão e da
  quantidade de lugares. Valor vindo do cliente NÃO PODE ser aceito.
- **FR-004**: Uma reserva inexistente ou de outro cliente DEVE resultar em recusa, sem revelar sua
  existência.

### Cobrança simulada

- **FR-005**: A cobrança DEVE ser simulada. Nenhuma transação financeira real e nenhum provedor
  externo de pagamento podem ser envolvidos.
- **FR-006**: O desfecho da cobrança DEVE ser **determinístico**, decidido pelo número do cartão
  informado. Sorteio, aleatoriedade ou percentual de falha NÃO SÃO PERMITIDOS.
- **FR-007**: A regra que mapeia número de cartão a desfecho DEVE estar documentada no README,
  com os números que aprovam e os que recusam.
- **FR-008**: DEVEM existir ao menos **três** motivos de recusa distintos — saldo insuficiente,
  cartão expirado e recusado pelo emissor —, cada um com seu próprio cartão de teste.
- **FR-009**: Cada motivo de recusa DEVE ter mensagem própria, escrita em português para o usuário
  final, dizendo o que houve e qual a próxima ação. Código de erro cru é violação.
- **FR-010**: Dados de cartão mal formados DEVEM produzir aviso de preenchimento, distinto de uma
  recusa de cobrança.
- **FR-011**: Nenhum dado de cartão pode ser persistido além do necessário para exibir a compra —
  o número completo NÃO PODE ser armazenado.
- **FR-012**: Toda tentativa de cobrança DEVE ficar registrada com seu desfecho, para que a
  aprovação seja rastreável.

### Emissão — o par indissociável

- **FR-013**: Um pagamento aprovado DEVE emitir os ingressos na **mesma** operação que o aprova.
  Não pode existir reserva paga sem ingresso, nem ingresso sem pagamento aprovado.
- **FR-014**: DEVE ser emitido **um ingresso por lugar reservado**, não um por reserva.
- **FR-015**: Cada ingresso DEVE identificar sessão, sala, lugar e comprador.
- **FR-016**: A emissão DEVE ocorrer por inteiro ou não ocorrer — nunca uma reserva paga com menos
  ingressos do que lugares.
- **FR-017**: Uma reserva paga DEVE ser distinguível de uma reserva viva, vencida ou cancelada.
- **FR-018**: Os lugares de uma reserva paga NÃO PODEM voltar ao estoque no vencimento original.
  A partir da aprovação, aquele lugar está vendido.

### Unicidade — o núcleo do Princípio II nesta feature

- **FR-019**: Uma mesma reserva NUNCA pode gerar dois conjuntos de ingressos, e um mesmo lugar
  reservado NUNCA pode ter dois ingressos. Esta garantia DEVE ser imposta pelo **banco de dados**,
  não apenas pela aplicação.
- **FR-020**: A aprovação e a emissão DEVEM ocorrer dentro de uma transação; a leitura que
  antecede a escrita DEVE bloquear as linhas envolvidas.
- **FR-021**: Dois pagamentos simultâneos da mesma reserva DEVEM resultar em exatamente uma
  aprovação e um único conjunto de ingressos; o perdedor recebe explicação clara.
- **FR-022**: Confirmar o pagamento duas vezes NÃO PODE emitir dois conjuntos de ingressos.
- **FR-023**: Uma reserva **vencida** NÃO PODE ser paga.
- **FR-024**: Uma reserva **cancelada** NÃO PODE ser paga.
- **FR-025**: Uma reserva de sessão cancelada ou já iniciada NÃO PODE ser paga.

### Recusa e prazo

- **FR-026**: Uma recusa NÃO PODE liberar os lugares. A reserva permanece viva até seu vencimento
  original — ver a seção "Leitura do Princípio II sobre a recusa".
- **FR-027**: Uma recusa NÃO PODE alterar, encurtar nem estender o vencimento da reserva.
- **FR-028**: O cliente DEVE poder tentar pagar novamente enquanto a reserva não vencer.
- **FR-029**: A decisão sobre o prazo DEVE ser do servidor. O contador exibido é informativo.

### Código em QR

- **FR-030**: O código do ingresso DEVE ser assinado criptograficamente pelo servidor.
- **FR-031**: O segredo de assinatura DEVE ser **próprio desta finalidade e distinto da chave
  secreta da aplicação**, NUNCA pode chegar ao front-end, e DEVE constar no `.env.example`.
- **FR-032**: O código NÃO PODE ser um identificador adivinhável — nem sequencial, nem
  identificador cru, nem dado do pedido concatenado.
- **FR-033**: O conteúdo do código DEVE carregar a **identidade da sessão**, para que a portaria
  possa distinguir "sessão errada" de "inválido" na feature seguinte.
- **FR-034**: A verificação da assinatura DEVE acontecer **antes de qualquer consulta ao banco**.
- **FR-035**: Um código adulterado DEVE ser rejeitado.
- **FR-036**: Um código assinado com outro segredo DEVE ser rejeitado.
- **FR-037**: Cada ingresso DEVE ter código distinto, e um código não pode permitir deduzir outro.
- **FR-038**: O código DEVE estar disponível também em texto legível, além da imagem do QR, porque
  a constitution exige digitação manual como alternativa sempre disponível na portaria.

### Autorização

- **FR-039**: Apenas usuários com papel de **cliente** podem pagar.
- **FR-040**: Apenas o **dono** da reserva pode pagá-la.
- **FR-041**: Organizador e portaria DEVEM receber recusa por papel ao tentar pagar.
- **FR-042**: A recusa DEVE acontecer no servidor. Esconder o botão na interface não conta como
  controle de acesso.
- **FR-043**: Um cliente NÃO PODE ver ingressos de outro cliente.
- **FR-044**: Um visitante sem sessão ativa que tente pagar DEVE ser conduzido à entrada, sem que
  nenhuma cobrança seja registrada.

### Estados e mensagens

- **FR-045**: Recusa por cartão, reserva vencida, reserva já paga, reserva cancelada, sessão
  cancelada ou iniciada, e recusa por papel DEVEM ter mensagem própria em português, dizendo o que
  houve e a próxima ação.
- **FR-046**: Nenhum estado pode exibir texto genérico de erro nem área em branco.
- **FR-047**: O resultado da cobrança DEVE ser anunciado a tecnologias assistivas.
- **FR-048**: O pagamento e a emissão DEVEM funcionar com o catálogo externo indisponível.

### Preservação

- **FR-049**: Nenhuma asserção de teste das features 001–007 pode ser alterada.
- **FR-050**: Nenhum contrato de API existente pode mudar de forma.
- **FR-051**: A disciplina de tokens da 006 DEVE ser mantida: nenhum valor de cor, espaçamento,
  tipografia, raio ou duração fora dos tokens.
- **FR-052**: O README DEVE ser atualizado com a nova variável de ambiente e com os cartões de
  teste.

### Key Entities

- **Pagamento**: uma tentativa de cobrança simulada sobre uma reserva, com desfecho (aprovado ou
  recusado), motivo em caso de recusa, valor e instante. Uma reserva pode ter várias tentativas
  recusadas e **no máximo uma** aprovada — é aqui que a unicidade de FR-019 começa.
- **Ingresso**: o direito de uma pessoa entrar na sala, **um por lugar reservado**. Pertence a uma
  ocupação de assento e carrega o código assinado. Não podem existir dois ingressos para a mesma
  ocupação — é a outra metade da unicidade de FR-019.
- **Código do ingresso**: o conteúdo assinado que vai para o QR. Carrega a identidade do ingresso
  e a da sessão, e é verificável sem tocar o banco.
- **Reserva** *(existente, ampliada)*: ganha o desfecho **paga**, que a distingue de viva, vencida
  e cancelada, e que retira seus lugares do estoque em definitivo.

## Success Criteria *(mandatory)*

- **SC-001**: A partir da confirmação da reserva, o cliente chega ao pagamento em 1 interação.
- **SC-002**: Um cliente conclui o pagamento e vê seus ingressos com QR em menos de 2 minutos,
  bem dentro dos 10 minutos da reserva.
- **SC-003**: Uma reserva de N lugares aprovada produz exatamente N ingressos, com N códigos
  distintos.
- **SC-004**: Dois pagamentos simultâneos da mesma reserva resultam em exatamente uma aprovação e
  um único conjunto de ingressos — verificável por teste automatizado de concorrência que
  **falha** se a garantia do banco for removida.
- **SC-005**: Nenhuma sequência de operações produz dois ingressos para o mesmo lugar da mesma
  sessão, nem uma reserva paga sem ingressos.
- **SC-006**: Os três motivos de recusa são alcançáveis pelo avaliador de forma determinística,
  seguindo apenas o README, e produzem três mensagens distintas em português.
- **SC-007**: Após uma recusa, os lugares continuam reservados e o vencimento continua o mesmo;
  uma nova tentativa aprovada dentro do prazo emite os ingressos.
- **SC-008**: Uma reserva vencida não pode ser paga, e a recusa vem do servidor.
- **SC-009**: Uma reserva já paga não emite um segundo conjunto de ingressos em nenhuma tentativa.
- **SC-010**: Um código adulterado e um código assinado com outro segredo são rejeitados, e a
  rejeição ocorre sem consulta ao banco — verificável por teste automatizado.
- **SC-011**: O segredo de assinatura não aparece em nenhuma resposta enviada ao navegador, e está
  declarado no `.env.example`.
- **SC-012**: Organizador, portaria e cliente que não é dono recebem recusa do servidor ao tentar
  pagar, e a recusa persiste quando a interface é contornada.
- **SC-013**: Nenhum estado exibe texto genérico de erro nem área em branco.
- **SC-014**: O pagamento e a emissão permanecem funcionais com o catálogo externo fora do ar.
- **SC-015**: As asserções de teste das features 001–007 continuam passando sem alteração.

## Assumptions

- **Regra dos cartões de teste**: assume-se decisão por número de cartão, na convenção já
  reconhecível de ambientes de teste de pagamento, com quatro números documentados no README:

  | Número | Desfecho | Mensagem ao cliente |
  |---|---|---|
  | `4242 4242 4242 4242` | Aprovado | — |
  | `4000 0000 0000 9995` | Recusado | Saldo insuficiente |
  | `4000 0000 0000 0069` | Recusado | Cartão expirado |
  | `4000 0000 0000 0002` | Recusado | Recusado pelo emissor |

  Qualquer outro número bem formado é aprovado, para que o avaliador não precise consultar a
  tabela só para ver o caminho feliz. A tabela é o contrato: mudar um número exige mudar o README
  na mesma alteração.

- **Meio de pagamento**: assume-se **cartão de crédito** como único meio simulado. Adicionar Pix
  ou boleto multiplicaria telas sem exercitar nenhum princípio novo.

- **Campos do formulário**: assume-se número, nome impresso, validade e código de segurança —
  o conjunto mínimo que torna a simulação reconhecível. Validade e código de segurança são
  validados quanto à forma, mas não participam da decisão de aprovar ou recusar, que é do número.

- **Tentativas ilimitadas dentro do prazo**: assume-se que não há limite de tentativas enquanto a
  reserva não vencer. O prazo de dez minutos já é o limite natural, e um contador de tentativas
  criaria um segundo motivo de bloqueio para o avaliador explicar.

- **Confirmação com endereço próprio**: assume-se que a confirmação com os ingressos tem endereço
  estável, acessível ao dono enquanto a sessão de navegação durar — recarregar a página não pode
  fazer o ingresso desaparecer. A **lista** de todos os ingressos do cliente ("Meus ingressos") e
  o link de compartilhamento continuam fora, na feature seguinte.

- **Vencimento inalterado pela tentativa**: assume-se que nem a tentativa nem a recusa tocam o
  instante de vencimento da reserva. Estender o prazo a cada tentativa transformaria o cartão
  recusado em ferramenta para segurar o lugar indefinidamente.

- **A imagem do QR é gerada a partir do código, não é o código**: assume-se que o conteúdo
  assinado é a fonte da verdade e a imagem é uma representação dele. Por isso o texto do código
  aparece junto, e por isso a digitação manual da portaria continua possível na feature seguinte.

- **Preço congelado na reserva**: assume-se que o valor cobrado é o preço da sessão no momento da
  cobrança. O organizador não altera preço de sessão publicada em nenhuma feature entregue até
  aqui, então a distinção não é observável agora — mas fica registrada para quando o painel do
  organizador existir.

- **Sem estorno e sem cancelamento após o pagamento**: assume-se que um ingresso emitido não é
  desfeito nesta feature. Cancelamento com devolução ao estoque está listado na constitution como
  item posterior ao fluxo completo.

### Escopo excluído

Área "Meus ingressos" e link de compartilhamento · tela de portaria, leitura por câmera e
transição para "utilizado" — a marcação e a garantia de validação única nascem juntas na feature
da portaria, pelo mesmo cuidado da 007 · painel do organizador · nota fiscal · revenda · e-mail ·
recuperação de senha · estorno e cancelamento de compra · meios de pagamento além do cartão.

### Dependências

- Reserva com prazo e `UNIQUE(sessão, assento)` (`007-seat-selection`)
- Autenticação com os três papéis (`003-user-authentication`)
- Sessões publicadas com preço e seed dos quatro usuários (`005`)
- Disciplina de tokens (`006`)
