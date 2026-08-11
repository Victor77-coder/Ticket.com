# Quickstart — Identidade Visual

**Feature**: `006-visual-identity` | **Date**: 2026-08-11

Pressupõe o ambiente de pé com catálogo sincronizado e semeado — ver o
[README](../../README.md).

---

## 1. Ver

```bash
docker compose up -d
```

Abrir <http://localhost:5003>. O esperado, em relação à baseline:

- o título do filme em destaque é **largo e pesado**, ocupando a linha como cartaz
- há **respiro visível** entre o painel de destaques e a primeira trilha, maior que entre trilhas
- os cartazes estão **maiores e mais juntos**, lendo como parede em vez de grade
- as setas das trilhas **não têm mais o círculo com borda**

---

## 2. Verificar o que é automatizável

Estes quatro comandos cobrem SC-001, SC-002 e a regra dos 60fps. **Nenhum pode retornar linha.**

```bash
# Cor literal fora dos tokens
grep -rn "#[0-9a-fA-F]\{3,8\}\|rgb(\|hsl(" frontend/components frontend/app --include="*.css" \
  | grep -v "var(--"

# Família tipográfica fora dos tokens
grep -rn "font-family" frontend/components frontend/app --include="*.css"

# Duração literal fora dos tokens
grep -rn "transition:.*[0-9]\+m\?s\|animation:.*[0-9]\+m\?s" \
  frontend/components frontend/app --include="*.css" | grep -v "var(--"

# Propriedades que não podem ser animadas
grep -rn "transition:.*\(width\|height\|top\|left\|margin\|background-position\)" \
  frontend/components frontend/app --include="*.css"
```

### Sem texto de preenchimento (SC-010)

```bash
grep -rni "lorem\|placeholder\|coming soon\|em breve\.\.\.\|TODO\|FIXME" \
  frontend/app frontend/components --include="*.tsx" --include="*.css"
```

> "Em breve" como **nome de trilha** é conteúdo legítimo. O que se procura é a seção vazia
> prometendo funcionalidade futura.

### Teto de três movimentos (SC-004)

```bash
grep -rn "transition:.*transform\|animation:" frontend/components --include="*.css"
```

**Esperado**: elevação do cartaz, transição do painel e deslocamento da trilha. Mudança de cor ou
borda **não conta** — ver a distinção em R5 do `research.md`.

---

## 3. Verificar o comportamento congelado

```bash
docker compose exec frontend npm run test
```

**Esperado**: as mesmas 95 asserções passando, **sem nenhuma edição**. Se um teste precisou mudar,
a feature saiu do escopo visual (FR-030).

```bash
docker compose exec backend pytest -q
```

**Esperado**: 136 passando. O back-end não foi tocado.

---

## 4. Verificar o que exige olho

### Sem salto ao carregar a fonte (SC-006)

Abrir a home com o cache desativado nas ferramentas do navegador e recarregar. O texto **não pode
mudar de posição** depois de aparecer.

O ajuste por métrica do `next/font` é o que evita isso — se houver salto, a fonte está sendo
carregada por outro caminho.

### Movimento reduzido (SC-005)

Ativar a preferência do sistema e recarregar:

- macOS: Ajustes → Acessibilidade → Tela → Reduzir movimento
- Chrome DevTools: Rendering → Emulate CSS `prefers-reduced-motion: reduce`

**Esperado**: cartaz não eleva, carrossel troca sem deslizar, trilha salta direto. Nada anima.

### Teclado e foco (FR-028)

Percorrer a home só com Tab. **Esperado**: contorno de foco perceptível em cada alvo, na ordem
visual. O refino visual não pode ter tornado o foco sutil.

### Contraste sobre o véu (SC-007)

Com o inspetor, medir o contraste do título e do botão sobre a arte do filme, no painel de
destaques.

**Esperado**: igual ou melhor que a baseline. O véu **não** pode ter sido afinado para o título
ficar mais bonito.

### Sem rolagem horizontal (SC-011)

Estreitar até 360px e alargar até 1920px. A página nunca rola para o lado; só as trilhas.

---

## 5. A checagem de identidade (SC-003)

O único ponto de julgamento humano. Roteiro completo em
[contracts/anti-slop-review.md](./contracts/anti-slop-review.md).

Em resumo: capturar a primeira dobra, **recortar o cabeçalho inteiro**, e responder —

> Numa galeria ao lado de cinco catálogos de streaming, dava para apontar qual é o nosso?

---

## Problemas comuns

**O texto salta quando a fonte carrega** — a fonte não está passando pelo `next/font`, ou o
fallback perdeu o ajuste de métrica. Conferir se a família vem da variável CSS gerada.

**A varredura acusa `px`** — largura de borda de 1px e deslocamento de contorno de foco são
exceções documentadas no contrato de tokens. Qualquer outro `px` fora dos tokens é violação.

**O título do destaque não parece expandido** — o eixo `wdth` só responde se a fonte foi carregada
como variável **com o eixo declarado**. Sem declarar, chega só o corte padrão.

**Um teste de front-end falhou** — não ajuste a asserção. A feature congelou o comportamento
(FR-030); o teste falhando é o sinal de que a mudança visual atravessou para comportamento.

**O ritmo sumiu em tela estreita** — `--ritmo-dobra` e `--ritmo-secao` são fluidos e se aproximam
em telas pequenas por desenho. Se ficarem idênticos, os limites inferiores do `clamp` precisam
divergir mais.
