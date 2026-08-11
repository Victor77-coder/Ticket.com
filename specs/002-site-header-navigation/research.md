# Research — Cabeçalho Global do Site

**Feature**: `002-site-header-navigation` | **Date**: 2026-08-11

Decisões técnicas tomadas antes de escrever código, com as alternativas que foram descartadas e o
motivo. Cada decisão é referenciada no `plan.md` pelo seu identificador (R1, R2, …).

---

## R1 — Como a busca-enquanto-digita atravessa a rede

**Decisão**: um **Route Handler do Next** em `app/api/busca/route.ts` recebe a chamada do
navegador e repassa server-side para o Django. O navegador conversa apenas com a própria origem
(`http://localhost:5003/api/busca?q=...`).

**Rationale**:

- A feature 001 fixou em `lib/api.ts` que "o navegador nunca fala com o Django direto", e nenhuma
  configuração de back-end chega ao bundle. Manter isso é mais barato que revisar a decisão.
- No Docker Compose o front-end recebe `API_BASE_URL=http://backend:8000`. Esse nome só existe
  dentro da rede do Compose — **o navegador não consegue resolvê-lo**. Uma chamada direta exigiria
  uma segunda variável pública com um endereço diferente (`localhost:8000`), duplicando a
  configuração e criando duas verdades sobre onde a API está.
- Mesma origem significa nenhum preflight de CORS no caminho quente da digitação.
- O proxy é o lugar natural para traduzir falha do Django em mensagem pt-BR (FR-018) sem vazar
  detalhe interno ao navegador.

**Alternativas consideradas**:

| Alternativa | Por que foi descartada |
|---|---|
| Navegador chamando `http://localhost:8000/api/v1/busca/` direto | `CORS_ALLOWED_ORIGINS` já permitiria, mas quebra dentro do Compose (o container do front resolve `backend`, o navegador não) e coloca a topologia do back-end no bundle. |
| Server Action do Next | Server Actions são `POST` e passam pelo pipeline de mutação/revalidação do Next. Busca é leitura idempotente; um Route Handler `GET` é mais simples de testar, cachear e chamar com `AbortController`. |
| Buscar tudo no servidor e filtrar no cliente | Com ~20 filmes funcionaria, mas embute o catálogo inteiro no HTML e deixa de funcionar assim que o catálogo crescer. Estaria otimizando para o seed, não para o sistema. |

---

## R2 — Correspondência insensível a acento e a caixa

**Decisão**: criar a extensão `unaccent` do PostgreSQL por migração e consultar com
`title__unaccent__icontains`, adicionando `django.contrib.postgres` a `INSTALLED_APPS` (é o que
registra o lookup `__unaccent` no Django).

**Rationale**:

- `icontains` sozinho já resolve caixa; o acento é o que exige `unaccent`. FR-008 pede os dois.
- A extensão é criada por migração versionada (`UnaccentExtension` de
  `django.contrib.postgres.operations`), então o ambiente de qualquer pessoa que rodar `migrate`
  fica igual — nada de passo manual esquecido no README.
- O usuário do PostgreSQL no `docker-compose.yml` é o dono do banco criado pela imagem oficial e
  tem permissão para `CREATE EXTENSION`.
- Uma única fonte de verdade: o título continua sendo o campo do TMDb, sem cópia normalizada para
  manter em sincronia.

**Alternativas consideradas**:

| Alternativa | Por que foi descartada |
|---|---|
| Coluna `title_normalizado` preenchida no `save()`/na sincronização | Não depende de extensão, mas cria um segundo ponto de verdade que precisa de backfill e que silenciosamente desalinha se alguém escrever no banco por fora. Troca uma dependência de banco por uma dívida de consistência. |
| `SearchVector`/`SearchQuery` (full-text do PostgreSQL) | Full-text trabalha por palavra e radical; não encontra `"matr"` dentro de `"Matrix"`. FR-008 exige correspondência **parcial**, que é justamente o que full-text não faz bem. |
| Filtrar em Python depois de carregar tudo | Com 20 filmes passa, com 2000 não. E move para a aplicação uma regra que o banco resolve. |

**Nota de escala registrada**: `unaccent(title) ILIKE '%termo%'` não usa índice btree. Com o
catálogo desta entrega (~20 filmes) a consulta é irrelevante para o SC-004. Se o catálogo crescer
uma ordem de grandeza, o caminho é um índice GIN de trigramas (`pg_trgm`) sobre a expressão —
registrado aqui para não ser redescoberto, **não** implementado agora, porque otimizar 20 linhas
seria complexidade sem problema correspondente.

---

## R3 — Garantir que a lista sempre corresponda ao termo atual (FR-015, SC-005)

**Decisão**: três mecanismos combinados no `SearchBox`:

1. **Debounce de 250 ms** após a última tecla antes de disparar a requisição.
2. **`AbortController`**: toda nova busca aborta a anterior ainda em voo.
3. **Guarda por número de sequência**: cada requisição carrega um número crescente; a resposta só
   é aplicada ao estado se for a de maior número já visto.

**Rationale**: o abort sozinho **não** é suficiente. Uma resposta pode já estar decodificada e a
caminho do `setState` quando o abort chega, e o `fetch` abortado nem sempre impede a continuação
de uma `Promise` já resolvida. A guarda por sequência é o que torna SC-005 uma afirmação
verdadeira em vez de provável — e é ela que o teste unitário mira, resolvendo as respostas
deliberadamente fora de ordem.

250 ms é a folga escolhida: curto o bastante para SC-004 (≤ 1 s após a pausa) sobrar tempo de
rede, longo o bastante para não disparar uma requisição por tecla.

**Alternativas consideradas**:

| Alternativa | Por que foi descartada |
|---|---|
| Só `AbortController` | Deixa a janela de corrida descrita acima. É o bug clássico de autocomplete: o resultado de "mat" aparecendo depois do de "matrix". |
| Buscar só ao apertar Enter | Elimina a corrida, mas contraria a US2 — o valor da sugestão é aparecer enquanto se digita. |
| `useDeferredValue` / `useTransition` do React | Ajudam na prioridade de renderização, não na ordem de chegada de respostas de rede. Resolvem outro problema. |

---

## R4 — Semântica acessível do campo de busca

**Decisão**: implementar o padrão **combobox do WAI-ARIA 1.2** à mão:

- `<input role="combobox">` com `aria-expanded`, `aria-controls` e `aria-autocomplete="list"`.
- `<ul role="listbox">` com `<li role="option">`, cada uma com `id` estável.
- **Foco virtual**: o foco do DOM nunca sai do input; `aria-activedescendant` aponta para a opção
  em destaque. Setas movem o destaque, Enter aciona, Esc fecha (FR-019).
- Região `aria-live="polite"` fora da lista anunciando quantidade de resultados / ausência deles,
  para satisfazer FR-027 sem tagarelar a cada tecla (a região só anuncia quando a busca conclui).

**Rationale**: é o padrão que leitores de tela realmente esperam de um campo de sugestões. O foco
virtual é o que permite continuar digitando enquanto se navega pela lista — mover o foco real para
as opções quebraria isso. E é a mesma decisão "sem biblioteca" tomada para o carrossel na feature
001: o controle sobre foco e anúncio é o produto aqui, não um detalhe a delegar.

**Alternativas consideradas**:

| Alternativa | Por que foi descartada |
|---|---|
| `<datalist>` nativo | Não permite estilizar, não exibe pôster, e o comportamento varia entre navegadores. Não atende FR-010 nem os estados de erro/carregando. |
| Biblioteca de combobox (Downshift, Radix, Headless UI) | Resolveria a semântica, mas acrescenta dependência nova, contraria a linha "sem biblioteca" já estabelecida, e o Princípio V cobra autoria justamente nesta superfície. |
| Foco real percorrendo as opções | Tira o cursor do input; quem quiser corrigir uma letra depois de descer na lista perde o contexto. |

---

## R5 — Ordenação e limite das sugestões

**Decisão**: ordenar **prefixo antes de conteúdo**, desempatando por título; limitar a **6**
sugestões; devolver `truncated: true` quando houver mais correspondências que o limite.

**Rationale**:

- Quem digita "mat" espera "Matrix" antes de "Chamado da Mata". Ranquear prefixo primeiro é a
  expectativa mínima de uma busca por título.
- O desempate por título torna o resultado determinístico — mesma razão pela qual
  `get_highlighted_movies` desempata por título: teste que depende de ordem de banco fica instável.
- 6 cabe na tela de 360 px sem virar uma lista rolável de tamanho imprevisível, e o `truncated`
  cumpre FR-011 (comunicar que há mais) sem precisar contar tudo.

**Alternativas consideradas**: ordenar por popularidade do TMDb (não temos o campo persistido, e
buscá-lo violaria o Princípio VII); ordenar por proximidade da próxima sessão (mistura relevância
de busca com disponibilidade — a busca não deve esconder filme sem sessão, ver R6).

---

## R6 — O que a busca devolve: catálogo inteiro ou só o comprável

**Decisão**: devolver **todos os filmes ativos** que correspondam, tenham ou não sessão à venda.

**Rationale**: é o que o spec determina no caso de borda — "a busca não mente sobre o catálogo". A
página do filme é quem comunica a indisponibilidade, e ela já tem esse estado desde a feature 001.
Esconder da busca um filme que existe no site produz o pior resultado possível: a pessoa procura
pelo nome exato e recebe "nada encontrado" enquanto o filme está visível em outra tela.

**Contraste deliberado com a feature 001**: o carrossel **só** destaca filme com sessão publicada e
futura (FR-002 da 001), porque destaque é promessa de compra. Busca é navegação, não promessa. As
duas regras divergem de propósito e isso está registrado aqui para não parecer inconsistência.

---

## R7 — Fixação do cabeçalho na rolagem

**Decisão**: `position: sticky; top: 0` no elemento do cabeçalho.

**Rationale**: `sticky` mantém o elemento no fluxo do documento, então ele reserva a própria
altura e nenhuma página precisa compensar com `padding-top`. `fixed` tiraria o cabeçalho do fluxo,
exigindo que cada página conhecesse a altura dele — acoplamento que o `layout.tsx` não deve impor.
`sticky` também não sobrepõe conteúdo na impressão, atendendo o caso de borda correspondente.

**Ponto de atenção**: o carrossel da feature 001 usa `--altura-painel: clamp(30rem, 78vh, 44rem)`.
Com o cabeçalho ocupando espaço no fluxo, a primeira dobra encolhe. A altura do cabeçalho entra em
`tokens.css` como `--altura-cabecalho` para que esse ajuste seja feito em um lugar só.

---

## R8 — Título do documento e identidade "ticket.com"

**Decisão**: `metadata.title` do `layout.tsx` passa de `"Cinema — ingressos"` para
`"ticket.com — ingressos de cinema"` (FR-004), e o wordmark no cabeçalho é texto, não imagem.

**Rationale**: texto é selecionável, escala com o zoom, é lido corretamente por leitor de tela e
não exige um asset. A autoria pedida pelo Princípio V vem do tratamento tipográfico (peso, cor de
destaque no sufixo `.com`, espaçamento), não de um logotipo importado.

**Registro deliberado**: "ticket.com" é o nome de marca do projeto, escrito assim por pedido do
usuário. Não há link para o domínio real, nem uso de marca, cor ou logotipo de qualquer empresa
existente de nome semelhante. O wordmark aponta para `/` (FR-002).
