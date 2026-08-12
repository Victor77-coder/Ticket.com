# Research — Validação de Ingressos na Portaria

**Feature**: `010-gate-validation` · **Data**: 2026-08-12

Quatorze decisões. As que mais importam são **R1** (a garantia muda de forma pela primeira vez),
**R3** — a armadilha desta feature, que é o `if` mais natural que existe —, **R6** (a dependência
nova) e **R11** (o retorno da armadilha da 009, agora conhecida).

---

## R1 — A garantia não é uma constraint. É escrita condicional atômica

**Decisão**: a marcação de uso é **um** `UPDATE` com predicado:

```sql
UPDATE screening_ticket
   SET used_at = now()
 WHERE id = %s AND used_at IS NULL
```

O número de linhas afetadas **é o desfecho**: `1` → **válido**, `0` → **já utilizado**.

**Racional**: é a primeira vez em quatro features que a garantia de unicidade não tem a forma de um
índice, e vale registrar por quê — a série vinha assim:

| Feature | Garantia | Forma |
|---|---|---|
| 007 | um assento por sessão | `UNIQUE` absoluta |
| 008 | um pagamento aprovado por reserva | `UNIQUE` parcial |
| 009 | um link ativo por ingresso | `UNIQUE` parcial |
| 010 | **uma validação por ingresso** | **`UPDATE` condicional** |

A diferença não é de rigor, é de natureza do invariante. As três primeiras proíbem **duas linhas
coexistirem** — e isso um índice expressa. Esta proíbe **uma transição acontecer duas vezes**, sobre
a mesma linha. Não existe índice que diga "esta coluna só pode sair de nulo uma vez": uma `CHECK`
enxerga o valor final, não a história; uma `UNIQUE` não tem duas linhas para comparar.

**O que torna o `UPDATE` condicional suficiente**: no PostgreSQL, sob `READ COMMITTED`, o segundo
`UPDATE` sobre a mesma linha **bloqueia** até o primeiro confirmar e então **reavalia o predicado**
com a versão nova. Encontra `used_at` preenchido, não casa com `IS NULL`, e afeta zero linhas. A
serialização é do banco; a aplicação não decide nada.

**Alternativas rejeitadas**:

- **`SELECT ... FOR UPDATE` e depois escrever** — correto, e mais frágil: são duas instruções, e a
  correção passa a depender de ninguém as separar numa refatoração. O `UPDATE` condicional é
  indivisível por construção. (A 008 usa `FOR UPDATE` porque lá há revalidação de **várias**
  condições sob o bloqueio; aqui a condição é uma só e cabe no `WHERE`.)
- **Coluna booleana `used` em vez de instante** — perderia FR-021 ("já utilizado" informa **quando**),
  que é o que permite ao operador julgar se é a mesma pessoa voltando.
- **Tabela de eventos de validação com `UNIQUE(ingresso)`** — devolveria a garantia ao formato de
  índice, à custa de uma tabela inteira para guardar um instante. Foi considerada seriamente e
  rejeitada por isso: acrescenta um modelo para não mudar de técnica.

---

## R2 — O desfecho vem da ESCRITA, nunca da leitura

**Decisão**: o serviço deriva o desfecho do **resultado do `UPDATE`**, e não de ter lido
`used_at` antes.

**Racional**: é a diferença entre correto e quase-correto, e é invisível em teste de uma thread só.
Ver R3 — esta decisão só existe por causa daquela armadilha.

Consequência prática: o objeto lido antes da escrita serve para **duas** coisas apenas — conferir a
sessão (FR-030) e montar a resposta (lugar, filme, horário). O campo `used_at` daquela leitura
**não** decide nada.

---

## R3 — A armadilha: o `if` mais natural que existe

**O código que qualquer pessoa escreve primeiro**, e que está errado:

```python
ingresso = Ticket.objects.get(public_id=...)
if ingresso.used_at is not None:
    return JA_UTILIZADO
ingresso.used_at = timezone.now()
ingresso.save()
return VALIDO
```

**Por que é errado**: é leitura seguida de escrita, o padrão exato que a concorrência quebra. Duas
requisições leem `None`, ambas passam pelo `if`, ambas escrevem. Duas pessoas entram com o mesmo
ingresso, e o Princípio III — "a primeira leitura marca o ingresso como utilizado; leituras
subsequentes retornam 'já utilizado'" — foi violado sem que nada no banco reclamasse.

**Por que passa despercebido**: em teste de uma thread só, ele passa. Passa em todos os cenários
funcionais. Passa na revisão, porque *lê* como a regra escrita na spec. É a mesma classe de erro que
a 007 evitou ao escolher chave de idempotência em vez de "existe reserva parecida?", e que a 009
evitou ao deixar a corrida de link para a constraint.

**A diferença desta vez, e é ela que exige cuidado**: nas três features anteriores, quem pegava o
erro era o **banco** — a constraint recusava, o teste via a recusa. Aqui **não há constraint para
recusar**. Se a implementação usar o `if`, o banco aceita as duas escritas em silêncio. A única
coisa entre o projeto e uma portaria que deixa passar dois é o teste de concorrência.

**Como fica protegido**:

1. `test_gate_concurrency.py` com transação real e threads, escrito **antes** do serviço;
2. verificação explícita — trocar o `UPDATE` condicional pelo `if` e conferir que o teste **falha**;
3. o serviço deriva o desfecho do `rowcount`, e o motivo fica escrito ao lado da linha.

---

## R4 — A ordem do pipeline, e o que cada etapa pode escrever

**Decisão**:

```text
1. assinatura confere?            não → INVÁLIDO      (sem tocar o banco)
2. ingresso existe?               não → INVÁLIDO
3. o `s` do código bate com a
   sessão do ingresso no banco?   não → INVÁLIDO      (inconsistência)
4. a sessão do ingresso é a
   sessão DA PORTA?               não → SESSÃO ERRADA (sem escrever)
5. UPDATE condicional             0 linhas → JÁ UTILIZADO
                                  1 linha  → VÁLIDO
```

**Racional de cada fronteira**:

- **1 antes de tudo** — Princípio III, e a 008 já deixou a função pura pronta para isso.
- **2 e 3 devolvem o mesmo INVÁLIDO** — quem apresenta não recebe pista sobre onde o palpite chegou
  perto (FR-029). O passo 3 é defesa em profundidade: o `s` é assinado e confiável, mas comparar com
  o banco custa nada e transforma uma inconsistência de dados em desfecho claro em vez de exceção.
- **4 antes de 5** — decisão registrada na spec (FR-030). Um ingresso de outra sessão **e** já
  utilizado responde **sessão errada**, porque é essa a informação que muda a ação do operador. A
  ordem inversa consumiria o desfecho mais útil.
- **4 não escreve** (FR-031) — é o que faz o ingresso continuar valendo na porta certa. Um ingresso
  legítimo queimado na porta errada seria pior do que não ter a checagem.

---

## R5 — Todos os quatro desfechos respondem `200`

**Decisão**: os quatro são `200`, distinguidos por um campo `situacao` com valor fixo. `400` só para
entrada malformada (código vazio, sessão ausente), `403` para papel errado, `401` para sem sessão.

**Racional**: nenhum dos quatro é erro **da requisição**. A portaria perguntou "posso deixar entrar?"
e recebeu resposta; "não" é uma resposta, não uma falha. Mapear **já utilizado** para `409` ou
**inválido** para `422` faria o front distinguir desfecho de negócio por semântica de HTTP, e
qualquer camada intermediária que trate `4xx` como erro passaria a esconder um desfecho legítimo.

**Diferença deliberada em relação à 008**, para não parecer incoerência: lá a recusa de cartão é
`402` porque o front precisa distinguir "corrija o formulário" (`400`) de "troque de cartão"
(`402`) — dois **caminhos de recuperação** diferentes. Aqui os quatro desfechos vão para a mesma
tela e o front escolhe a apresentação pelo campo `situacao`, nunca por interpretar texto nem status.

---

## R6 — Uma dependência nova: o decodificador de QR no navegador

**Decisão**: `jsQR` — JavaScript puro, sem dependências transitivas, versão fixada. Os quadros do
vídeo vão para um `<canvas>` e o decodificador roda sobre os pixels.

**Racional**: é a mesma justificativa que a 008 usou para `qrcode` do lado do servidor, do outro
lado do vidro. Decodificação de QR é um padrão publicado com casos de borda reais — localização dos
padrões de alinhamento, correção de erro, perspectiva, binarização sob luz irregular. Reimplementar
seria indefensável; é exatamente onde uma dependência se paga.

**Alternativas rejeitadas**:

- **`BarcodeDetector` nativo do navegador** — zero dependência e é tentador, porque é provável que o
  avaliador use um navegador que o tem. Rejeitado como caminho único: não existe em toda parte, e a
  portaria não pode depender da escolha de navegador. Rejeitado **também** como caminho preferencial
  com `jsQR` de reserva: seriam dois decodificadores com comportamentos diferentes, e o de reserva é
  o que apodrece sem ninguém notar. Um caminho só, testado.
- **`@zxing/library`** — mais completo e bem maior, para ler um formato só.
- **Enviar o quadro ao servidor para decodificar** — mandaria imagem da fila do cinema pela rede a
  cada quadro, para resolver no servidor um problema que é do cliente.

**Registrado em Complexity Tracking.**

---

## R7 — A câmera só funciona em contexto seguro, e a digitação é o que salva

**Decisão**: nenhuma tentativa de contornar. A tela detecta a indisponibilidade e explica; a
digitação manual continua visível o tempo todo.

**Racional**: `getUserMedia` exige contexto seguro. `localhost` conta, então o avaliador que abrir
`http://localhost:5003/portaria` na própria máquina tem câmera. Quem abrir pelo IP da rede local —
para testar com o celular, que é o gesto natural — **não tem**, e nenhuma configuração da aplicação
muda isso.

O que torna isso aceitável em vez de um buraco: a constitution já exige que a digitação manual
esteja "sempre disponível". A exigência que parecia redundante é justamente a que mantém a portaria
funcionando no cenário mais provável de demonstração. Vai para o README, não para uma nota de
rodapé.

---

## R8 — Uma apresentação, um desfecho

**Decisão**: três regras somadas no cliente:

1. enquanto uma validação está em andamento, o laço de leitura não dispara outra;
2. o **mesmo** conteúdo decodificado é ignorado por alguns segundos após ter sido submetido;
3. o desfecho permanece na tela até a leitura seguinte (FR-026) — nada se apaga sozinho.

**Racional**: um QR parado na frente da câmera decodifica dezenas de vezes por segundo. Sem as
regras, a primeira leitura marca o uso e a segunda — 40 ms depois, do mesmo aparelho, da mesma
pessoa — responde **já utilizado**. O sistema estaria **inteiramente correto** e a portaria veria
uma contradição na cara.

Vale nomear o que **não** resolve: o servidor ser idempotente não resolve. Idempotência garante que
o estado não se corrompe, não que a pessoa não veja duas respostas contraditórias. É um defeito de
interface causado por uma característica do hardware, e só se conserta onde o hardware está.

---

## R9 — A sessão da porta vive no navegador, e é enviada em cada validação

**Decisão**: a escolha da sessão é guardada no armazenamento local do navegador e viaja no corpo de
cada requisição de validação. O servidor confere que ela existe e que quem chama é portaria.

**Racional**: a spec exige que a escolha sobreviva ao recarregamento e seja **por posto, não por
conta** — duas portas podem operar com a mesma conta de seed, e guardar a escolha no usuário faria
uma sobrescrever a outra.

**Sobre o cliente controlar o valor**: um operador de portaria pode enviar qualquer sessão. Isso
**não** é escalada de privilégio — ele obteria o mesmo resultado escolhendo aquela sessão no menu.
A autorização que importa continua sendo o papel, conferida no servidor. Registrar isso evita que
alguém "endureça" o ponto errado numa revisão futura.

**Alternativa rejeitada**: guardar a sessão da porta no servidor, atrelada ao usuário. Quebra o
requisito de dois postos com a mesma conta, que é exatamente o cenário do seed.

---

## R10 — O desfecho é um valor fixo, não uma frase

**Decisão**: a resposta traz `situacao` com um de quatro valores fixos, mais a frase em pt-BR e o
contexto de cada caso (lugar, instante do uso, sessão do ingresso).

**Racional**: mesmo padrão do `motivo` da 008. A tela escolhe símbolo, texto e destaque pelo valor —
nunca interpretando a frase. Frase é apresentação e muda numa revisão de redação; se a tela
dependesse dela, a revisão quebraria a interface.

E é o que sustenta FR-017: os quatro precisam ser distinguíveis **sem depender de cor**. Com um
valor fixo, cada desfecho tem símbolo e título próprios por construção.

---

## R11 — A armadilha da 009 volta, e agora é conhecida

**Decisão**: a lista de sessões que a portaria pode receber **não** usa `sellable()`.

**Racional**: `sellable()` é `published()` **e** `starts_at > now()`. A porta precisa exatamente do
que aquele segundo termo exclui: **a sessão que já começou**. Gente chega atrasada, e a portaria
valida durante a sessão inteira — uma lista que some com a sessão em andamento é uma lista que não
serve à porta.

É a segunda vez que o mesmo filtro é o erro natural: a 009 registrou que ele esvaziaria o histórico
de ingressos. A regra que emerge das duas, e que vale escrever no selector: **`sellable()` responde
"dá para comprar?", e nenhuma outra pergunta.**

Sessões **canceladas** ficam fora da lista — não há entrada a receber. O ingresso de uma sessão
cancelada continua alcançando a portaria e sai como **sessão errada**, com o aviso do cancelamento
(FR-023).

---

## R12 — `num_queries == 0` é medido no serviço, não na view

**Decisão**: a prova de FR-027 é `django_assert_num_queries(0)` em volta da **função de validação**,
com um código de assinatura inválida.

**Racional**: na view a asserção seria falsa por um motivo que não tem a ver com a feature — a
autenticação por sessão consulta o banco antes de qualquer código nosso rodar. Medir ali obrigaria a
uma contagem "esperada" que ninguém sabe defender, e que muda quando o Django muda.

É a mesma escolha da 008, que mediu a função pura em vez do endpoint. A spec já está escrita na
forma certa: "antes de qualquer consulta ao **registro de ingressos**".

---

## R13 — Os quatro desfechos na tela: símbolo, título e disposição

**Decisão**: cada desfecho recebe símbolo próprio, título próprio em pt-BR e uma faixa de destaque.
A cor é o **quarto** sinal, nunca o primeiro.

| Desfecho | Símbolo | Título | Token de cor |
|---|---|---|---|
| válido | ✓ | Pode entrar | `--cor-sucesso` |
| já utilizado | ⟳ | Este ingresso já foi usado | `--cor-alerta` |
| sessão errada | ⇄ | Ingresso de outra sessão | `--cor-alerta` |
| inválido | ✕ | Ingresso não reconhecido | `--cor-erro` |

**Racional**: **já utilizado** e **sessão errada** compartilham a cor de alerta de propósito — para
o operador as duas significam "não entra por aqui, e não é fraude". Se a cor fosse o sinal
principal, elas seriam indistinguíveis; como o sinal principal é símbolo + título, a cor pode
agrupar por gravidade sem perder a distinção. É a mesma disciplina que o mapa de assentos da 007
aplica aos quatro estados de poltrona.

**FR-019 (legível à distância de um braço)** vira decisão de tamanho: o título do desfecho usa o
maior degrau tipográfico da tela, e o detalhe fica abaixo.

---

## R14 — O estado de uso não pode vazar para as telas do cliente

**Decisão**: `TicketSerializer` e `MeuIngressoSerializer` **não** ganham o campo de uso (FR-048).

**Racional**: é a mesma pressão de crescimento que a 009 registrou, agora vindo do outro lado. O
campo passa a existir no modelo nesta feature, e acrescentá-lo ao serializer é uma linha — a partir
daí "utilizado" aparece na área do cliente e na **página compartilhada pública**, que é onde importa.

A 009 deixou a ausência escrita no modelo e nos serializers justamente para este momento. Exibir o
estado de uso ao cliente é decisão de produto que esta feature não precisa tomar para fechar o
fluxo, e `test_share_link_leakage.py` — que verifica a resposta pública por inclusão — pega o
vazamento se ele acontecer.
