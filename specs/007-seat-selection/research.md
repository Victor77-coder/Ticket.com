# Phase 0 — Research: Escolha de Assentos

**Feature**: `007-seat-selection` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado. As decisões R1 a R4 são o núcleo
do Princípio II — as demais são o que sustenta a feature em volta delas.

---

## R1. Onde vive a garantia de não vender duas vezes

**Decision**: constraint `UNIQUE(sessão, assento)` **absoluta**, sem predicado, na tabela que
representa a ocupação.

**Rationale**: a constitution exige a garantia no banco, não na aplicação. Uma constraint sem
condição é a forma mais forte disso: nenhuma sequência de operações, nenhum bug de aplicação e
nenhum acesso direto ao banco consegue produzir duas ocupações do mesmo lugar.

**Alternatives considered**:

- **Índice parcial sobre "reserva viva"** — seria a saída natural para conciliar com a expiração:
  `UNIQUE(sessão, assento) WHERE expira_em > now()`. **É impossível.** O PostgreSQL exige que o
  predicado de um índice parcial use apenas funções imutáveis, e `now()` não é. Um índice cujo
  predicado muda com o relógio não pode existir — o banco não teria como manter a árvore
  consistente.
- **Índice parcial sobre uma coluna de status** — `WHERE status = 'ativa'` é imutável e funciona.
  Mas exige que algo **mude** o status ao expirar, ou seja, uma rotina agendada — e o spec decidiu
  expiração por consulta justamente para não ter a janela que uma rotina cria.
- **Validar só na aplicação** — rejeitado pela constitution, e com razão: é o caminho que produz o
  bug clássico de venda dupla sob concorrência.

---

## R2. Como a constraint absoluta convive com a expiração

**Decision**: a linha vencida é **removida sob bloqueio, dentro da própria transação de reserva**.

```
transação:
    bloqueia as linhas de ocupação daqueles assentos   (SELECT ... FOR UPDATE)
    para cada linha bloqueada:
        se a reserva dela venceu  → apaga
        senão                     → recusa a reserva inteira
    insere as novas ocupações
```

**Rationale**: é o que concilia constraint absoluta com liberação por consulta, sem rotina
agendada e sem janela de inconsistência.

O bloqueio é essencial e a ordem importa: apagar **antes** de bloquear deixaria duas transações
apagarem a mesma linha vencida e ambas seguirem para inserir. Com o bloqueio, a segunda espera, e
quando prossegue a primeira já commitou.

**Consequência assumida**: uma reserva vencida sobrevive no banco até alguém tentar aquele
assento. Isso é aceitável e até desejável — a linha é registro histórico até ser reciclada, e
ninguém a enxerga como ocupação porque a leitura já a trata como vencida.

---

## R3. A violação de unicidade é resultado esperado

**Decision**: capturar o erro de integridade na criação da reserva e traduzi-lo em "este lugar
acabou de ser tomado". **Não** é caso excepcional a ser registrado como falha.

**Rationale**: o bloqueio de R2 resolve a maioria das corridas, mas não todas. Em nível de
isolamento *read committed*, duas transações podem não enxergar a linha recém-inserida uma da
outra quando a linha antiga foi apagada — a segunda tenta inserir e bate na constraint.

Isso não é defeito: **é a rede funcionando**. A constraint é o árbitro final, e bater nela é o
comportamento correto quando o bloqueio não cobriu. Tratar como erro 500 esconderia o mecanismo
que mais importa.

**O que isso obriga**: o teste de concorrência tem de aceitar as duas formas de derrota — recusa
pelo bloqueio e recusa pela constraint. O que ele exige é que **exatamente uma** vença e que o
banco nunca fique com duplicata.

---

## R4. Como o teste de concorrência prova alguma coisa

**Decision**: duas threads reais, com **conexões de banco separadas**, sincronizadas por barreira,
tentando o mesmo assento. O teste roda com transação real, não dentro da transação de teste
padrão.

**Rationale**: é o ponto onde é mais fácil ter um teste verde que não testa nada.

O `pytest-django` por padrão envolve cada teste numa transação e faz *rollback* ao fim. Duas
threads nesse modo **compartilham a mesma conexão e a mesma transação** — não há corrida, não há
bloqueio entre elas, e o teste passa sem exercitar concorrência alguma. Passaria até com a
constraint removida.

Exige então: transação real por thread, barreira para que as duas cheguem juntas ao ponto crítico,
e fechamento explícito das conexões ao fim de cada thread.

**O que o teste afirma**:

1. exatamente uma das duas obtém a reserva
2. a outra recebe recusa — por bloqueio ou por constraint, tanto faz
3. o banco tem exatamente **uma** ocupação daquele assento naquela sessão

**Verificação de que o teste testa**: removendo a constraint, ele precisa **falhar**. Um teste de
concorrência que passa sem a constraint não está provando o Princípio II.

---

## R5. Por que `ReservedSeat` guarda a sessão

**Decision**: a linha de ocupação aponta para a reserva **e** carrega a sessão.

**Rationale**: a constraint precisa ser `UNIQUE(sessão, assento)`, e ambas as colunas têm de estar
na mesma tabela. A sessão já é acessível via `reserva.sessão`, mas o Django não expressa unicidade
através de travessia de chave estrangeira — e nem o PostgreSQL, sem um gatilho.

**Alternatives considered**:

- **`UNIQUE(reserva, assento)`** — impede repetir o assento **dentro** de uma reserva, que é o
  problema errado. Duas reservas diferentes continuariam podendo tomar o mesmo lugar.
- **Gatilho de banco** — funcionaria sem denormalizar, mas move a regra para fora do modelo, onde
  ela some da leitura do código e das migrações.
- **Colocar tudo em `Reservation` com um assento por reserva** — a constraint ficaria natural, mas
  quebraria a ideia de reserva como unidade que segue para o pagamento: comprar três lugares
  viraria três reservas e três pagamentos.

**Como a duplicação é mantida honesta**: `screening` é preenchido a partir de `reserva.screening`
no momento da criação, num único lugar do código, e nunca é editável depois.

---

## R6. Assentos persistidos, não derivados

**Decision**: tabela `Seat` por sala, com fileira, número e tipo. Gerada a partir da capacidade
pelo comando de seed.

**Rationale**: a ocupação aponta para o assento, então ele precisa de identidade estável. Derivar
o mapa da capacidade a cada requisição funcionaria para desenhar, mas não daria a chave
estrangeira que a constraint exige.

Persistir também é o que permite o tipo **acessibilidade** — informação que não sai da capacidade.

**Por que no seed e não numa migração de dados**: uma migração prenderia a disposição da sala ao
histórico de migrações, e mudar o desenho exigiria nova migração. No seed, basta rodar de novo.

---

## R7. A disposição da sala

**Decision**: fileiras de **10 lugares**, letra por fileira (A, B, C…), número de 1 a 10, corredor
visual entre o quinto e o sexto. Capacidade determina a quantidade de fileiras. **3 lugares de
acessibilidade** na última fileira.

| Sala | Capacidade | Fileiras | Acessibilidade |
|---|---|---|---|
| Sala 1 | 60 | A–F | 3 na fileira F |
| Sala 2 | 40 | A–D | 3 na fileira D |

**Rationale**: dez por fileira com corredor central é a convenção que qualquer pessoa reconhece
como sala de cinema, e mantém o mapa legível em tela estreita. Capacidade que não fecha a fileira
deixa a última incompleta — sem inventar lugares que a sala não tem.

Acessibilidade na última fileira é a convenção de sala real: é onde há espaço para cadeira de
rodas sem obstruir a passagem.

---

## R8. Como a disponibilidade é consultada

**Decision**: **uma** consulta por mapa. Os assentos da sala com anotação de ocupação, feita por
subconsulta sobre as ocupações não vencidas daquela sessão.

**Rationale**: uma consulta por assento daria 60 consultas por mapa. O padrão já usado no projeto
— anotação e `prefetch_related` nos seletores da 001 e da 004 — resolve em uma.

**Regra da ocupação**: um assento está tomado quando existe ocupação para ele naquela sessão cuja
reserva **não venceu**. Reserva vencida não conta, sem depender de rotina ter passado.

---

## R9. Idempotência do envio duplo

**Decision**: o cliente envia uma **chave de idempotência** junto da confirmação. Uma segunda
requisição com a mesma chave devolve a reserva já criada, em vez de criar outra.

**Rationale**: FR-023. Verificar "já existe reserva parecida?" antes de criar é justamente o
padrão que a concorrência quebra — duas requisições verificam ao mesmo tempo, ambas não encontram
nada, ambas criam.

A chave resolve pela mesma via de todo o resto: uma constraint. `UNIQUE(chave)` na reserva, e a
segunda tentativa bate nela e devolve a existente.

**Alternatives considered**: desabilitar o botão ao enviar. Resolve o clique duplo mas não a
requisição repetida por instabilidade de rede, que é o caso que produz reserva duplicada de
verdade.

---

## R10. Autorização

**Decision**: o endpoint de reserva exige papel **cliente**. Organizador e portaria recebem
recusa. Um cliente só alcança as próprias reservas.

**Rationale**: FR-024 a FR-027 e o Princípio IV. A recusa acontece na permissão do endpoint, não
na interface — esconder o botão não é controle de acesso, e o teste de acesso cruzado é o que
prova a diferença.

**O mapa é público** de propósito: ver onde há lugar não exige conta, e exigir login para olhar
afastaria o visitante antes de ele ter motivo para criar conta.

---

## R11. A tela do mapa

**Decision**: rota própria por sessão. Assentos são `<button>` reais, com estado em `aria-pressed`
e `aria-disabled`, e rótulo que inclui fileira, número e situação.

Os quatro estados se distinguem por **forma e rótulo**, não só por cor:

| Estado | Forma | Rótulo acessível |
|---|---|---|
| Livre | contorno | "Fileira A, lugar 3, livre" |
| Selecionado | preenchido em laranja, com marca | "…, selecionado" |
| Tomado | preenchido escuro, com traço | "…, indisponível" |
| Acessibilidade | contorno com símbolo | "…, reservado para acessibilidade" |

**Rationale**: FR-008 e FR-011. Botão real dá teclado, foco e semântica de graça — reconstruir
isso com `div` é o erro que torna mapas de assento inacessíveis.

---

## R12. Estratégia de testes

| Alvo | Tipo | Por quê |
|---|---|---|
| **Duas reservas simultâneas do mesmo assento** | back-end, threads reais | **Prova do Princípio II** — obrigatória pela constitution |
| Sem a constraint, o teste acima falha | back-end | Prova que o teste testa |
| Seleção com um assento indisponível não reserva nenhum | back-end | FR-019 — atomicidade |
| Reserva vencida libera o assento | back-end | FR-021 |
| Organizador e portaria recebem recusa | back-end | Gate do Princípio IV |
| Cliente não alcança reserva de outro | back-end | FR-027 |
| Envio duplo cria uma reserva só | back-end | FR-023 |
| Sessão em rascunho, cancelada ou passada recusa | back-end | FR-002, FR-003 |
| Resposta não vaza dado de gestão nem de outro cliente | back-end | Gate do Princípio IV |
| Quatro estados distinguíveis sem cor | front-end | FR-008 |
| Mapa operável só por teclado | front-end | FR-011, SC-008 |
| Limite de seleção | front-end | FR-013 |
| Percurso filme → sessão → mapa → reserva | e2e | Princípio I |

**Rationale**: a lista é maior que a das features anteriores porque esta é a única onde uma falha
significa vender o mesmo lugar duas vezes. O segundo item — provar que o teste falha sem a
constraint — não é excesso: sem ele, um teste de concorrência mal montado passa e dá falsa
segurança justamente no ponto mais crítico do sistema.
