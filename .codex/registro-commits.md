# Registro de commits

- 2026-08-13 10:29:59 | branch `main` | sha `8efa7bd` | mensagem `feat(vitrine): troca o backdrop escuro da odisseia por still mais clara`
  arquivos: `backend/apps/catalog/services/tmdb_sync.py`, `backend/tests/test_tmdb_sync.py`
- 2026-08-13 10:30:05 | branch `main` | sha `24c8799` | mensagem `feat(vitrine): tira o contador e reposiciona as setas do carrossel`
  arquivos: `frontend/components/highlights/CarouselControls.tsx`, `frontend/components/highlights/HighlightsCarousel.tsx`, `frontend/components/highlights/highlights.module.css`, `frontend/tests/carousel.test.tsx`, `frontend/tests/e2e/highlights.spec.ts`, `frontend/tests/trailer.test.tsx`
- 2026-08-13 10:30:11 | branch `main` | sha `964da51` | mensagem `feat(deploy): sobe front, api e postgres juntos no render`
  arquivos: `.env.example`, `.gitignore`, `backend/apps/catalog/management/commands/bootstrap_demo.py`, `backend/config/health.py`, `backend/config/settings/prod.py`, `backend/config/urls.py`, `backend/pyproject.toml`, `backend/tests/test_bootstrap_demo.py`, `backend/tests/test_health.py`, `frontend/app/saude/route.ts`, `frontend/lib/api.ts`, `frontend/middleware.ts`, `frontend/package-lock.json`, `frontend/package.json`, `render.yaml`
- 2026-08-13 10:30:30 | branch `main` | sha `7d9e3ff` | mensagem `docs(deploy): explica como publicar o sistema no render`
  arquivos: `README.md`
- 2026-08-13 10:36:00 | branch `main` | sha `563914f` | mensagem `fix(deploy): move migrate e seed para o start no plano free`
  arquivos: `backend/start.sh`, `render.yaml`
- 2026-08-13 10:42:34 | branch `main` | sha `ac0310d` | mensagem `fix(deploy): instala deps via requirements e abre a porta antes do tmdb`
  arquivos: `backend/requirements.txt`, `backend/start.sh`, `render.yaml`
- 2026-08-13 10:43:12 | branch `main` | sha `eecb005` | mensagem `fix(deploy): instala typescript no build mesmo com node_env=production`
  arquivos: `render.yaml`
- 2026-08-13 10:49:05 | branch `main` | sha `29fbcf3` | mensagem `fix(deploy): aceita DATABASE_URL sem exigir POSTGRES_DB`
  arquivos: `backend/config/settings/base.py`, `backend/config/settings/prod.py`, `render.yaml`
- 2026-08-13 13:10:39 | branch `main` | sha `450a564` | mensagem `fix(home): recarrega sozinha enquanto a api do render acorda`
  arquivos: `frontend/app/page.tsx`, `frontend/components/RecarregarAoAcordar.tsx`, `frontend/lib/api.ts`
- 2026-08-13 13:40:29 | branch `main` | sha `eda85ad` | mensagem `fix(deploy): next fala na rede interna e o navegador acorda a api`
  arquivos: `README.md`, `backend/config/health.py`, `frontend/components/RecarregarAoAcordar.tsx`, `render.yaml`
- 2026-08-13 14:24:26 | branch `main` | sha `9b4b489` | mensagem `fix(deploy): web free não recebe rede interna; para o loop de refresh`
  arquivos: `README.md`, `frontend/components/RecarregarAoAcordar.tsx`, `render.yaml`
