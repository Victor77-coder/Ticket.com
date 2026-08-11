# Contract — Emenda ao limite de highlights

**Feature**: `005-seed-and-carousel-tuning` | **Date**: 2026-08-11

Esta feature **não cria endpoint**. Ela emenda um número no contrato de
`GET /api/v1/highlights/`, entregue pela feature 001.

---

## `GET /api/v1/highlights/` — o que muda

| Antes | Depois |
|---|---|
| `count` entre 0 e **5** | `count` entre 0 e **3** |

**Só isso.** A forma da resposta, os campos do painel, a ordenação, o cache e o comportamento com
catálogo vazio permanecem exatamente como especificados em
[`001-movie-highlights-carousel/contracts/highlights-api.md`](../../001-movie-highlights-carousel/contracts/highlights-api.md).

O cliente não precisa de nenhuma mudança: ele já renderiza `results` na ordem recebida e já lida
com qualquer quantidade entre 0 e o máximo. O indicador de posição do carrossel lê `count`, então
passa a mostrar "1 / 3" sozinho.

---

## O que **não** muda

- **`GET /api/v1/home/`** — a trilha **Em cartaz** não tem limite e continua listando todos os
  filmes com sessão comprável. Com o seed maior, ela passa a ter ~12 filmes contra os 3 do
  carrossel, que é o que o SC-004 exige.
- **Trilhas Em alta e Em breve** — inalteradas por esta feature. A trilha Em alta deve crescer
  como efeito colateral, porque três dos quatro filmes nomeados já estão marcados como em alta e
  passarão a ter sessão.
- **Campos proibidos** — a mesma lista do Princípio IV continua valendo nos dois endpoints.

---

## Verificação

```bash
curl -s http://localhost:8000/api/v1/highlights/ | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('count:', d['count'], '(máximo 3)')
for r in d['results']:
    print(' ·', r['title'])
"
```

**Esperado**: `count` no máximo 3, e os três títulos sendo A Odisseia, Homem-Aranha e Minions
depois de sincronizar e semear (SC-002).
