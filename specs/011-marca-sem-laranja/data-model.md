# Data Model — Marca sem Laranja

**Feature**: `011-marca-sem-laranja` · **Data**: 2026-08-12

Esta feature não tem modelo de dados: não toca banco, API, seed nem migração. O que ela tem é um
**grafo de tokens** — e ele merece o mesmo rigor, porque é a única estrutura que esta feature altera.

---

## Os cinco valores que mudam

Todos em `frontend/styles/tokens.css`. **Nenhum outro arquivo do front-end define cor de marca.**

| Token | Antes | Depois | Papel |
|---|---|---|---|
| `--cor-destaque` | `#ff5c39` | **`#ff2e88`** | ação, seleção, marca, texto de realce |
| `--cor-destaque-forte` | `#ff7a5c` | **`#ff5ca3`** | hover **e contorno de foco global** |
| `--cor-destaque-fraca` | `rgba(255,92,57,.14)` | **`rgba(255,46,136,.14)`** | fundo de realce sutil |
| `--cor-destaque-vestigio` | `rgba(255,92,57,.2)` | **`rgba(255,46,136,.2)`** | substituto de cartaz |
| `--cor-sobre-destaque` | `#150703` | **`#12040a`** | texto **sobre** o destaque |

**As opacidades de `-fraca` e `-vestigio` não mudam.** Foram calibradas na 006; o que muda é a matiz.
Alterá-las junto misturaria duas decisões e tornaria qualquer regressão difícil de atribuir.

**`--cor-sobre-destaque` é recalibrada, não herdada.** O valor antigo é um quase-preto tingido de
laranja; sobre magenta ele puxaria para um marrom sujo. O novo carrega a matiz nova.

### Um token novo

| Token | Valor | Consumidores permitidos |
|---|---|---|
| `--fonte-marca` | a família da marca, com fallback | **exatamente um**: o componente de marca |

Nenhum texto de interface pode consumi-lo (FR-016). É o que impede a família de display vazar para
corpo de texto, onde ela seria pior que a atual.

---

## O que NÃO muda, e por que cada um está aqui

| Token | Valor | Por que fica |
|---|---|---|
| `--cor-fundo`, `--cor-superficie`, `--cor-borda`… | inalterados | A base escura é o que a 006 fixou e esta feature preserva. A emenda é no destaque. |
| `--cor-sucesso` `#3ecf8e` | inalterado | Cor de estado. Mudar altera o significado de um estado — fora de escopo. |
| `--cor-alerta` `#f5b544` | inalterado | Idem. **E é o que eliminou o âmbar da disputa** (R1). |
| `--cor-erro` `#ff6b6b` | inalterado | Idem. |
| **`--cor-fundo-qr` `#ffffff`** | **inalterado** | Exceção deliberada da 008. Leitor de QR depende do contraste entre módulo escuro e fundo claro; harmonizá-lo com a marca faria a catraca falhar de ler. **É o token mais provável de ser mudado por engano nesta feature.** |
| `--cor-fundo-video` `#000` | inalterado | Preto real para a barra do vídeo desaparecer. |
| `--veu-painel` e variantes | inalterados | Garantem contraste do texto sobre a arte do filme. Podem acompanhar a base **se** ela mudasse — não muda. |
| `--cor-assento-*` | inalterados | Derivam de bordas e texto, não do destaque. |

---

## O mapa: onde o destaque atua hoje

FR-041 exige este mapa, e a razão é que a cor precisa ser avaliada contra **todos** os papéis, não só
contra o cabeçalho. **28 usos de `--cor-destaque`**, distribuídos assim:

### Papel 1 — Ação principal (preenchimento + texto por cima)

O par `--cor-destaque` / `--cor-sobre-destaque`, e o hover troca o fundo para `-forte`.

| Superfície | Elemento |
|---|---|
| `entrar` | botão Entrar |
| `pagamento` | botão Pagar e receber ingressos |
| `meus-ingressos` | ação do estado vazio e dos avisos |
| `portaria` | botão Validar e ação dos avisos |
| `highlights` | ação do painel de destaque |
| `tickets` | botão primário do painel de link |
| `seats` | ação de confirmar lugares |

**É o papel que exige os dois contrastes**: a cor sobre o fundo escuro **e** o texto sobre a cor.

### Papel 2 — Foco de teclado

| Superfície | Elemento |
|---|---|
| `tokens.css:293` | **contorno de foco global**, `--cor-destaque-forte` |
| `payment` | contorno do campo em foco |

**O uso mais frágil da feature.** Um token escurecido "para a marca ficar mais elegante" apaga o
foco de teclado — e nada reclama.

### Papel 3 — Seleção

| Superfície | Elemento |
|---|---|
| `seats` | assento selecionado (preenchimento + borda) |
| `filme` | sessão escolhida (borda) |
| `portaria` | sessão da porta escolhida (borda) |

**Aqui mora o risco de dependência de cor** (FR-030). O assento selecionado usa preenchimento **e**
forma; se o ajuste fino reduzir a forma, o estado passa a depender só de cor.

### Papel 4 — Marca e realce de texto

| Superfície | Elemento |
|---|---|
| `header` | sufixo `.com` |
| `tickets`, `meus-ingressos`, `gate` | o lugar do ingresso, em destaque |
| `portaria` | horário da sessão na lista de portas |

**Exige contraste de texto** (≥ 4.5:1), não só de componente — é o papel mais exigente da cor.

### Papel 5 — Vestígio

| Superfície | Elemento |
|---|---|
| `rows`, `highlights` | gradiente radial do substituto de cartaz |

Onde o filme não tem arte. Se ficar para trás, aparece um respingo laranja num sistema magenta —
exatamente o "vestígio" que FR-004 proíbe.

---

## Os invariantes que o teste verifica

`frontend/tests/tokens.test.ts` lê `tokens.css` e calcula. É o análogo, nesta feature, do teste de
concorrência das anteriores — a única coisa entre o projeto e um defeito que ninguém vê (R10).

### 1. Contraste

| Par | Mínimo | Medido |
|---|---|---|
| `--cor-destaque` sobre `--cor-fundo` (texto) | 4.5 | **5.64** |
| `--cor-destaque` sobre `--cor-superficie` (texto) | 4.5 | **5.23** |
| `--cor-destaque-forte` sobre `--cor-fundo` (foco) | 3.0 | **6.88** |
| `--cor-sobre-destaque` sobre `--cor-destaque` | 4.5 | **5.73** |
| `--cor-sobre-destaque` sobre `--cor-destaque-forte` | 4.5 | **6.98** |

**Os dois últimos são um par, não um.** O texto do botão vive sobre a base em repouso e sobre a
`-forte` no hover — e hover é o estado em que a pessoa está quando vai clicar.

### 2. Distância de estado (ΔE, CIELAB)

| Par | Mínimo | Medido |
|---|---|---|
| `--cor-destaque` × `--cor-erro` | 25 | **33.2** |
| `--cor-destaque` × `--cor-alerta` | 25 | ~60 |
| `--cor-destaque` × `--cor-sucesso` | 25 | ~75 |

Impede que uma "harmonização" futura aproxime a marca do alerta ou do erro. É a mesma medida que
eliminou o âmbar na fase de pesquisa, agora congelada como regra.

### 3. Ausência da cor antiga

Nenhuma ocorrência de `ff5c39`, `ff7a5c` ou `255, 92, 57` em nenhum arquivo do front-end.

### 4. Nenhum valor de cor fora dos tokens

Nenhum hexadecimal ou `rgba(` de cor de marca em arquivo de componente. É a disciplina da 006,
verificada em vez de confiada — e é o que garante que os 12 consumidores não precisaram ser tocados.

---

## O componente de marca

```text
BrandMark                       decide: destino por PAPEL (010), rótulo acessível, variante
   └── MarcaGrafica             desenha: caminho vetorial, sem dependência de fonte
```

**Separados de propósito.** A marca é geometria fixa; o `BrandMark` carrega a única lógica da
feature — o destino que muda por papel, entregue na 010. Enterrar essa lógica dentro de um `<svg>` é
a forma mais provável de perdê-la numa refatoração, e perdê-la significa a portaria voltando a cair
no catálogo.

**A marca é caminho, não texto.** Se fosse texto na família da marca, dependeria de a fonte ter
chegado — e não serviria como ícone de aba, onde não há fonte nenhuma.

### Variantes

| Variante | Composição | Onde |
|---|---|---|
| completa | marca + `ticket` + `.com` com o ponto em destaque | cabeçalho em tela larga |
| compacta | só a marca | tela estreita, portaria, ícone de aba |
