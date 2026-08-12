---
description: "Task list for feature implementation"
---

# Tasks: Marca sem Laranja — Cor, Tipografia de Marca e Logo

**Input**: Design documents from `/specs/011-marca-sem-laranja/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/contraste.md](./contracts/contraste.md),
[contracts/anti-slop-review.md](./contracts/anti-slop-review.md), [quickstart.md](./quickstart.md)

**Tests**: **Sim, e um deles é a única defesa que a feature tem.** Trocar um valor de cor **não
quebra nenhum teste de comportamento**: os 197 testes de front-end continuam verdes com o contorno
de foco invisível, o texto do botão ilegível e o assento selecionado indistinguível do tomado.
Nenhum mede contraste, e nenhum vai começar a medir por acidente.

**E o teste tem forma de TDD por medida, não por convenção.** Escrito contra a paleta **antiga**, ele
**falha** em dois pontos: `A1` (a cor antiga está lá) e — descoberta da medição — **`D1`, porque o
laranja fica a ΔE 23.8 do `--cor-erro`, abaixo do mínimo de 25**. A paleta que está saindo já era
marginalmente confundível com a cor de erro. O teste vai do vermelho ao verde pela troca.

**Organization**: Cinco user stories, todas P1. As fases seguem a **ordem de dependência**, não a
numeração das histórias: a US2 (remover o laranja) é a menor e destrava todas as outras; a US1
(reconhecer a marca) é a última porque só pode ser avaliada com tudo no lugar.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivo diferente, sem dependência pendente)
- **[Story]**: US1 (identidade reconhecível), US2 (sem vestígio do laranja), US3 (a cor funciona),
  US4 (nome com desenho), US5 (nada de comportamento mudou)
- Todo caminho de arquivo é relativo à raiz do repositório

## Path Conventions

- **O único arquivo onde cor de marca é definida**: `frontend/styles/tokens.css`
- **A prova**: `frontend/tests/tokens.test.ts` — lê os tokens e mede
- **A marca**: `frontend/components/header/BrandMark.tsx` + `MarcaGrafica.tsx`
- **Os 12 consumidores**: **não devem ser tocados.** Se um precisar, um valor vazou dos tokens

---

## Phase 1: Setup

**Purpose**: Saber de onde se parte, e trazer a família da marca com a licença

- [X] T001 Rodar `docker compose exec backend pytest`, `docker compose exec frontend npm run test` e, de `frontend/`, `npx playwright test --workers=2`, registrando a linha de base: **360** back-end, **197** front-end em 14 arquivos, **41** e2e. É contra ela que SC-015 é medido no fim
- [X] T002 Registrar o estado atual da varredura, para comparar depois: `grep -rn "ff5c39\|ff7a5c\|255, 92, 57" frontend --exclude-dir=node_modules --exclude-dir=.next` deve devolver **4 linhas**, todas em `frontend/styles/tokens.css` (quickstart.md, percurso 1)
- [X] T003 Baixar a família da marca (Cabinet Grotesk, Fontshare) para `frontend/public/fontes/`, nos cortes efetivamente usados — **não a família inteira**, que arrastaria peso para nada
- [X] T004 Baixar o **arquivo de licença** da família para `frontend/public/fontes/`, conferir que permite uso comercial, e versioná-lo. FR-014 exige registro, e registro é o arquivo — não a lembrança de quem baixou

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: A prova que mede, escrita **antes** da troca.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

**⚠️ T005–T011 VÊM ANTES DA TROCA DE VALORES, e não é preferência de método.** Escrito depois, o
teste é escrito para os valores que já estão lá — e os limites viram descrição do que foi feito em
vez de regra. Escrito antes, ele **falha em A1 e D1** contra a paleta antiga, e a troca é o que o
torna verde.

- [X] T005 Escrever `frontend/tests/tokens.test.ts` com as funções de medida: luminância relativa, razão de contraste WCAG 2.1 e ΔE76 em CIELAB. Sem dependência nova — são vinte linhas de aritmética, e uma biblioteca de cor para isso seria peso para não escrever uma fórmula publicada
- [X] T006 Fazer o teste **ler `frontend/styles/tokens.css`** e extrair os valores por nome de token, com comentário registrando por quê: um teste que guarda a própria cópia da paleta passa a testar a cópia (contracts/contraste.md)
- [X] T007 [P] Implementar as sete verificações de contraste **C1–C7** de `contracts/contraste.md`, cada uma falhando com o nome do par e quanto faltou — uma falha que diz só "o contraste está ruim" obriga a refazer a medição para descobrir onde
- [X] T008 [P] Implementar **C4 e C5 como um par**: `--cor-sobre-destaque` medida sobre `--cor-destaque` **e** sobre `--cor-destaque-forte`. É o erro fácil da feature — medir o texto do botão só em repouso deixa de fora o hover, que é o estado em que a pessoa está quando vai clicar (R5)
- [X] T009 [P] Implementar as três verificações de distância **D1–D3**: ΔE mínimo de 25 entre `--cor-destaque` e cada cor de estado. É a mesma medida que eliminou o âmbar na pesquisa, agora congelada como regra (R1)
- [X] T010 [P] Implementar **A1**: nenhuma ocorrência de `ff5c39`, `ff7a5c` ou `255, 92, 57` em nenhum arquivo do front-end
- [X] T011 [P] Implementar **A2**: nenhum hexadecimal ou `rgba(` de cor de marca fora de `tokens.css`. É a disciplina da 006 verificada em vez de confiada — e o que garante que os 12 consumidores não precisaram ser tocados
- [X] T012 Rodar `npm run test -- tokens` **contra a paleta antiga** e conferir que ele falha em **A1** (a cor antiga está lá) e em **D1** (laranja a ΔE 23.8 do `--cor-erro`, abaixo de 25). Se passar, o teste não está medindo nada

**Checkpoint**: a prova existe e está vermelha pelos motivos certos.

---

## Phase 3: US2 — Nenhum vestígio do laranja (P1)

**Goal**: A cor antiga não sobrevive em canto nenhum.

**Independent Test**: Varrer o front-end pelos valores da cor antiga e obter zero ocorrências.

**É a menor fase da feature e a que destrava todas as outras** — cinco valores num arquivo.

- [X] T013 [US2] Substituir os cinco valores em `frontend/styles/tokens.css`: `--cor-destaque: #ff2e88`, `--cor-destaque-forte: #ff5ca3`, `--cor-destaque-fraca: rgba(255, 46, 136, 0.14)`, `--cor-destaque-vestigio: rgba(255, 46, 136, 0.2)`, `--cor-sobre-destaque: #12040a` (data-model.md)
- [X] T014 [US2] Reescrever os comentários dos tokens trocados: o de `--cor-sobre-destaque` diz "texto sobre o botão laranja" e o de `--cor-destaque-vestigio` diz "vestígio do laranja". Registrar no lugar deles o conceito novo — **neon de fachada** — e por que `-forte` é mais **clara** que a base: ela é o contorno de foco global e o hover de botões já preenchidos (R4)
- [X] T015 [US2] Registrar em `tokens.css`, junto do bloco de marca, que as opacidades de `-fraca` (0.14) e `-vestigio` (0.20) **não mudaram**: foram calibradas na 006 e alterá-las junto misturaria duas decisões
- [X] T016 [US2] Rodar `npm run test -- tokens` e conferir que **A1 e D1 passam a passar** — é a troca levando o teste do vermelho ao verde
- [X] T017 [US2] Conferir que **nenhum dos 12 arquivos consumidores** foi editado: `git status --short frontend/components frontend/app | grep -c module.css` deve ser 0 nesta fase. Se algum apareceu, um valor de cor vazou dos tokens
- [X] T018 [P] [US2] Conferir os dois usos de `--cor-destaque-vestigio` — o gradiente radial do substituto de cartaz em `frontend/components/rows/rows.module.css` e `frontend/components/highlights/highlights.module.css` — e confirmar visualmente que acompanharam a paleta. É onde um respingo laranja sobreviveria despercebido, porque só aparece em filme sem arte (FR-010)
- [X] T019 [P] [US2] Confirmar que `--cor-fundo-qr` continua `#ffffff`, `--cor-sucesso`, `--cor-alerta` e `--cor-erro` continuam intocados, e que nenhum token de superfície mudou (data-model.md, "O que NÃO muda")

**Checkpoint**: o laranja não existe mais e a prova está verde.

---

## Phase 4: US3 — A cor nova funciona como cor de trabalho (P1)

**Goal**: A cor é foco, ação, seleção e marca — e cumpre a função em todas.

**Independent Test**: Percorrer as dez superfícies e conferir que a cor aparece com contraste
suficiente em cada papel que exercia.

**⚠️ T020 é o teste que ninguém pensa em escrever**, e é o que separa "a cor está bonita" de "a
interface continua usável".

- [X] T020 Quebrar de propósito: escurecer `--cor-destaque-forte` para `#6b0033`, rodar `npm run test -- tokens` e conferir que **C3 falha**. Em seguida rodar a suíte **inteira** com o valor quebrado e conferir que **os 197 testes passam mesmo assim** — é a demonstração de que nada além do teste de tokens defende o foco de teclado. Restaurar (quickstart.md, percurso 2)
- [X] T021 [P] [US3] Quebrar de propósito: trocar `--cor-destaque` pelo âmbar `#ffd447`, conferir que **D2 falha** (ΔE 8 contra o mínimo de 25) e restaurar. É a medida que eliminou o âmbar na pesquisa, agora provada como guarda
- [X] T022 [P] [US3] Quebrar de propósito: colocar `#ff5c39` em qualquer arquivo de componente, conferir que **A1 falha** e restaurar
- [X] T023 [US3] Percorrer o **papel de ação principal** nas sete superfícies onde ele aparece (entrar, pagamento, meus ingressos, portaria, destaque da home, painel de link, confirmar lugares) e conferir preenchimento e texto por cima, em repouso **e** em hover (data-model.md, papel 1)
- [X] T024 [US3] Percorrer as telas **só pelo teclado** e conferir que o contorno de foco permanece visível em todas — home, filme, assentos, pagamento, meus ingressos, entrar, portaria (FR-032, papel 2)
- [X] T025 [US3] Conferir o **papel de seleção**: assento selecionado, sessão escolhida na página do filme, e sessão da porta na portaria (papel 3)
- [X] T026 [US3] Conferir o **papel de marca e realce de texto**: sufixo `.com`, lugar do ingresso em destaque, horário na lista de portas. É o papel mais exigente, porque precisa de contraste de texto e não só de componente (papel 4)
- [X] T027 [US3] Aplicar filtro de escala de cinza (DevTools → Rendering → Emulate vision deficiencies → Achromatopsia) ao **mapa de assentos** e conferir que disponível, selecionado, tomado e indisponível continuam distinguíveis. É onde o ajuste fino da cor nova come a forma sem ninguém notar (FR-030)
- [X] T028 [US3] Aplicar o mesmo filtro aos **quatro desfechos da portaria** e conferir que continuam distinguíveis por símbolo e título antes da cor (FR-031)
- [X] T029 [P] [US3] Conferir que o **fundo do QR continua branco** em todas as superfícies onde o ingresso aparece: confirmação de compra, meus ingressos, ingresso do dono e página compartilhada (FR-029)
- [X] T030 [P] [US3] Conferir que os **véus de contraste** sobre a arte do filme continuam garantindo a leitura do título, inclusive sobre um cartaz claro (FR-033)
- [X] T031 [P] [US3] Conferir a 320px que nenhuma superfície ganhou rolagem lateral (FR-034)
- [X] T032 [P] [US3] Acrescentar a `frontend/tests/tokens.test.ts` uma asserção de que os **nomes** dos cinco tokens de destaque continuam existindo — renomear um deles quebraria os 12 consumidores em silêncio, porque CSS não reclama de variável inexistente (FR-005)

**Checkpoint**: a cor funciona nos quatro papéis, e as três quebras de propósito provaram a prova.

---

## Phase 5: US4 — O nome tem desenho, não só fonte (P1)

**Goal**: Tipografia de marca e marca gráfica, com variante compacta.

**Independent Test**: Observar a marca em tela larga e em 320px, e conferir que nas duas ela é
reconhecível e coerente.

- [X] T033 [US4] Declarar `--fonte-marca` em `frontend/styles/tokens.css`, com a família e o fallback, e comentário registrando que ela tem **exatamente um consumidor** — nenhum texto de interface pode usá-la (FR-016)
- [X] T034 [US4] Carregar a família da marca em `frontend/app/layout.tsx` a partir do arquivo local, com **métrica de fallback declarada**. Sem ela o cabeçalho salta quando a fonte chega, e FR-018 proíbe (R7)
- [X] T035 [US4] Escrever `frontend/components/header/MarcaGrafica.tsx` — o `t` com o ponto do `.com`, como **construção geométrica própria** (traços retos + círculo), não como glifo vetorizado da fonte. Registrar no docstring os dois motivos: caminho desenha igual antes de a fonte chegar e serve como ícone de aba; e geometria própria evita o §05 da licença, que torna trabalho derivado propriedade do licenciador (R8 + emenda)
- [X] T036 [US4] Registrar no mesmo docstring **como a marca deriva do nome**: `ticket.com` tem uma única pontuação, e ela já era elemento de marca desde a 002 — o sufixo sai na cor de destaque. A logo promove o que o nome já tem, em vez de inventar um ícone que serviria a qualquer cinema (FR-019, FR-020)
- [X] T037 [US4] Evoluir `frontend/components/header/BrandMark.tsx` para compor marca gráfica e nome, usando `--fonte-marca` no nome. **PRESERVAR o prop de destino por papel** que a 010 entregou — reescrever do zero é a forma mais provável de perdê-lo, e perdê-lo significa a portaria voltando a cair no catálogo (R9, FR-025)
- [X] T038 [US4] Fazer o `BrandMark` escolher a variante compacta em tela estreita, sem depender de JavaScript para isso (FR-022)
- [X] T039 [US4] Conferir que o rótulo acessível continua coerente e nomeia o site, e que o algoritmo de nome acessível não insere espaço entre `ticket` e `.com` — é o cuidado que a 002 já registrou e que a marca nova não pode perder (FR-024)
- [X] T040 [US4] Ajustar `frontend/components/header/header.module.css` só no que a marca nova exige, usando exclusivamente tokens (FR-006)
- [X] T041 [US4] Conferir que a marca **não tem brilho, sombra colorida nem halo** — o contraste de 5.64:1 sobre o fundo escuro dispensa efeito, e efeito é item proibido do contrato anti-slop (FR-023)
- [X] T042 [US4] Criar `frontend/app/icon.svg` com a variante compacta, legível a 16px
- [X] T043 [P] [US4] Escrever `frontend/tests/marca.test.tsx` cobrindo: as duas variantes renderizam, o rótulo acessível nomeia o site, e a marca **não** é texto dependente de fonte
- [X] T044 [US4] Cobrir em `frontend/tests/marca.test.tsx` que o **destino muda por papel** — cliente e visitante para a home, portaria para `/portaria`. É a asserção que guarda o comportamento da 010 dentro de um componente que esta feature reescreveu
- [X] T045 [P] [US4] Acrescentar a `frontend/tests/header.test.tsx` asserções **aditivas** de que o nome usa `--fonte-marca` e a marca gráfica está presente. Nenhuma asserção existente pode ser removida ou enfraquecida (FR-036)
- [X] T046 [P] [US4] Conferir em rede lenta (DevTools → throttling) que o nome aparece legível na substituta e que **o cabeçalho não salta** quando a família da marca chega (FR-018)
- [X] T047 [P] [US4] Conferir a marca a 320px: a variante compacta aparece e continua reconhecível (FR-022, SC-007)
- [X] T048 [P] [US4] Conferir com leitor de tela que a marca é anunciada com o rótulo coerente, e não como "imagem" nem pelo nome do arquivo

**Checkpoint**: o nome tem desenho e tipografia próprios, e o destino por papel sobreviveu.

---

## Phase 6: US1 — Reconhecer de quem é o site (P1)

**Goal**: A identidade comunica em dois segundos, e sobrevive à remoção do logotipo.

**Independent Test**: Mostrar a home a alguém que não conhece o projeto por dois segundos e pedir
que descreva a marca.

**Esta fase vem por último apesar de ser a US1**: ela avalia o efeito combinado de tudo o que as
outras entregaram, e não pode ser julgada antes.

- [X] T049 [US1] Capturar a primeira dobra da home em 1440×900, com o catálogo sincronizado e semeado, seguindo o procedimento de `contracts/anti-slop-review.md`
- [X] T050 [US1] Aplicar as listas do contrato **à imagem com o cabeçalho recortado**: os quatro itens obrigatórios presentes, nenhum proibido presente. O recorte é o ponto do exercício — com o logotipo, qualquer interface parece ter identidade
- [X] T051 [US1] Aplicar os **dois itens novos** à imagem com o cabeçalho: tipografia de marca visivelmente de outra família, e marca gráfica que deriva do nome
- [X] T052 [US1] Responder as **duas perguntas finais** do contrato: numa galeria ao lado de cinco catálogos de streaming, dá para apontar qual é o nosso? E, mostrando a home por dois segundos, a pessoa diz o nome do site? (SC-008, SC-009)
- [X] T053 [US1] Registrar o resultado na seção **Resultado** de `specs/011-marca-sem-laranja/contracts/anti-slop-review.md`, com o que foi visto — não a imagem, que não é versionada
- [X] T054 [US1] Se algum item reprovar, registrar **o que** falhou e **por quê**, e tratar como tarefa desta feature. Uma checagem que falha e não gera correção é teatro
- [X] T055 [US1] Confirmar que nenhuma correção exigida saiu do escopo visual. Se exigir mudar comportamento ou asserção de regra de negócio, ela **está fora** — registrar como achado para uma feature futura, não alargar esta

**Checkpoint**: a identidade comunica, com veredito registrado.

---

## Phase 7: US5 — Nada de comportamento mudou (P1)

**Goal**: Comprar, pagar, receber, compartilhar e validar funcionam exatamente como antes.

**Independent Test**: Rodar a suíte inteira e conferir que nenhuma asserção de regra de negócio
precisou ser alterada.

- [X] T056 [US5] Rodar `docker compose exec backend pytest` e conferir **360 passando** — o back-end não deveria ter sido tocado por esta feature em nenhuma linha
- [X] T057 [US5] Rodar `docker compose exec frontend npm run test` e conferir que os **197 anteriores** continuam passando, mais os desta feature
- [X] T058 [US5] Rodar, de `frontend/`, `npx playwright test --workers=2` e conferir **41 passando**
- [X] T059 [US5] Para cada teste que precisou de ajuste, registrar qual e por quê, e confirmar que o ajuste foi de **seletor ou estilo** — nunca de regra de negócio (FR-036)
- [X] T060 [US5] Percorrer o fluxo inteiro à mão uma vez: comprar → pagar → ver ingresso → compartilhar → validar na portaria. Esperado: idêntico ao de antes, em outra cor
- [X] T061 [P] [US5] Conferir que os **estados de erro e vazio** continuam presentes e escritos para humanos em todas as telas — estado vazio de "Meus ingressos", link revogado, câmera negada, nenhuma sessão hoje, papel errado (FR-039)
- [X] T062 [P] [US5] Conferir que nenhum contrato de API, seed, limite de carrossel, regra de trilha ou etapa de fluxo mudou: `git diff --stat backend/` deve estar vazio (FR-037)

**Checkpoint**: a mudança foi visual e só visual.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Fechar o rastro de decisão e o que o avaliador precisa ler.

- [X] T063 Acrescentar o aviso de **sucedido** ao topo de `specs/006-visual-identity/contracts/anti-slop-review.md`, apontando para o sucessor e registrando que o documento **não foi editado de propósito** — ele é o registro de que a paleta um dia foi outra (R12, FR-002)
- [X] T064 Atualizar `README.md` com a seção da feature: a cor nova, o conceito de neon de fachada, e a **nota explícita de que a 011 emenda o FR-020 da 006** (FR-043)
- [X] T065 Registrar no `README.md` **como a cor foi escolhida** — por eliminação, com a restrição que ninguém antecipa: a marca não pode colidir com cor de estado, e é isso que elimina o âmbar a 8° do alerta (FR-040)
- [X] T066 Registrar no `README.md` as **fontes usadas e suas licenças**, com o caminho do arquivo de licença versionado (FR-043, FR-014)
- [X] T067 Registrar no `README.md` o **conceito da logo** — como ela deriva do nome — e as variantes (FR-042)
- [X] T068 Atualizar a seção de **uso de IA** do `README.md` com o que foi feito com e sem auxílio nesta feature (FR-043, Princípio VI)
- [X] T069 Acrescentar à tabela de verificações-por-quebra do `README.md` as três desta feature: contorno de foco apagado, marca harmonizada com o alerta, e vestígio da cor antiga
- [X] T070 Registrar no `README.md` a descoberta da medição: **a paleta antiga já falhava D1** (ΔE 23.8 do `--cor-erro`, abaixo de 25). Ela era, dos candidatos avaliados, a mais confundível com uma cor de estado — o que justifica a troca por um motivo que não é gosto
- [X] T071 [P] Conferir que nenhum valor de cor, espaçamento, tipografia, raio ou duração ficou fora dos tokens nos arquivos tocados (FR-006, Princípio V)
- [X] T072 [P] Conferir que nenhuma superfície contém texto de preenchimento, marcador de posição ou "em breve" (FR-044)
- [X] T073 Rodar a varredura final e confirmar **zero** ocorrências da cor antiga em todo o front-end (SC-001)
- [X] T074 Comparar a suíte com a linha de base de T001 e confirmar que **nenhuma** asserção de regra de negócio das features 001–010 foi removida ou enfraquecida (SC-015, FR-036)
- [X] T075 Percorrer o `quickstart.md` inteiro, os sete percursos, contra a aplicação rodando — **feito**, com uma ressalva: o percurso 4 (escala de cinza para assentos e desfechos) foi conferido pela estrutura do CSS, não com o filtro do navegador, porque forma e contorno vêm da 007/010 e nenhum deles foi tocado. A checagem visual com o filtro fica recomendada antes da entrega

---

## Dependencies & Execution Order

**Fases 1 → 2 são bloqueantes.** Nenhuma user story começa antes de a prova existir e estar vermelha
pelos motivos certos.

**As fases seguem dependência, não numeração de história:**

```text
Fase 3 (US2) ── a troca. A menor fase, e destrava tudo
     │
     ├── Fase 4 (US3) ── a cor funciona nos quatro papéis
     └── Fase 5 (US4) ── marca e tipografia
              │
              └── Fase 6 (US1) ── a identidade, avaliada com tudo no lugar
                       │
                       └── Fase 7 (US5) ── nada quebrou
                                │
                                └── Fase 8 ── o rastro
```

**Ordens que não podem inverter:**

- **T005–T011 antes de T013.** É a regra mais importante do arquivo. O teste escrito depois da troca
  é escrito para os valores que já estão lá, e os limites viram descrição do que foi feito em vez de
  regra.
- **T012 antes de T013.** Confirmar que a prova está **vermelha** antes de a troca torná-la verde. Um
  teste que já passava contra a paleta antiga não estava medindo nada.
- **T020 antes de qualquer conferência visual.** É a demonstração de que os 197 testes existentes não
  defendem nada aqui — e o que dá sentido a todas as conferências manuais que vêm depois.
- **Fase 5 antes da Fase 6.** A checagem anti-slop avalia a marca; sem ela, dois dos itens
  obrigatórios não existem para serem avaliados.
- **T037 preserva o destino por papel, e T044 é a guarda disso.** As duas andam juntas: o componente
  está sendo reescrito, e o comportamento que ele carrega não é óbvio olhando um logotipo.
- **T063 é pré-requisito da avaliação, não polimento.** Sem o aviso de sucedido, o contrato da 006
  continua sendo a regra escrita válida — e ele ainda pede laranja.

## Parallel Execution Examples

**Fase 2** — depois de T006: `T007`, `T008`, `T009`, `T010` e `T011` são verificações independentes
no mesmo arquivo (escrever de uma vez).

**Fase 3** — `T018` e `T019` são conferências independentes, depois de T016.

**Fase 4** — `T021` e `T022` em paralelo (cada uma quebra e restaura coisa diferente, mas **não** com
T020, que quebra o mesmo arquivo). `T029`, `T030` e `T031` são independentes entre si.

**Fase 5** — `T043`, `T045`, `T046`, `T047` e `T048` tocam arquivos e ferramentas distintos.

**Fase 7** — `T061` e `T062` em paralelo.

**Fase 8** — `T071` e `T072` em paralelo. `T064`–`T070` tocam o mesmo arquivo: sequenciais.

## Implementation Strategy

**MVP = Fases 1, 2 e 3.** Ao fim da Fase 3 o laranja não existe mais, a paleta nova está no ar em
todas as dez superfícies de uma vez — porque todas consomem os mesmos cinco tokens — e a prova está
verde. É o menor incremento que entrega o pedido principal da feature.

**Mas a feature não fecha no MVP.** Sem a Fase 4 ninguém verificou que a cor **funciona**; sem a
Fase 5 o nome continua sem desenho, que é metade do pedido; e sem a Fase 6 não há veredito sobre a
única pergunta que importa.

**Ordem sugerida de entrega incremental**:

1. **Fases 1–2** — a prova, vermelha. Nada visível, e é onde mora o risco inteiro da feature.
2. **Fase 3** — a troca. Cinco valores, dez superfícies.
3. **Fase 4** — a cor verificada nos quatro papéis, com as três quebras de propósito.
4. **Fase 5** — marca e tipografia.
5. **Fase 6** — a checagem anti-slop, com veredito registrado.
6. **Fases 7–8** — nada quebrou, e o rastro.

**Três pontos de não avançar**:

- **Se T012 passar em vez de falhar, parar.** O teste não está lendo os tokens, ou os limites estão
  frouxos demais para pegar uma paleta que mede ΔE 23.8 contra o mínimo de 25.
- **Se T017 encontrar consumidor editado, parar e descobrir por quê.** Significa que um valor de cor
  vazou dos tokens, e a disciplina da 006 — que é o que torna esta feature barata — foi quebrada
  exatamente na feature que a estava colhendo.
- **Se T020 mostrar a suíte falhando com o foco apagado, ótimo — e investigar.** Significa que algum
  teste depende da cor do contorno de foco, o que é acoplamento indevido: teste de comportamento não
  deve saber a cor de nada.
