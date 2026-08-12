# Contrato — Contraste e Distância de Estado

**Feature**: `011-marca-sem-laranja` · **Data**: 2026-08-12

Este documento fixa os limites que a paleta precisa atingir, e existe porque **trocar um valor de cor
não quebra nenhum teste de comportamento**.

Os 197 testes de front-end continuam verdes com o contorno de foco invisível, com texto ilegível no
botão principal e com o assento selecionado indistinguível do tomado. Nenhum deles mede contraste, e
nenhum vai começar a medir por acidente. Sem este contrato e o teste que o aplica, a única defesa
seria alguém lembrar de conferir.

Pior: o dano é invisível para quem escolheu a cor. Quem passou uma hora olhando a paleta enxerga
distinções que um usuário de passagem não enxerga, e um contorno de foco fraco só incomoda quem
navega por teclado.

---

## Como medir

**Contraste**: razão WCAG 2.1, calculada da luminância relativa dos dois valores.

**Distância perceptual**: ΔE76 em CIELAB. Abaixo de 25, duas cores são confundíveis num elemento
pequeno — que é o tamanho de um selo de estado ou de um texto de erro.

As duas são calculadas **a partir do arquivo de tokens**, não de valores copiados para o teste. Um
teste que guarda sua própria cópia da paleta passa a testar a cópia.

---

## Os limites

### Contraste — todos obrigatórios

| # | Frente | Fundo | Mínimo | Por que este mínimo |
|---|---|---|---|---|
| C1 | `--cor-destaque` | `--cor-fundo` | **4.5** | É usada como **texto** (o `.com`, o lugar do ingresso, o horário da porta) |
| C2 | `--cor-destaque` | `--cor-superficie` | **4.5** | Mesmo papel, sobre cartão elevado |
| C3 | `--cor-destaque-forte` | `--cor-fundo` | **3.0** | Contorno de foco — componente, não texto |
| C4 | `--cor-sobre-destaque` | `--cor-destaque` | **4.5** | Texto do botão em repouso |
| C5 | `--cor-sobre-destaque` | `--cor-destaque-forte` | **4.5** | Texto do **mesmo** botão em hover |
| C6 | `--cor-texto` | `--cor-fundo` | **4.5** | Regressão: a base não pode piorar |
| C7 | `--cor-texto-suave` | `--cor-superficie` | **4.5** | Idem |

**C4 e C5 são um par.** É o erro fácil desta feature: medir o texto do botão só em repouso deixa o
hover fora da verificação, e hover é o estado em que a pessoa está quando vai clicar.

### Distância de estado — todos obrigatórios

| # | Par | Mínimo | Por que |
|---|---|---|---|
| D1 | `--cor-destaque` × `--cor-erro` | **25** | O par mais próximo. Uma marca confundível com erro faz o botão principal parecer um aviso |
| D2 | `--cor-destaque` × `--cor-alerta` | **25** | Foi esta medida que eliminou o âmbar da disputa (R1) |
| D3 | `--cor-destaque` × `--cor-sucesso` | **25** | Completa o conjunto |

### Ausência — todos obrigatórios

| # | Regra |
|---|---|
| A1 | Nenhuma ocorrência de `ff5c39`, `ff7a5c` ou `255, 92, 57` em nenhum arquivo do front-end |
| A2 | Nenhum hexadecimal ou `rgba(` de cor de marca fora de `tokens.css` |

**A2 é a disciplina da 006 verificada em vez de confiada.** É ela que garante que os 12 arquivos
consumidores não precisaram ser tocados — e se um precisar, é sinal de que um valor vazou.

---

## Os valores medidos desta paleta

Registrados para que a próxima pessoa saiba quanta folga existe antes de um ajuste custar caro.

| Medida | Valor | Limite | Folga |
|---|---|---|---|
| C1 | 5.64:1 | 4.5 | confortável |
| C2 | 5.23:1 | 4.5 | **a menor folga do conjunto** |
| C3 | 6.88:1 | 3.0 | grande |
| C4 | 5.73:1 | 4.5 | confortável |
| C5 | 6.98:1 | 4.5 | grande |
| D1 | ΔE 33.2 | 25 | **a menor do conjunto** |

**C2 e D1 são os dois a vigiar.** Escurecer o destaque aperta C2; puxá-lo para o vermelho aperta D1.
Qualquer ajuste futuro de matiz ou luminosidade deve rodar o teste antes de ser considerado.

---

## O que acontece quando um limite cai

O teste falha, nomeando **qual** limite, **qual par** e **quanto** faltou. Uma falha que diz só "o
contraste está ruim" obrigaria a pessoa a refazer a medição para descobrir onde.

E não existe "aprovar com ressalva": um limite abaixo do mínimo é um estado que alguém não vai
conseguir usar. Se um valor novo não passa, o valor é que muda — não o limite.

---

## O que este contrato NÃO cobre

**Se a tela é bonita, e se a marca é reconhecível.** Isso é julgamento humano, e está em
`anti-slop-review.md`, com procedimento escrito para que outra pessoa chegue ao mesmo veredito.

Este documento cobre o que é medível, e para. Um contrato que tentasse medir identidade daria a
falsa sensação de que a parte difícil está automatizada.
