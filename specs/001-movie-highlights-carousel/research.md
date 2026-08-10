# Phase 0 — Research: Carrossel de Highlights de Filmes

**Feature**: `001-movie-highlights-carousel` | **Date**: 2026-08-10

Cada item registra a decisão, o motivo e o que foi descartado. Nenhum `NEEDS CLARIFICATION`
permanece aberto ao fim desta fase.

---

## R1. Como construir o carrossel

**Decision**: Componente próprio. Track horizontal com todos os painéis lado a lado, deslocado
por `transform: translateX(-index * 100%)`. Índice em estado React, com aritmética modular para
a navegação circular.

**Rationale**:

- FR-008 exige navegação circular. Com índice modular isso é uma linha; com `scroll-snap` exige
  clonar o primeiro e o último slide e reposicionar o scroll no meio da transição — muito mais
  código e uma classe inteira de bugs de sincronia.
- FR-010 exige pausar a rotação em três condições distintas (ponteiro sobre a área, foco de
  teclado interno, trailer tocando). Bibliotecas de carrossel expõem `pause on hover`, quase
  nunca as outras duas.
- O Princípio V da constitution proíbe entregar a saída padrão de uma ferramenta. O carrossel é
  a superfície mais visível do projeto; envolvê-lo em uma lib genérica trabalha contra o próprio
  critério que está sendo avaliado.
- São 5 painéis. Não há virtualização a resolver.

**Alternatives considered**:

- **`scroll-snap` puro em CSS** — ganha gesto de toque e inércia nativos de graça, mas o
  fechamento do ciclo (FR-008) e o controle programático de "ir para o índice N" (FR-007) ficam
  desajeitados. Descartado pelo custo do ciclo.
- **Embla / Swiper / `keen-slider`** — resolvem gesto e loop, mas trazem estilo próprio a
  sobrescrever, e o controle fino de ARIA e de pausa teria de ser reconstruído por cima mesmo
  assim. Descartado por Princípio V e por peso desnecessário para 5 slides.

**Consequência assumida**: perdemos a inércia nativa do scroll de toque. Compensamos com
handlers de `pointerdown/move/up` e um limiar de arrasto de ~50 px para decidir a troca de
painel. É código explícito, ~40 linhas, e sob nosso controle.

**Detalhe do ciclo**: ao passar do último painel para o primeiro, o track não faz o rebobinar
longo de 5 painéis. A transição de wrap é uma troca curta (fade + deslocamento pequeno) em vez
de um deslize atravessando todos os painéis intermediários. É honesto e legível — a ilusão de
fita infinita não vale a complexidade aqui.

---

## R2. Como reproduzir o trailer "dentro do próprio highlight"

**Decision**: Ao acionar "Trailer", montar um `<iframe>` apontando para
`https://www.youtube-nocookie.com/embed/{key}?autoplay=1&rel=0&modestbranding=1` ocupando a área
da arte do painel ativo. Ao fechar, ao trocar de painel ou ao desmontar o carrossel, **remover o
iframe da árvore**.

**Rationale**:

- FR-012 pede reprodução dentro do painel, sem modal e sem sair da plataforma. Um iframe
  posicionado sobre a área da arte, dentro do mesmo contêiner do painel, é literalmente isso.
- FR-014 e FR-016 (parar ao navegar; no máximo um trailer por vez) saem de graça: desmontar o
  iframe encerra a reprodução de forma garantida, sem depender de `postMessage`, sem carregar
  `iframe_api.js` e sem sincronizar estado com um player de terceiro.
- FR-017 proíbe autoplay na abertura. Como o iframe só passa a existir após o clique, não há
  nem requisição ao YouTube antes da ação do usuário — o que também ajuda SC-002.
- `youtube-nocookie.com` evita cookies de rastreamento antes de qualquer interação.

**Alternatives considered**:

- **YouTube IFrame Player API (`enablejsapi=1` + `player.stopVideo()`)** — permite controlar sem
  desmontar e dá eventos de estado. Custa um script de terceiro carregado na página e uma
  máquina de estados a manter sincronizada. Descartado: não precisamos de nenhum evento que a
  montagem/desmontagem não resolva.
- **Baixar e servir o arquivo de vídeo** — o TMDb fornece apenas a chave do YouTube, não o
  arquivo. Inviável.
- **Abrir em modal** — explicitamente contrariado pelo pedido do usuário e por FR-012.

**Consequência assumida**: um `autoplay=1` só é honrado pelo navegador porque decorre de um
gesto direto do usuário. Como o iframe nasce do clique, a condição está satisfeita e o áudio
pode iniciar ligado (FR-017, segunda metade).

---

## R3. De onde vem a classificação indicativa brasileira

**Decision**: `GET /3/movie/{movie_id}/release_dates`, filtrar o item com
`iso_3166_1 == "BR"`, e dentro dele preferir a entrada com `type == 3` (Theatrical), caindo para
a primeira entrada com `certification` não vazia.

**Rationale**: verificado na documentação do TMDb. A resposta é
`{ id, results: [ { iso_3166_1, release_dates: [ { certification, type, release_date, note,
iso_639_1, descriptors } ] } ] }`, e os tipos são: 1 Premiere, 2 Theatrical (limited),
3 Theatrical, 4 Digital, 5 Physical, 6 TV. O endpoint `/movie/{id}` principal **não** traz
classificação por país, então este endpoint extra é necessário.

**Fallback**: quando não houver entrada `BR` ou a certificação vier vazia, gravar `null` e o
painel omite o selo de classificação — sem exibir "N/A" nem caixa vazia (Princípio V).

---

## R4. De onde vem o trailer

**Decision**: `GET /3/movie/{movie_id}/videos`, e escolher o vídeo por esta ordem de preferência:

1. `site == "YouTube"` **e** `type == "Trailer"` **e** `official == true` **e**
   `iso_639_1 == "pt"`
2. o mesmo, com `iso_639_1 == "en"`
3. qualquer `site == "YouTube"` com `type == "Trailer"`
4. qualquer `site == "YouTube"` com `type == "Teaser"`
5. nenhum → o filme fica sem trailer e o botão não é renderizado (FR-015)

**Rationale**: confirmado na documentação — cada item de `results` traz `iso_639_1`,
`iso_3166_1`, `name`, `key`, `site`, `size`, `type`, `official`, `published_at`, `id`. Filtrar
por `site == "YouTube"` é obrigatório porque o TMDb também retorna Vimeo, que o nosso player
embutido não trata. A degradação para Teaser evita perder o botão em lançamentos recentes que
ainda não têm trailer completo.

**Otimização**: usar `append_to_response=videos,release_dates` na chamada de detalhe do filme
para resolver R3, R4 e os metadados em **uma** requisição por filme em vez de três.

---

## R5. Onde os dados são buscados no Next.js

**Decision**: a home (`app/page.tsx`) é um Server Component e busca
`GET http://backend:8000/api/v1/highlights/` no servidor durante a renderização. O carrossel
(`HighlightsCarousel.tsx`) é um Client Component que recebe os dados já prontos por props.

**Rationale**:

- SC-002 exige o primeiro painel legível em ≤ 2 s. Renderizar no servidor entrega HTML com o
  conteúdo já dentro — sem o ciclo de esqueleto → fetch → repintura.
- Princípio VII: mantém a superfície de rede no servidor. O navegador nunca fala com o Django
  diretamente nesta feature, e nada de configuração de back-end vaza para o bundle.
- A fronteira fica limpa: o componente cliente só carrega o que precisa de interatividade
  (índice, rotação, gesto, trailer).

**Alternatives considered**:

- **Fetch no cliente com `useEffect`** — obriga o estado de esqueleto no primeiro paint em toda
  visita e coloca em risco SC-002. Descartado.
- **Renderização estática com revalidação** — atraente, mas a elegibilidade depende de "sessão
  futura", que muda com o relógio. Ficaria com destaque obsoleto apontando para sessão já
  ocorrida, quebrando SC-004. Decisão: renderização dinâmica com cache curto no Django (R7).

---

## R6. Regra de elegibilidade ao destaque

**Decision**: um filme é elegível quando possui **ao menos uma sessão publicada com
`starts_at > agora`**. A ordenação é pela sessão elegível mais próxima, ascendente. O limite é 5.
Desempate por título, para que a ordem seja determinística e testável.

**Rationale**: é a leitura de FR-002 que sustenta SC-004 — todo destaque leva a algo comprável.
Ordenar pelo que estreia primeiro dá ao carrossel um significado editorial ("o que está
passando agora") em vez de uma lista arbitrária. O desempate explícito evita teste instável.

**Casos de borda cobertos** (todos já no spec): menos de 5 elegíveis exibe quantos houver; zero
elegíveis cai no estado vazio de FR-022; mais de 5 corta em 5.

---

## R7. Resiliência à queda do TMDb

**Decision**: o TMDb é acessado **apenas** por `sync_tmdb`, um comando de gerência executado sob
demanda. O caminho de leitura da home nunca chama o TMDb. O cliente HTTP usa timeout explícito
de 10 s de conexão/leitura e trata erro devolvendo mensagem acionável ao operador do comando.

**Rationale**: é o Princípio VII escrito em código. Com a arte, a sinopse, a duração, o gênero,
a classificação e a **chave do trailer** persistidos localmente, uma queda do TMDb não afeta o
carrossel. O trailer ainda depende do YouTube no navegador — e é exatamente essa a única
degradação prevista em SC-006, coberta pelo cenário 6 da US2.

**Cache**: a resposta de `/api/v1/highlights/` recebe cache de 60 s no Django. Curto o bastante
para não segurar um destaque cuja sessão acabou de passar, longo o bastante para absorver
recarregamentos durante a avaliação.

---

## R8. Portas e configuração de ambiente

**Decision**:

| Serviço | Porta no host | Observação |
|---|---|---|
| PostgreSQL | **5438** | mapeado de 5432 no contêiner; evita colidir com um Postgres local em 5432 |
| Interface web (Next.js) | **5000** | `next dev -p 5000` — é o endereço que o avaliador abre |
| API (Django) | 8000 | não foi especificada pelo usuário; padrão do Django mantido |

**Rationale**: 5438 e 5000 foram determinadas pelo usuário. A porta do Django não foi
mencionada; manter 8000 evita inventar convenção. `CORS_ALLOWED_ORIGINS` inclui
`http://localhost:5000`, embora o fetch principal seja server-side (R5) e não passe por CORS —
a liberação existe para chamadas de cliente em features futuras.

**Nota sobre uma inferência**: "a porta do localhost deve ser 5000" foi lida como a interface
web. Se a intenção era o Django em 5000, a troca é de duas linhas (`docker-compose.yml` e
`.env.example`) e não afeta nenhuma decisão deste documento.

---

## R9. Acessibilidade do carrossel

**Decision**: seguir o padrão de carrossel do WAI-ARIA Authoring Practices:

- Contêiner: `role="region"`, `aria-roledescription="carousel"`, `aria-label="Filmes em cartaz"`.
- Cada painel: `role="group"`, `aria-roledescription="slide"`,
  `aria-label="{n} de {total}: {título}"`.
- Painéis fora de vista recebem `inert` — impede que o Tab caia em botão invisível.
- Região viva: `aria-live="off"` enquanto a rotação é automática, alternando para
  `aria-live="polite"` quando a troca partiu do usuário. Anunciar cada troca automática
  inundaria o leitor de tela.
- Indicadores de posição são `<button>` reais com `aria-current` no ativo, não `<div>` clicável.
- `prefers-reduced-motion: reduce` desliga rotação automática e transições (FR-011); a checagem
  é feita por `matchMedia` no JS, não só por CSS, porque a rotação é lógica e não estilo.

**Rationale**: FR-025 a FR-027 e SC-005 são requisitos duros. O `aria-live="off"` durante
autoplay é a parte contraintuitiva do padrão e a que costuma ser feita errado — registrada aqui
para não se perder na implementação.

---

## R10. Estratégia de testes

**Decision**: testes concentrados onde a constitution exige prova e onde a regra é sutil.

| Alvo | Tipo | Por quê |
|---|---|---|
| Endpoint público sem autenticação e sem campo de gestão | back-end | Gate do Princípio IV |
| Elegibilidade: ordenação, limite 5, exclusão de sessão passada/rascunho | back-end | Sustenta SC-004 e FR-002 |
| Mapeamento TMDb → modelos (classificação BR, escolha do trailer, ausência de trailer) | back-end | Concentra toda a lógica frágil de terceiro (R3, R4) |
| Navegação circular, pausa por hover/foco/trailer, movimento reduzido | componente | FR-008, FR-010, FR-011 — a lógica que a lib descartada teria escondido |
| Desmontagem do trailer ao trocar de painel | componente | FR-014 e FR-016 |
| Percurso home → trailer → "Ver ingressos" | e2e | Princípio I: o fluxo inteiro, não as partes |

**Rationale**: a constitution não obriga cobertura ampla, mas lista testes como diferencial
avaliado e **obriga** prova nos princípios não negociáveis. Nenhum deles (II e III) é tocado por
esta feature, então a obrigação aqui recai sobre o Princípio IV. O resto é escolha deliberada
sobre onde o erro é caro.
