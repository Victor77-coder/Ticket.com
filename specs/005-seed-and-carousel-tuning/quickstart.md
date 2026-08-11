# Quickstart — Ajuste da Vitrine

**Feature**: `005-seed-and-carousel-tuning` | **Date**: 2026-08-11

Pressupõe o ambiente de pé — ver o [README](../../README.md) para o setup completo.

---

## 1. Sincronizar e semear

```bash
docker compose exec backend python manage.py sync_tmdb --limit 20
docker compose exec backend python manage.py seed_demo
```

O `sync_tmdb` precisa vir primeiro: o seed só enxerga filmes que já foram importados. Rodar o
seed com o catálogo vazio não quebra — ele avisa que os filmes nomeados não foram encontrados
(FR-011).

---

## 2. Conferir a vitrine pela saída do comando

O seed agora informa quais filmes ficaram no carrossel e quais entraram só na trilha (FR-014).
O esperado:

```
  no carrossel (sessão mais próxima):
    1. A Odisseia
    2. Homem-Aranha: Um Novo Dia
    3. Minions & Monstros
  também à venda:
    · Moana
    · … mais 8 filmes
```

**Isto é o SC-002**: a vitrine é conferível sem abrir o navegador.

---

## 3. Conferir pela API

```bash
curl -s http://localhost:8000/api/v1/highlights/ | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('carrossel:', d['count'], 'filmes (máximo 3)')
for r in d['results']: print('  ·', r['title'])
"
```

```bash
curl -s http://localhost:8000/api/v1/home/ | python3 -c "
import json, sys
for r in json.load(sys.stdin)['rows']:
    print(f\"{r['title']:<12} {r['count']:>2} filmes\")
"
```

**Esperado**: carrossel com 3; **Em cartaz** com ~12; **Em alta** e **Em breve** com conteúdo.

---

## 4. Verificações que valem a pena

### Moana está à venda mas fora do carrossel (SC-003)

```bash
docker compose exec backend python manage.py shell -c "
import json, urllib.request
destaque = json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/highlights/').read())
home = json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/home/').read())
cartaz = next(r for r in home['rows'] if r['key'] == 'em-cartaz')

titulos_destaque = [r['title'] for r in destaque['results']]
titulos_cartaz = [m['title'] for m in cartaz['movies']]

print('Moana no carrossel:', any('Moana' in t for t in titulos_destaque), '(esperado: False)')
print('Moana em Em cartaz:', any('Moana' in t for t in titulos_cartaz), '(esperado: True)')
"
```

### A trilha tem bem mais que o carrossel (SC-004)

```bash
docker compose exec backend python manage.py shell -c "
import json, urllib.request
d = json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/home/').read())
cartaz = next(r for r in d['rows'] if r['key'] == 'em-cartaz')['count']
destaque = json.loads(urllib.request.urlopen('http://localhost:8000/api/v1/highlights/').read())['count']
print(f'carrossel: {destaque} | Em cartaz: {cartaz} | razão: {cartaz/destaque:.1f}x (mínimo 2x)')
"
```

### Duas execuções produzem a mesma vitrine (SC-005)

```bash
docker compose exec backend python manage.py seed_demo | grep -A4 "no carrossel"
docker compose exec backend python manage.py seed_demo | grep -A4 "no carrossel"
```

**Esperado**: as duas saídas idênticas. Se a ordem variar, o desempate da busca por nome não está
determinístico (R2).

### Filme nomeado ausente não quebra o seed (SC-006)

```bash
docker compose exec backend python manage.py shell -c "
from apps.catalog.models import Movie
Movie.objects.filter(title__unaccent__icontains='moana').update(is_active=False)
print('Moana desativada')
"
docker compose exec backend python manage.py seed_demo | tail -20
```

**Esperado**: o comando conclui, avisa que Moana não foi encontrada, e a vitrine sai com os
demais. Reverter com `sync_tmdb` ou reativando o filme.

### O carrossel continua completo com 3 painéis

Abrir <http://localhost:5003> e conferir que, com três filmes:

- avançar do terceiro volta ao primeiro (navegação circular)
- a rotação automática funciona e pausa com o ponteiro sobre a área
- o botão Trailer aparece nos filmes que têm
- o indicador mostra "1 / 3"

---

## Problemas comuns

**O carrossel não tem os três filmes esperados** — provavelmente o `sync_tmdb` não trouxe algum
deles. A saída do seed diz quais não foram encontrados. Aumentar o `--limit` do sync pode
resolver.

**A ordem do carrossel muda entre execuções** — o desempate da busca por nome não está
determinístico. Deve ordenar por `-release_date, pk` e imprimir qual escolheu.

**Em cartaz tem só 4 ou 5 filmes** — o preenchimento além dos nomeados não rodou. Conferir se o
catálogo tem longas com arte suficientes; com catálogo pequeno o seed cai para critérios mais
frouxos, mas não inventa filmes.

**Em alta continua quase idêntica a Em cartaz** — esperado enquanto poucos filmes em alta tiverem
sessão. Com 12 à venda a sobreposição diminui, mas não desaparece: aquela trilha exige sessão
desde a emenda da feature 004, e isso é por decisão registrada.
