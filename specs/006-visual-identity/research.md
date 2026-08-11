# Phase 0 — Research: Identidade Visual

**Feature**: `006-visual-identity` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado. Nenhum `NEEDS CLARIFICATION`
permanece aberto ao fim desta fase.

---

## R1. A tipografia

**Decision**: **Archivo**, família única em fonte variável, com o eixo de largura (`wdth`)
fazendo a distinção entre display e texto.

| Papel | Tratamento |
|---|---|
| Display — título do filme em destaque | peso 700, largura ~118 (expandido) |
| Título de seção | peso 600, largura 100 |
| Texto | peso 400, largura 100 |

**Rationale**:

- **É uma família só, e ainda assim há contraste real.** Verificado antes de decidir: Archivo é
  variável com eixos de peso e de largura, indo de ExtraCondensed a Expanded. Isso resolve o
  problema clássico de parear duas famílias — não há duas vozes a casar, e a coerência é
  estrutural, não fruto de bom gosto.
- **Um arquivo em vez de dois.** Menos peso, menos requisição, e o corte expandido não pode
  divergir do texto porque é o mesmo desenho.
- **O corte expandido evoca cartaz de mostra de cinema**, não catálogo de streaming. É o
  ingrediente que faz a primeira dobra passar no SC-003.
- **Licença SIL Open Font License** — permite uso comercial, modificação e redistribuição
  embutida, sem exigir atribuição na interface. Num repositório público avaliado por terceiros, é
  a licença mais fácil de defender.

**Alternatives considered**:

- **Clash Display + Satoshi (Fontshare)** — apresentada ao usuário com mockup e descartada por
  ele. A ITF Free Font License foi verificada e permite uso comercial e self-hosting, proibindo
  só a revenda dos arquivos; a recusa foi por margem de segurança, não por impedimento. Também
  exigiria casar duas famílias.
- **Bespoke Stencil (Fontshare)** — o sinal de "cinema" mais alto dos três, e o mais fácil de
  envelhecer mal. Estêncil cansa em título longo e pode ler como "militar".
- **Inter, Roboto ou a pilha do sistema** — é exatamente o que a feature existe para eliminar.
  São as fontes que qualquer aplicação usa por padrão; nenhuma delas comunica escolha, que é o
  que o Princípio V cobra.

**A registrar no README** (FR-012): a família, a licença, e por que não a fonte do sistema.

---

## R2. Como a fonte é carregada

**Decision**: `next/font/google` com `Archivo`, declarando o eixo `wdth`, exposta como variável
CSS que os tokens consomem.

**Rationale**:

- **Baixa em tempo de build e serve do próprio domínio.** Nenhuma requisição a terceiro em tempo
  de visita — é o Princípio VII aplicado a fontes, o mesmo raciocínio que mantém o TMDb fora do
  caminho de leitura.
- **Gera automaticamente um fallback ajustado por métrica.** É o que satisfaz FR-011 sem trabalho
  manual: o texto de reserva ocupa o mesmo espaço da fonte final, então nada salta quando ela
  chega.
- **`display: swap`** mantém o texto legível durante o carregamento, em vez de invisível.

**Alternatives considered**:

- **`<link>` para `fonts.googleapis.com`** — requisição a terceiro em toda visita, mais um
  domínio no caminho crítico, e nenhum ajuste de métrica. Contraria o Princípio VII.
- **Baixar o `.woff2` e declarar `@font-face` à mão** — funciona e dá controle total, mas exige
  calcular o `size-adjust` do fallback manualmente para evitar o salto. Trabalho maior para o
  mesmo resultado.

**Consequência assumida**: a família variável é maior que um corte estático. Aceitável por ser um
arquivo só cobrindo todos os pesos e larguras que o produto usa — o conjunto equivalente em
estáticos seria maior.

---

## R3. A escala tipográfica

**Decision**: escala com razão explícita de **1,25** a partir de 1rem, mais um degrau de display
fluido.

| Token | Antes | Depois | Uso |
|---|---|---|---|
| `--texto-xs` | 0.75 | 0.75 | metadados do cartão |
| `--texto-sm` | 0.875 | 0.8125 | apoio, legendas |
| `--texto-md` | 1 | 1 | corpo |
| `--texto-lg` | 1.25 | 1.25 | título de seção |
| `--texto-xl` | 1.75 | 1.5625 | título de página |
| `--texto-2xl` | 2.5 | 1.953 | destaque secundário |
| `--texto-display` | (era `--texto-3xl`) | `clamp(2.5rem, 6vw, 4.5rem)` | título do filme |

**Rationale**: os sete valores de hoje não seguem razão nenhuma — 0.75, 0.875, 1, 1.25, 1.75,
2.5. Os saltos são irregulares, e é isso que faz uma página parecer montada em vez de composta.
Uma razão fixa dá progressão previsível, e o único degrau fora da escala é o display, que é
fluido de propósito porque precisa dominar a dobra em qualquer largura.

**Consequência assumida**: `--texto-sm`, `--texto-xl` e `--texto-2xl` mudam de valor. Nenhum nome
some, então nada quebra — é o que a regra de extensão do contrato de tokens exige.

---

## R4. O ritmo vertical

**Decision**: dois níveis de separação, com números distintos.

| Token | Valor | Onde |
|---|---|---|
| `--ritmo-dobra` | `clamp(3.5rem, 8vw, 6rem)` | entre o painel de destaques e a primeira trilha |
| `--ritmo-secao` | `clamp(2rem, 5vw, 3.5rem)` | entre trilhas consecutivas |

**Rationale**: hoje os dois espaços são o mesmo `--esp-7` de 3rem, e é por isso que a home lê
como lista uniforme em vez de página com hierarquia. FR-001 exige que a separação de dobra seja
maior — a diferença é o que diz ao olho "aqui terminou o destaque e começou o catálogo".

Ambos fluidos porque um respiro de 6rem numa tela de 360px é buraco, e de 3.5rem numa de 1920px
é aperto.

**Alternatives considered**: manter um espaçamento só e diferenciar por linha divisória. Uma
régua entre seções é o recurso mais genérico de layout de catálogo, e resolve com traço o que o
espaço resolve melhor.

---

## R5. O que conta como "movimento"

**Decision**: distinguir **movimento** de **realce**. O teto de três do FR-015 vale só para
movimento.

| Categoria | Definição | Conta para o teto? |
|---|---|---|
| **Movimento** | deslocamento ou escala — `transform` | **sim** |
| **Realce** | mudança de cor, borda ou opacidade em resposta a estado | não |

Os três movimentos do produto:

1. **Elevação do cartaz** ao ponteiro
2. **Transição de painel** do carrossel
3. **Deslocamento da trilha** ao acionar a seta

**Rationale**: sem essa distinção o teto seria arbitrário — um `transition: border-color` num
campo de formulário não é "gesto de movimento", e contá-lo esgotaria o orçamento sem que nada se
mexesse na tela. O que o teto existe para impedir é o acúmulo de coisas que se deslocam, que é o
que faz uma interface parecer inquieta.

Registrado aqui porque é exatamente o tipo de definição que, sem estar escrita, gera discussão na
revisão.

---

## R6. A regra dos 60fps

**Decision**: movimento anima **somente `transform` e `opacity`**. Realce pode animar cor e
borda. **Nada anima `width`, `height`, `top`, `left`, `margin` ou `background-position`.**

**Rationale**: `transform` e `opacity` são compostos pela GPU sem recalcular layout nem repintar.
Cor e borda repintam mas não relayoutam — em três ou quatro elementos por tela, é irrelevante.

**Correção necessária**: o brilho do esqueleto de carregamento hoje anima `background-position`
sobre um gradiente, o que repinta a área inteira a cada quadro, em loop, enquanto a página
carrega — justamente o momento de maior disputa por CPU. Reescrito como um elemento sobreposto
que atravessa com `transform`.

**Consequência assumida**: o esqueleto ganha um elemento a mais. É o preço de tirar um repintura
em loop do caminho crítico.

---

## R7. O tratamento das setas

**Decision**: remover a borda e o fundo circular. As setas viram alvos discretos alinhados à
linha de base do título de seção, com o realce vindo do fundo apenas ao ponteiro.

**Rationale**: o círculo com borda de 1px é o traço mais reconhecível de carrossel de catálogo
genérico — está em toda interface gerada, e é o primeiro sinal que denuncia o produto no SC-003.
Alinhar à linha de base do título integra o controle à seção em vez de sobrepor um widget.

**O que NÃO muda**: a regra de quando aparecem, herdada da 004 — só com transbordo, desabilitadas
nas extremidades. FR-004 é explícito.

**Consequência assumida**: alvos sem borda têm afordância visual menor. Compensado mantendo a
área de toque e o contorno de foco intactos — o alvo continua do mesmo tamanho, só perde a
moldura.

---

## R8. A densidade dos cartazes

**Decision**: cartaz mais largo e espaçamento menor.

| | Antes | Depois |
|---|---|---|
| Largura (desktop) | 10.5rem | 11.5rem |
| Espaço entre cartazes | 1rem | 0.75rem |

Proporção 2:3 mantida, e as reduções por largura de tela mantidas proporcionalmente.

**Rationale**: cartaz maior com respiro menor lê como **parede de cartazes** — a referência é a
vitrine física de um cinema. Cartaz menor com respiro maior lê como grade de aplicativo, que é o
oposto do que a feature busca.

**Consequência assumida**: cabem menos cartazes por tela. É desejável: uma trilha que revela um
cartaz cortado na borda comunica que há mais conteúdo, e faz o gesto de deslizar parecer natural.

---

## R9. O critério da checagem de identidade

**Decision**: critérios escritos em `contracts/anti-slop-review.md`, aplicados a uma captura da
primeira dobra com o cabeçalho recortado.

**Rationale**: SC-003 é o único ponto de julgamento humano da feature, e um critério subjetivo
sem regra escrita é o mesmo que critério nenhum. O documento lista o que precisa estar presente e
o que não pode estar, para que a revisão seja repetível por outra pessoa.

Isolar o julgamento num único critério é deliberado — tudo o mais desta feature é verificável por
varredura.

---

## R10. A dívida de token herdada

**Decision**: a cor `#150703` vira `--cor-sobre-destaque`.

**Rationale**: encontrada na auditoria antes da redação do spec, literal em
`highlights.module.css` e `entrar.module.css`. É a cor do texto sobre o botão laranja — escura o
bastante para contrastar com o laranja, e por isso não é nenhuma das cores de texto existentes.

Nomear resolve as duas coisas: elimina o único valor solto do projeto e dá nome a um papel real
que hoje está implícito.

**Por que entra nesta feature**: uma feature cujo objeto é a disciplina de tokens não pode deixar
passar o único valor que a viola. Com a exceção presente, a varredura do SC-001 não teria
autoridade.

---

## R11. Como as regras viram verificação

**Decision**: varredura por padrão nos módulos CSS, executável a qualquer momento.

| Critério | Verificação |
|---|---|
| SC-001 — sem valor solto | procurar por hex, `rgb(`, `px` fora de `tokens.css` |
| SC-002 — sem família fora dos tokens | procurar por `font-family` fora de `tokens.css` |
| SC-004 — teto de 3 movimentos | contar `transition` e `animation` sobre `transform` |
| R6 — propriedades proibidas | procurar por animação de `width`, `height`, `top`, `left` |
| SC-010 — sem texto de preenchimento | procurar por "lorem", "placeholder", "em breve", "TODO" |

**Rationale**: sem verificação executável, a disciplina de tokens dura até o próximo commit
apressado. Escrita como comando, ela pode entrar no roteiro de revisão e é conferível por
qualquer pessoa, sem depender de quem lembra da regra.

**Consequência assumida**: `px` continua legítimo dentro de `tokens.css` e em bordas de 1px, onde
`rem` não faz sentido. A varredura precisa dessa exceção documentada para não gerar ruído.

---

## R12. Estratégia de testes

**Decision**: **nenhuma asserção nova de comportamento** e **nenhuma asserção existente alterada**.

| Alvo | Como |
|---|---|
| Comportamento intacto | as 95 asserções de front-end continuam passando, sem edição |
| Disciplina de tokens | varredura de R11 |
| Movimento sob preferência reduzida | teste existente do carrossel já cobre; estender à trilha |
| Identidade da primeira dobra | revisão humana com o critério de R9 |

**Rationale**: FR-030 congela os testes existentes de propósito — se a implementação precisar
mudar uma asserção, é sinal de que saiu do escopo visual e entrou em comportamento. O teste que
não muda é, aqui, o instrumento de contenção.

O único teste novo é o de movimento reduzido na trilha, porque a 004 cobriu isso no carrossel mas
não na trilha, e R6 acrescenta um movimento ali.
