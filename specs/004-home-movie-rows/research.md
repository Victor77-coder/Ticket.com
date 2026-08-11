# Phase 0 — Research: Trilhas de Filmes na Home

**Feature**: `004-home-movie-rows` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado. Nenhum `NEEDS CLARIFICATION`
permanece aberto ao fim desta fase.

---

## R1. Como a trilha rola — e por que a resposta é diferente da do carrossel

**Decision**: contêiner com `overflow-x: auto` e `scroll-snap-type: x mandatory`, cada cartão com
`scroll-snap-align: start`. Os controles de seta chamam `scrollBy()`. **Nada de índice em estado
React, nada de `translateX`.**

**Rationale**: a feature 001 descartou `scroll-snap` no carrossel por dois motivos concretos — a
navegação circular (FR-008 de lá) exigiria clonar slides, e a rotação automática precisava de
controle programático fino. **Nenhum dos dois existe aqui.** A trilha não fecha ciclo e não roda
sozinha.

Removidos esses requisitos, o CSS nativo entrega de graça o que o carrossel teve de escrever à
mão:

- gesto de toque com inércia, que no carrossel custou ~40 linhas de pointer events
- rolagem por roda e trackpad
- rolagem por teclado quando o foco entra na trilha
- `scroll-behavior: smooth` desligável por `prefers-reduced-motion`

Insistir no padrão do carrossel aqui seria coerência aparente pagando em código e em
acessibilidade pior.

**Alternatives considered**:

- **Reusar `HighlightsCarousel`** — o componente é um-de-cada-vez com rotação; a trilha é
  muitos-ao-mesmo-tempo sem rotação. Generalizar os dois num componente só produziria um
  emaranhado de condicionais.
- **Biblioteca de carrossel** — descartada pelo mesmo motivo da feature 001 (Princípio V), e aqui
  ainda mais desnecessária, já que o CSS resolve.

**Armadilha registrada**: `overflow-x` só contém o transbordo se o contêiner pai tiver
`min-width: 0` dentro de grid ou flex. Sem isso o conteúdo empurra a largura e a **página** passa
a rolar horizontalmente, quebrando SC-005. É o erro clássico desse padrão e precisa de teste.

---

## R2. Onde a classificação de catálogo é guardada

**Decision**: dois campos booleanos em `Movie` — `is_trending` e `is_upcoming` — mais
`catalog_synced_at`. Sem tabela de coleção, sem modelo `Collection`.

**Rationale**: a cardinalidade é fixa em três trilhas, e nenhuma delas tem atributo próprio a
guardar (sem ordem manual, sem curadoria, sem data de início e fim). Uma tabela de associação
adicionaria um join e uma migração para representar exatamente a mesma informação que dois
booleanos.

A trilha **Em cartaz** não ganha campo algum: ela é derivada das sessões, não do TMDb.

**Alternatives considered**:

- **Modelo `Collection` + `CollectionMovie`** — a escolha certa se as trilhas fossem curadas por
  um organizador, com ordem manual. Não é o caso: as três são automáticas. Quando existir curadoria
  a migração é direta.
- **Campo texto com a categoria** — impediria um filme de estar em alta **e** em breve ao mesmo
  tempo, que é comum e que o FR-005 exige suportar.

---

## R3. Como a classificação expira

**Decision**:

- **`is_trending`**: zerado em **todos** os filmes no início de cada sincronização e remarcado
  apenas nos que voltarem na lista. Um filme deixa de estar em alta quando o TMDb para de
  listá-lo.
- **`is_upcoming`**: gravado pela sincronização, mas a consulta da trilha exige **também**
  `release_date > hoje`. A data manda; a marca só ajuda a filtrar.

**Rationale**: "em alta" é um estado do mundo, não um atributo do filme — sem a limpeza, o
primeiro sync marcaria filmes que ficariam em alta para sempre.

"Em breve" é diferente: tem uma verdade verificável localmente (a data de estreia). Confiar só na
marca faria um filme já estreado continuar na trilha Em breve até a próxima sincronização, o que
é visivelmente errado para quem já viu o filme em cartaz. Confiar só na data traria todo filme
futuro do catálogo, incluindo os que o TMDb não considera lançamento próximo. Exigir as duas
condições é o que dá o resultado certo.

**Consequência assumida**: entre sincronizações a trilha Em alta envelhece. É aceitável e
reconhecível — `catalog_synced_at` registra quando foi atualizada.

---

## R4. Quantas requisições a home faz

**Decision**: uma só — `GET /api/v1/home/` devolve as três trilhas em um objeto.

**Rationale**: a home precisa das três juntas para renderizar. Três endpoints separados
multiplicariam a latência por três sem nenhum ganho, já que nenhuma trilha é opcional nem
carregada sob demanda.

O endpoint de highlights (feature 001) **permanece separado e intocado**. Fundi-lo aqui quebraria
o contrato de uma feature entregue para economizar uma requisição que já é rápida.

**Alternatives considered**:

- **Três endpoints, um por trilha** — permitiria carregar independentemente, o que só importaria
  se as trilhas fossem lazy. Não são: as três aparecem na primeira dobra ou logo abaixo.
- **Incluir as trilhas no endpoint de highlights** — misturaria duas features e obrigaria a
  revisar o contrato e os testes da 001 sem necessidade.

---

## R5. Como "Em cartaz" é montada

**Decision**: reusar `get_highlighted_movies` da feature 001, extraindo a regra para um seletor
sem limite. O carrossel continua pedindo 5; a trilha pede todos.

**Rationale**: SC-003 exige que 100% dos filmes da trilha conduzam a uma sessão comprável — que é
literalmente a regra de elegibilidade já implementada e testada. Duplicá-la criaria dois lugares
para manter em sincronia, e a divergência apareceria como promessa quebrada na trilha.

**Consequência assumida**: os 5 filmes do carrossel aparecem também na trilha. É intencional
(FR-005) e comum em vitrines de streaming e de ingressos.

---

## R6. O que o `sync_tmdb` passa a fazer

**Decision**: importar três listas em vez de uma:

| Trilha | Endpoint | Parâmetros |
|---|---|---|
| Em cartaz (catálogo) | `/movie/now_playing` | `region=BR` |
| Em alta | `/trending/movie/week` | — |
| Em breve | `/movie/upcoming` | `region=BR` |

Os filmes são desduplicados por `tmdb_id` antes do detalhamento, e a marcação é aplicada depois.
O `--limit` passa a valer por lista.

**Rationale**: verificado na documentação do TMDb antes da redação do spec. `/trending/movie/{time_window}`
aceita `day` ou `week`; escolhida **week**, porque a diária oscila demais para uma vitrine que só
é sincronizada manualmente. `/movie/upcoming` aceita `region` e devolve a janela de datas que
considerou.

A desduplicação importa: um filme costuma aparecer em duas listas, e detalhar duas vezes gastaria
o dobro de requisições ao TMDb sem ganho.

**Consequência assumida**: o comando passa a fazer 3 requisições de listagem mais uma por filme
único. Com `--limit 20` por lista, o pior caso é ~60 filmes — aceitável para um comando manual.

---

## R7. Quando os controles de seta aparecem

**Decision**: renderizados apenas quando o conteúdo transborda, detectado comparando
`scrollWidth` com `clientWidth` via `ResizeObserver`. Também desabilitados nas extremidades.

**Rationale**: FR-014. Uma seta permanentemente desabilitada é ruído visual que sugere conteúdo
inexistente. O `ResizeObserver` é necessário porque o transbordo muda quando a janela é
redimensionada — checar só na montagem daria resposta errada depois do primeiro `resize`.

---

## R8. A página do filme sem sessão

**Decision**: a página já existe e já trata a lista vazia. Ganha duas coisas: a **data de
estreia**, quando conhecida, e a mensagem ajustada.

O texto segue o que o usuário especificou, menos a parte descartada:

> **Estreia em 13/08/2026**
> No momento, este filme não possui sessões programadas.

Sem data conhecida, só a segunda linha. Com data no passado e sem sessão, também só a segunda —
anunciar "estreia em" uma data já vencida seria informação errada.

**Rationale**: FR-024 a FR-027. O "Lembre-me" foi descartado pelo usuário porque o sistema
registraria o interesse sem entregar aviso algum.

---

## R9. O critério do seed

**Decision**: `seed_demo` passa a preferir filmes que o TMDb classifica como **em cartaz**, com
arte e duração acima de 60 minutos, antes de cair para o critério atual de data de lançamento.

**Rationale**: com catálogo real, o critério atual (`-release_date`) trouxe para o carrossel um
show de banda e um curta de 9 minutos. A vitrine de um cinema com esses títulos em destaque não é
falha funcional, mas é exatamente o tipo de coisa que o Princípio V cobra — a interface precisa
demonstrar escolha, e o avaliador vê a home antes de ler qualquer código.

A trilha Em cartaz herda os mesmos filmes do seed, então o problema apareceria duas vezes.

**Registrado em Complexity Tracking**: altera arquivo da feature 001.

---

## R10. Estratégia de testes

| Alvo | Tipo | Por quê |
|---|---|---|
| Composição das três trilhas, limite de 9 em Em alta | back-end | FR-002 a FR-004, SC-002 |
| Trilha vazia é omitida da resposta | back-end | FR-006, SC-008 |
| Em cartaz só traz filme com sessão comprável | back-end | SC-003 — a promessa da trilha |
| `is_trending` é zerado antes de remarcar | back-end | R3 — sem isso a trilha nunca esvazia |
| `is_upcoming` exige data futura | back-end | R3 — filme já estreado sairia da trilha |
| Resposta pública sem dado de gestão | back-end | Gate do Princípio IV |
| Cartão sem cartaz mostra substituto legível | front-end | FR-011 |
| Setas só com transbordo | front-end | FR-014 |
| Todos os cartões alcançáveis por teclado | front-end | FR-017, SC-006 |
| Página não rola horizontalmente | e2e | SC-005 — a armadilha de R1 |
| Percurso trilha → página do filme | e2e | Princípio I |

**Rationale**: concentra no que R1 identificou como armadilha, no que R3 identificou como sutil, e
no gate que a constitution obriga. Nada de teste por cobertura.
