# Phase 1 — Data Model: O Sistema de Tokens

**Feature**: `006-visual-identity` | **Date**: 2026-08-11

Esta feature não tem modelo de dados no sentido usual — não há tabela, campo nem migração. O
"modelo" aqui é o **sistema de tokens**: a fonte única de verdade de cor, tipografia, espaçamento,
forma e movimento que o Princípio V exige.

Registrar assim não é formalidade. Tratar os tokens como esquema é o que impede a próxima feature
de espalhar valores soltos de novo.

---

## A regra de extensão

**Nenhum nome de token existente pode desaparecer.** Cinco módulos CSS já os consomem, e remover
um nome quebra silenciosamente — CSS não reclama de variável inexistente, apenas não aplica nada.

| Operação | Permitida? |
|---|---|
| Acrescentar token novo | sim |
| Mudar o **valor** de um token existente | sim — é o objeto desta feature |
| Renomear um token | **não** nesta feature |
| Remover um token | **não** nesta feature |

O contrato completo dos nomes está em
[contracts/token-contract.md](./contracts/token-contract.md).

---

## Tokens que mudam de valor

### Escala tipográfica (R3)

Os sete valores de hoje não seguem razão nenhuma. Passam a seguir 1,25.

| Token | Antes | Depois |
|---|---|---|
| `--texto-xs` | `0.75rem` | `0.75rem` |
| `--texto-sm` | `0.875rem` | `0.8125rem` |
| `--texto-md` | `1rem` | `1rem` |
| `--texto-lg` | `1.25rem` | `1.25rem` |
| `--texto-xl` | `1.75rem` | `1.5625rem` |
| `--texto-2xl` | `2.5rem` | `1.953rem` |
| `--texto-3xl` | `clamp(2rem, 5vw, 3.75rem)` | mantido como apelido de `--texto-display` |

### Pesos

| Token | Antes | Depois |
|---|---|---|
| `--peso-normal` | 400 | 400 |
| `--peso-medio` | 500 | 500 |
| `--peso-forte` | 700 | 600 |

O 700 migra para o display; 600 é o peso de título de seção. Com fonte variável a diferença é
contínua, e 700 em texto de interface fica pesado demais ao lado de um display expandido.

---

## Tokens novos

### Tipografia

| Token | Valor | Papel |
|---|---|---|
| `--fonte-base` | a variável de `next/font` + pilha de reserva | **substitui** a pilha do sistema |
| `--texto-display` | `clamp(2.5rem, 6vw, 4.5rem)` | título do filme em destaque |
| `--largura-display` | `118` | eixo `wdth` do display (expandido) |
| `--largura-normal` | `100` | eixo `wdth` do texto |
| `--peso-display` | `700` | peso do display |
| `--espacamento-display` | `-0.02em` | ajuste ótico do display |

`--largura-*` são números crus porque alimentam `font-variation-settings`, que não aceita
unidade. É a única categoria de token que não carrega unidade, e por isso está anotada.

### Ritmo vertical (R4)

| Token | Valor | Papel |
|---|---|---|
| `--ritmo-dobra` | `clamp(3.5rem, 8vw, 6rem)` | painel de destaques → primeira trilha |
| `--ritmo-secao` | `clamp(2rem, 5vw, 3.5rem)` | trilha → trilha |

São tokens de **relação**, não de espaço bruto — por isso não entram na escala `--esp-*`. A
distinção existe porque `--esp-6` pode ser usado em qualquer lugar; `--ritmo-dobra` tem um único
significado.

### Cor

| Token | Valor | Papel |
|---|---|---|
| `--cor-sobre-destaque` | `#150703` | texto sobre o botão laranja |

Elimina o único valor literal do projeto (R10) e nomeia um papel que hoje é implícito.

### Movimento (R5, R6)

| Token | Valor | Papel |
|---|---|---|
| `--movimento-cartaz` | `220ms` | elevação do cartaz |
| `--elevacao-cartaz` | `-6px` | quanto o cartaz sobe |
| `--curva-saida` | `cubic-bezier(0.22, 0.61, 0.36, 1)` | desaceleração dos movimentos |

`--transicao-rapida` e `--transicao-painel` permanecem, com os valores atuais.

---

## Tokens inalterados

Toda a paleta — superfícies, texto, marca, estados — e os dois véus permanecem **exatamente** como
estão. FR-020 veta mudança de paleta, e o véu é o que garante contraste sobre qualquer arte
(FR-028).

Escala de espaçamento `--esp-1` a `--esp-8`, raios e sombras: inalterados.

---

## Invariantes que a implementação precisa preservar

1. **Nenhum valor de cor, espaçamento, escala, raio ou duração fora deste arquivo.** É o SC-001, e
   a varredura de R11 é o que o torna verificável.
2. **Nenhuma `font-family` fora deste arquivo.** SC-002.
3. **O véu não afina.** Ele existe para contraste, não para estética.
4. **`:focus-visible` mantém contorno perceptível.** Acessibilidade entregue não regride.
5. **No máximo três tokens de movimento com deslocamento.** Acima disso, o teto de FR-015 caiu.

---

## O que NÃO é criado

| Não criado | Por quê |
|---|---|
| Arquivo de tema separado | Duplicaria a fonte única de verdade que o Princípio V exige |
| Tokens de modo claro | Fora de escopo; o produto é uma sala escura por decisão |
| Segunda família tipográfica | O eixo `wdth` do Archivo já dá o contraste (R1) |
| Tokens por componente | Token é vocabulário do sistema; um `--cartaz-largura-em-tablet` seria valor solto com nome bonito |
