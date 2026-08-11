# Contract — Tokens

**Feature**: `006-visual-identity` | **Date**: 2026-08-11

Esta feature não expõe endpoint. O contrato aqui é interno: **os nomes de token que os componentes
já consomem**. CSS não avisa quando uma variável não existe — apenas não aplica nada —, então
remover um nome quebra em silêncio.

---

## Nomes congelados

Consumidos hoje pelos cinco módulos CSS. **Não podem ser removidos nem renomeados nesta feature.**
O valor pode mudar; o nome, não.

### Superfícies e bordas

`--cor-fundo` · `--cor-superficie` · `--cor-superficie-elevada` · `--cor-borda` ·
`--cor-borda-forte`

### Texto

`--cor-texto` · `--cor-texto-suave` · `--cor-texto-fraco`

### Marca e estados

`--cor-destaque` · `--cor-destaque-forte` · `--cor-destaque-fraca` · `--cor-sucesso` ·
`--cor-alerta` · `--cor-erro`

### Véus

`--veu-painel` · `--veu-painel-base`

> Estes dois são os que garantem contraste do texto sobre qualquer arte de filme. **Não podem ser
> afinados por estética** (FR-028).

### Tipografia

`--fonte-base` · `--texto-xs` · `--texto-sm` · `--texto-md` · `--texto-lg` · `--texto-xl` ·
`--texto-2xl` · `--texto-3xl` · `--peso-normal` · `--peso-medio` · `--peso-forte` ·
`--altura-linha-apertada` · `--altura-linha-base`

### Espaçamento, forma e elevação

`--esp-1` … `--esp-8` · `--raio-sm` · `--raio-md` · `--raio-lg` · `--raio-pilula` ·
`--sombra-md` · `--sombra-lg`

### Movimento

`--transicao-rapida` · `--transicao-painel`

### Medidas

`--altura-painel` · `--largura-conteudo`

---

## Nomes novos

| Token | Categoria | Sem unidade? |
|---|---|---|
| `--texto-display` | tipografia | não |
| `--largura-display` | tipografia | **sim** — alimenta `font-variation-settings` |
| `--largura-normal` | tipografia | **sim** — idem |
| `--peso-display` | tipografia | sim, é número |
| `--espacamento-display` | tipografia | não |
| `--ritmo-dobra` | ritmo | não |
| `--ritmo-secao` | ritmo | não |
| `--cor-sobre-destaque` | cor | não |
| `--movimento-cartaz` | movimento | não |
| `--elevacao-cartaz` | movimento | não |
| `--curva-saida` | movimento | não |

Os tokens sem unidade são a única exceção da varredura de valores soltos — estão marcados porque,
sem isso, pareceriam violação.

---

## Regra de consumo

Um componente **só** pode referenciar token por `var(--nome)`.

**Proibido em qualquer arquivo que não seja `tokens.css`:**

- valor hexadecimal de cor, `rgb()`, `hsl()`
- `font-family`
- duração em `ms` ou `s`
- `px`, exceto largura de borda de 1px e deslocamento de contorno de foco

**Permitido fora dos tokens:**

- `%`, `vw`, `vh`, `fr`, `auto`, `1fr`
- `aspect-ratio`
- `rem` em medida derivada de conteúdo (largura de cartaz, altura de moldura), desde que **não**
  seja cor, tipografia, duração ou raio

A fronteira é: **vocabulário do sistema vem de token; geometria de um componente pode ser local.**
Um `--cartaz-largura-em-tablet` seria valor solto com nome bonito — token é vocabulário, não
esconderijo.

---

## Verificação

```bash
# SC-001 — cor literal fora dos tokens
grep -rn "#[0-9a-fA-F]\{3,8\}\|rgb(\|hsl(" frontend/components frontend/app --include="*.css" \
  | grep -v "var(--"

# SC-002 — família tipográfica fora dos tokens
grep -rn "font-family" frontend/components frontend/app --include="*.css"

# Duração literal fora dos tokens
grep -rn "transition:.*[0-9]\+m\?s\|animation:.*[0-9]\+m\?s" \
  frontend/components frontend/app --include="*.css" | grep -v "var(--"

# R6 — propriedades proibidas em animação
grep -rn "transition:.*\(width\|height\|top\|left\|margin\|background-position\)" \
  frontend/components frontend/app --include="*.css"
```

**Esperado**: nenhuma saída em nenhum dos quatro.

---

## O que este contrato NÃO cobre

Nenhum contrato de API muda. `GET /api/v1/highlights/`, `GET /api/v1/home/`,
`GET /api/v1/filmes/<slug>/`, `GET /api/v1/busca/` e as rotas de autenticação permanecem
**idênticos** — mesma forma, mesmos campos, mesmas regras (FR-026).
