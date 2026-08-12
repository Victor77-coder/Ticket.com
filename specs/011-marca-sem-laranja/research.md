# Research — Marca sem Laranja

**Feature**: `011-marca-sem-laranja` · **Data**: 2026-08-12

Doze decisões. As que mais importam são **R1** (a cor sai por eliminação, não por gosto), **R2** (o
conceito que sobreviveu), **R8** (a logo) e **R10** — a falha silenciosa desta feature, que nenhum
teste existente pegaria.

---

## R1 — A cor não é escolhida. É o que sobra depois das restrições

**Decisão**: `#ff2e88` — magenta de neon.

**Racional**: a escolha parece subjetiva e não é. Quatro restrições, aplicadas em ordem, deixam uma
região do círculo cromático:

**Restrição 1 — as proibições nomeadas.** Roxo, índigo e violeta (≈250–290°) e o par creme com
serifada terracota estão vetados pela spec, por serem a assinatura visual do que o desafio chama de
saída de ferramenta. Some também o próprio laranja (11°).

**Restrição 2 — não colidir com cor de estado, e esta é a que ninguém antecipa.** O sistema já tem
três cores com significado fixo, e a marca não pode ser confundível com nenhuma:

| Token | Valor | Matiz |
|---|---|---|
| `--cor-sucesso` | `#3ecf8e` | 153° |
| `--cor-alerta` | `#f5b544` | **38°** |
| `--cor-erro` | `#ff6b6b` | 0° |

É o que **elimina o âmbar**, que era o candidato mais óbvio para um cinema — marquise, bilheteria,
canhoto de ingresso. Medido: âmbar `#ffd447` fica a **8° do `--cor-alerta`**. Adotá-lo obrigaria a
mover a cor de alerta, e mover uma cor de estado muda o significado de um estado — coisa que as
Assumptions da spec excluem explicitamente. O âmbar não foi rejeitado por gosto; ele custa caro
demais.

**Restrição 3 — funcionar nos quatro papéis.** A mesma cor é foco de teclado, ação principal,
seleção de assento e marca. Precisa de contraste ≥ 4.5:1 como texto sobre o fundo escuro **e** de
uma cor de texto escura em cima dela que também atinja 4.5:1.

**Restrição 4 — não ser a cor padrão de tecnologia.** Azul (217°) tem a melhor separação de todas
(ΔE 101 do estado mais próximo) e é rejeitado assim mesmo: é o azul padrão de todo produto de
software, vizinho do índigo vetado, e a assinatura exata do "dark SaaS" que a spec manda evitar. A
melhor nota nas medidas não vence o pior resultado no critério anti-slop.

**O que sobra**: a faixa magenta (≈320–340°). E ela passa em tudo:

| Medida | `#ff2e88` | Mínimo |
|---|---|---|
| Como texto sobre `--cor-fundo` | **5.64:1** | 4.5 |
| Como texto sobre `--cor-superficie` | **5.23:1** | 4.5 |
| Como contorno de foco (`-forte`) | **6.88:1** | 3.0 |
| Texto escuro sobre ela | **5.73:1** | 4.5 |
| ΔE do estado mais próximo (`--cor-erro`) | **33.2** | 25 |

**Alternativas rejeitadas, com o motivo medido**:

| Direção | Por que não |
|---|---|
| **Manter o laranja** | É o pedido explícito da feature — a identidade não podia continuar sendo a de todo produto de entretenimento escuro. E o laranja fica a **ΔE 20 do `--cor-erro`**, o mais próximo de todos: era, ele próprio, o candidato mais confundível com um estado. |
| **Âmbar / ouro de marquise** `#ffd447` | 8° do `--cor-alerta`. Exigiria mover uma cor de estado — fora de escopo por decisão da spec. Contraste excelente (13.9:1), e nada disso importa. |
| **Lima ácido** `#d7f14a` | Passa em tudo (15.6:1, ΔE 45). Rejeitado por leitura: lê como bebida energética, cripto e esporte, não cinema — e é justamente a cor da onda estética atual, o que a coloca dentro do cluster que o critério anti-slop existe para evitar. Sobre a arte de um cartaz, briga com a imagem em vez de emoldurá-la. |
| **Ciano** `#22d3ee` | A assinatura cromática do painel escuro de software. A spec manda evitar dark-SaaS por nome. |
| **Azul elétrico** `#3b82f6` | Melhor separação de todas, pior resultado no critério que importa. Vizinho do índigo vetado. |

---

## R2 — O conceito: as quatro luzes de um cinema, e três já estão ocupadas

**Decisão**: o conceito da paleta passa a ser **"neon de fachada"**.

**Racional**: a 006 fixou a ideia estruturante — *sala escura, a arte do filme é a fonte de luz* — e
escolheu como destaque a **luz de projeção**, daí o laranja. A ideia continua certa; a fonte de luz
é que muda.

Um cinema à noite tem quatro luzes, e a coincidência é grande demais para ser ignorada:

| Luz | Cor | Situação |
|---|---|---|
| Bulbos da marquise | âmbar | **ocupada** por `--cor-alerta` |
| Placa de saída | verde | **ocupada** por `--cor-sucesso` |
| Feixe de projeção | laranja quente | **é a que está saindo**, e vizinha de `--cor-erro` |
| **Neon da fachada** | **magenta** | **livre** |

O neon da fachada é o que se vê **antes de entrar** — é a luz que anuncia que ali tem cinema, e é a
imagem popular de uma sala à noite. Para uma marca chamada `ticket.com`, cuja função é vender a
entrada, a luz do lado de fora é mais apropriada que a de dentro.

Isto não é racionalização depois do fato: a eliminação de R1 é que produziu a região magenta, e o
conceito é o que aquela região significa neste domínio. Se o conceito viesse primeiro, seria
decoração.

---

## R3 — Os nomes de token ficam. Só os valores mudam

**Decisão**: `--cor-destaque`, `--cor-destaque-forte`, `--cor-destaque-fraca`,
`--cor-destaque-vestigio` e `--cor-sobre-destaque` mantêm os nomes.

**Racional**: a disciplina de tokens da 006 **funcionou**, e este é o momento de colher. Verificado:

- o laranja existe em **4 declarações**, todas em `frontend/styles/tokens.css`;
- **12 arquivos** consomem apenas os nomes, com **28 usos** de `--cor-destaque`;
- **zero** hexadecimais de marca espalhados por componente.

Trocar a identidade cromática inteira é, portanto, trocar quatro valores. Renomear os tokens
obrigaria a tocar os doze consumidores — e cada arquivo tocado é uma chance de uma superfície ficar
para trás, que é exatamente o defeito que FR-028 proíbe.

**Alternativa rejeitada**: renomear para algo neutro (`--cor-acao`). Seria mais honesto
semanticamente e custaria 28 edições para ganhar nada verificável.

---

## R4 — A família derivada, valor por valor

**Decisão**:

```text
--cor-destaque:           #ff2e88   base — ação, seleção, marca
--cor-destaque-forte:     #ff5ca3   hover e CONTORNO DE FOCO GLOBAL
--cor-destaque-fraca:     rgba(255, 46, 136, 0.14)
--cor-destaque-vestigio:  rgba(255, 46, 136, 0.20)
--cor-sobre-destaque:     #12040a   texto SOBRE o destaque
```

**Racional de cada um**:

- **`-forte` é mais clara que a base**, não mais escura. É contraintuitivo para "forte", e é o que a
  função exige: ela é o contorno de foco (`tokens.css:293`) e o estado de hover de botões já
  preenchidos com a base. Escurecer reduziria o contraste justamente onde ele é obrigatório.
- **`-fraca` e `-vestigio` mantêm as opacidades de 0.14 e 0.20.** As duas foram calibradas na 006 e
  o que muda é a matiz. Alterá-las junto misturaria duas decisões.
- **`--cor-sobre-destaque` foi recalibrada, não herdada.** O valor antigo (`#150703`) é um quase-preto
  tingido de laranja; sobre magenta ele puxaria para um marrom sujo. O novo (`#12040a`) é a mesma
  ideia com a matiz nova: 5.73:1 sobre a base e 6.98:1 sobre a `-forte`.

**Por que `#ff2e88` e não o rosa mais claro `#ff4d9d`**, que mede melhor (6.40:1): o destaque é usado
como **preenchimento grande** — assento selecionado, botão principal. Um rosa claro em área grande lê
como confeito; o magenta profundo lê como letreiro. Os dois passam com folga, então a medida não
decide, e o critério passa a ser o que a cor comunica.

---

## R5 — A cor sobre o destaque precisa passar em DOIS fundos

**Decisão**: `--cor-sobre-destaque` é verificada contra `--cor-destaque` **e** contra
`--cor-destaque-forte`.

**Racional**: é o erro fácil desta feature. O texto do botão principal fica sobre a base em repouso e
sobre a `-forte` no hover — dois fundos, um texto só. Medir só o primeiro deixa o hover fora da
verificação, e hover é o estado em que a pessoa está justamente quando vai clicar.

---

## R6 — Tipografia da marca: família própria, e não um corte extremo do Archivo

**Decisão**: **Cabinet Grotesk** (Fontshare), reservada exclusivamente à marca, exposta como
`--fonte-marca`.

**Racional**: a spec abria as duas portas — família própria ou corte extremo do Archivo com
justificativa. A família própria vence por um motivo verificável: o Archivo já é usado em **dois**
cortes na interface (`wdth` 100 no texto, 118 no display). Um terceiro corte extremo seria mais uma
posição no mesmo eixo, e "a marca é o Archivo mais condensado" é uma distinção que ninguém percebe a
20px no cabeçalho — que é o tamanho em que a marca vive.

Cabinet Grotesk é uma grotesca de display com personalidade nas letras que o nome tem em maior
número: `t`, `k`, `c`. `ticket.com` é quase inteiramente feito das letras onde ela se diferencia.

**Alternativas rejeitadas**:

- **Corte extremo do Archivo (`wdth` 62, peso 700)** — zero dependência nova, e um argumento
  tipográfico real (bloco de créditos de cartaz). Rejeitada porque a diferença some no tamanho em que
  a marca é vista. Fica registrada como a saída se a licença de qualquer família nova travar.
- **Clash Display** — a face de display mais usada em interface escura contemporânea. Escolhê-la
  seria escolher exatamente a tipografia que o critério anti-slop existe para evitar.
- **Boska / Zodiak** (serifadas de alto contraste) — brigariam com a grotesca neutra da interface e
  puxariam a marca para editorial, não para cinema. E serifada de alto contraste em corpo pequeno
  perde os traços finos.

**Obrigação que fica para a implementação**: baixar o arquivo de licença, conferir que permite uso
comercial e **versioná-lo junto da fonte**. Este documento não trata a licença como resolvida — FR-014
exige o registro, e registro é o arquivo, não a lembrança de alguém.

---

## R7 — A fonte da marca é servida do próprio domínio

**Decisão**: a família da marca é auto-hospedada, como a 006 já faz com a da interface.

**Racional**: o Princípio VII aplicado a fontes — nenhuma requisição a terceiro em tempo de visita.
A 006 registrou isso ao escolher `next/font`, que baixa em tempo de build e serve do próprio domínio,
e não há razão para a marca abrir uma exceção.

**Consequência que precisa de cuidado**: a família da marca vem de arquivo local, não do catálogo
que `next/font/google` conhece. O carregamento precisa declarar a métrica de fallback — sem isso, o
cabeçalho **salta** quando a fonte chega, e FR-018 proíbe isso.

---

## R8 — A logo: o ponto que o nome já tem

**Decisão**: a marca gráfica é o **`t` inicial com o ponto do `.com`** — desenhada como caminho
vetorial, não como texto.

**Racional da derivação**: `ticket.com` tem uma única pontuação, e ela já é tratada como elemento de
marca desde a 002 — o sufixo `.com` sai na cor de destaque. A logo não inventa um símbolo novo:
promove o que o nome já tem.

- **Variante completa**: a marca seguida do nome por extenso, `ticket` no tom de texto e `.com` mais
  leve, com o ponto no destaque.
- **Variante compacta**: só a marca — `t` no tom de texto, ponto no destaque. É a que serve tela
  estreita, portaria e ícone de aba.

**Por que não um ícone de ingresso, claquete ou pipoca** (FR-020): esses três são o vocabulário de
biblioteca do domínio. Qualquer um deles seria intercambiável com o de qualquer outro cinema — o
oposto de marca. O `t` com ponto só significa alguma coisa para **este** nome.

**Por que caminho vetorial e não texto na fonte da marca**: se a marca fosse texto, ela dependeria da
fonte ter chegado. Como caminho, ela desenha igual no primeiro quadro — e é o que permite usá-la como
ícone de aba, onde não há fonte nenhuma.

**Sem brilho, halo ou sombra** (FR-023): o contraste de `#ff2e88` sobre o fundo escuro é 5.64:1. A
marca não precisa de efeito para se destacar, e efeito é item proibido do contrato anti-slop.

### Emenda de 2026-08-12 — a marca é geometria PRÓPRIA, não um `t` vetorizado da fonte

Ao ler a licença (T004), a redação obrigou a corrigir a derivação acima. A EULA da Fontshare:

- **§01 concede** — "You may use the Font Software to create logos and other graphic elements,
  vector files or other scalable drawings". Vetorizar para logo está dentro da concessão.
- **§05 cobra caro por isso** — "Any derivative works are the exclusive property of the Licensor
  and shall be subject to the terms and conditions of this EULA. Derivative works may not be
  sub-licensed, sold, leased, rented, loaned, or given away without express written permission."

Um `t` vetorizado da Cabinet Grotesk seria trabalho derivado, e a marca do produto passaria a ser
propriedade do licenciador da fonte. Para um projeto de avaliação isso não é bloqueio, mas é
exatamente o tipo de coisa que o Princípio VI manda escrever em vez de deixar passar.

**A correção melhora o desenho**, o que é sorte e não mérito: a marca gráfica passa a ser
**construção geométrica nossa** — o `t` e o ponto desenhados em traços retos e um círculo, com as
proporções da grade da própria marca. O **nome por extenso** continua usando a fonte como TEXTO, que
é o uso mais direto que §01 concede e não cria derivado nenhum.

Efeito colateral bom: a razão original de a marca ser caminho — desenhar igual antes de a fonte
chegar, e servir como ícone de aba — continua valendo, e agora sem depender de outlines de terceiro.

---

## R9 — A marca evolui o `BrandMark`, não o substitui

**Decisão**: o componente existente ganha a marca gráfica e a fonte nova, e **preserva** o
comportamento que a 010 lhe deu: o destino muda por papel — a portaria vai para a tela dela.

**Racional**: FR-025 exige isso, e é um lembrete de que esta feature é visual. Reescrever o
componente do zero seria a maneira mais provável de perder aquele comportamento sem perceber, porque
ele não é óbvio olhando um componente de logotipo. O teste da 010 que fixa o destino por papel
continua sendo a guarda.

---

## R10 — A falha silenciosa: contraste quebra sem quebrar teste nenhum

**Decisão**: um teste automatizado que **lê os tokens** e calcula os contrastes exigidos, falhando
quando qualquer par cai abaixo do mínimo.

**Racional**: é a armadilha desta feature, e ela é de uma classe diferente das anteriores.

Nas features 007 a 010, o risco era de correção — e havia sempre um teste ou uma constraint que
reclamava. Aqui, **trocar um valor de cor não quebra absolutamente nada**. Todos os 197 testes de
front-end continuam verdes com um contorno de foco invisível, com texto ilegível sobre o botão
principal, com o assento selecionado indistinguível do tomado. Nenhum teste de comportamento mede
contraste, e nenhum vai começar a medir por acidente.

Pior: o dano é invisível para quem **escolheu** a cor. Quem passou uma hora olhando a paleta enxerga
distinções que um usuário de passagem não enxerga, e um contorno de foco fraco só incomoda quem
navega por teclado.

**O teste fecha três coisas de uma vez**, todas lendo o mesmo arquivo de tokens:

1. **Contraste** — cada par (texto sobre fundo, texto sobre superfície, contorno de foco, texto sobre
   destaque, texto sobre destaque-forte) contra o mínimo da regra;
2. **Distância de estado** — ΔE mínimo entre o destaque e cada cor de estado, para impedir que uma
   "harmonização" futura aproxime a marca do alerta ou do erro;
3. **Ausência da cor antiga** — nenhum valor do laranja em nenhum arquivo do front-end.

É o análogo, nesta feature, do teste de concorrência das anteriores: a única coisa entre o projeto e
um defeito que ninguém vê.

---

## R11 — Distinção sem cor: o que já existe e como não perdê-lo

**Decisão**: nenhuma mudança estrutural. O que muda é a **verificação**, que passa a ser explícita.

**Racional**: o mapa de assentos já não depende de cor — cada estado tem forma própria, contorno ou
preenchimento, e a 007 registrou isso. A portaria já distingue os quatro desfechos por símbolo e
título antes da cor, e a 010 registrou. As duas continuam corretas com a paleta nova.

O risco não é o código atual; é o ajuste que vem depois. Quem estiver acertando o magenta pode achar
que o assento selecionado ficou "forte demais" e reduzir a borda — e nesse instante o estado passa a
depender só de cor, sem que nada reclame. Por isso as duas superfícies entram na conferência da
feature em vez de serem dadas como resolvidas.

---

## R12 — O contrato anti-slop ganha sucessor, não emenda

**Decisão**: um documento novo em `contracts/`, que **substitui** o da 006 e declara isso na primeira
linha. O da 006 permanece onde está, marcado como sucedido.

**Racional**: aquele contrato é o único critério subjetivo da 006 com regra escrita, e existe
precisamente para que "não passou" venha com motivo. Editá-lo no lugar apagaria o registro de que a
paleta um dia foi outra — e o Princípio VI pede rastro, não estado final.

O item **"Laranja de projeção"** dá lugar a **"Neon de fachada"**, com o mesmo formato: o destaque
aparece em ao menos um elemento de ação e é a única cor saturada da tela. Entram dois itens novos —
tipografia de marca e marca gráfica —, porque a feature promete os dois. E a lista de proibições
ganha "qualquer vestígio da cor antiga".
