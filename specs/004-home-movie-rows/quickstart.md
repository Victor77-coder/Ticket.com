# Quickstart — Trilhas de Filmes na Home

**Feature**: `004-home-movie-rows` | **Date**: 2026-08-11

Pressupõe o ambiente de pé — ver o [README](../../README.md) para o setup completo.

---

## 1. Migrar e sincronizar

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py sync_tmdb --limit 20
docker compose exec backend python manage.py seed_demo
```

O `sync_tmdb` agora importa **três** listas do TMDb — em cartaz, em alta da semana e estreias
futuras — e marca cada filme com o que ele é. O `--limit` vale **por lista**, então `--limit 20`
traz até 60 filmes, menos as repetições entre listas.

Conferir a distribuição:

```bash
docker compose exec backend python manage.py shell -c "
from apps.catalog.models import Movie
from django.utils import timezone
print('catálogo:  ', Movie.objects.count())
print('em alta:   ', Movie.objects.filter(is_trending=True).count())
print('em breve:  ', Movie.objects.filter(is_upcoming=True, release_date__gt=timezone.now().date()).count())
"
```

---

## 2. Ver as trilhas

Abrir <http://localhost:5003>. Abaixo do painel de destaques, o esperado:

1. **Em cartaz** — filmes com sessão à venda, o mais próximo primeiro
2. **Em alta** — no máximo **9** cartazes
3. **Em breve** — estreias futuras, a mais próxima primeiro

Conferir a resposta direta:

```bash
curl -s http://localhost:8000/api/v1/home/ | python3 -c "
import json, sys
for r in json.load(sys.stdin)['rows']:
    print(f\"{r['title']:<12} {r['count']:>2} filmes\")
"
```

---

## 3. Verificações que valem a pena

### Nenhuma trilha vazia é exibida (FR-006, SC-008)

```bash
docker compose exec backend python manage.py shell -c "
from apps.catalog.models import Movie
Movie.objects.update(is_trending=False)
print('trilha Em alta esvaziada')
"
```

Recarregar a home: a seção **Em alta** desaparece por inteiro — não fica um título com espaço
vazio embaixo. Rodar `sync_tmdb` de novo a traz de volta.

### A página não rola horizontalmente (SC-005)

Estreitar a janela até 360px e conferir que só as trilhas rolam para o lado, nunca a página.

> Esta é a armadilha do padrão: `overflow-x` só contém o transbordo se o contêiner pai tiver
> `min-width: 0` dentro de grid ou flex. Sem isso o conteúdo empurra a largura da página.

### As setas só aparecem quando há transbordo (FR-014)

Alargar a janela até todos os cartazes de uma trilha caberem. As setas daquela trilha somem —
seta permanentemente desabilitada é ruído que sugere conteúdo que não existe.

### Tudo alcançável por teclado (SC-006)

Percorrer a home só com Tab: cada cartaz recebe foco visível, na ordem visual, e a trilha
acompanha o foco.

### Resiliência ao TMDb (SC-004)

```bash
docker compose exec backend env TMDB_API_KEY= python manage.py check
```

Recarregar a home: as três trilhas continuam completas. Só a **atualização** da classificação
depende do TMDb; a exibição não.

### Filme sem sessão (FR-024 a FR-027)

Acionar um cartaz da trilha **Em breve**. A página deve ter a composição completa — cartaz,
título, sinopse, duração, classificação, gênero — e a mensagem:

> **Estreia em 13/08/2026**
> No momento, este filme não possui sessões programadas.

Um filme sem data de estreia conhecida mostra **apenas** a segunda linha. Um filme com data no
passado e sem sessão, também — anunciar estreia numa data vencida seria informação errada.

---

## 4. Testes

```bash
docker compose exec backend pytest tests/test_home_rows_api.py tests/test_tmdb_sync.py
docker compose exec frontend npm run test
```

Ponta a ponta, a partir do host (a imagem é Alpine e os navegadores do Playwright são glibc):

```bash
cd frontend && npx playwright test e2e/home-rows.spec.ts
```

---

## Problemas comuns

**Trilhas Em alta e Em breve vazias** — o catálogo foi importado antes desta feature e os campos
de classificação nasceram `False`. Rodar `sync_tmdb` novamente resolve.

**A página inteira rola para o lado** — falta `min-width: 0` no contêiner pai da trilha. Ver a
armadilha em R1 do `research.md`.

**Em breve mostra filme que já estreou** — a consulta precisa exigir `release_date > hoje`
**além** da marca. Só a marca deixa o filme preso na trilha até a próxima sincronização.

**Em alta nunca esvazia** — a sincronização precisa zerar `is_trending` em todos os filmes antes
de remarcar. Sem isso, quem entrou uma vez fica para sempre.

**O carrossel mostra filme estranho** — o `seed_demo` passou a preferir filmes em cartaz com arte
e duração acima de 60 minutos. Se ainda aparecer um curta ou um show, o catálogo importado tem
poucos filmes de cinema; aumentar o `--limit` do `sync_tmdb`.
