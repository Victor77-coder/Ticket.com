# Quickstart — Painel do Organizador

Como subir, como percorrer, e como provar que a feature fez o que promete **sem** ter quebrado o que
já existia.

## Subir

```bash
docker compose up -d                      # PostgreSQL
cd backend && python manage.py migrate    # nenhuma migração nova nesta feature
python manage.py sync_tmdb --limit 20     # catálogo local (precisa de TMDB_API_KEY no .env)
python manage.py seed_demo                # 1ª vez: roda direto. Depois: exige --force
python manage.py runserver                # :8000

cd ../frontend && npm run dev             # :5003
```

Credenciais do cenário — senha `desafio2026` para todas:

| Papel | Usuário | Pousa em |
|---|---|---|
| Organizador | `organizador` | **`/programacao`** ← novo |
| Cliente | `cliente1`, `cliente2` | `/` (catálogo) |
| Portaria | `portaria` | `/portaria` |

## O caminho principal — 2 minutos, sem terminal (SC-001)

1. Entre como `organizador`. **Você deve cair em `/programacao`**, não no catálogo.
2. Programe uma sessão com um filme que já está no catálogo, uma sala do seed, horário para daqui a
   algumas horas, preço `30,00`, e escolha **publicar**.
3. Abra a home num navegador anônimo (ou saia). Encontre o filme, abra a página dele: **o horário que
   você acabou de criar está lá**.
4. Compre até o ingresso, com `cliente1`. Cartão de teste do README.

Se o passo 3 exigiu rodar qualquer comando, a feature falhou em SC-002.

## O caminho do TMDb (US3)

1. Em `/programacao`, programe uma sessão e busque um filme **que não está no catálogo** — algo fora
   das 20 primeiras entradas do `sync_tmdb`.
2. Escolha um resultado. O filme é persistido localmente.
3. Abra a página pública do filme: **Sobre e Trailers têm conteúdo**. Se estiverem vazias, a
   importação usou um mapeamento reduzido — falha de FR-011a.
4. Abra a home: o filme **não** está em "Em alta" nem em "Em breve" (FR-046).

**Prova de que o TMDb não é dependência do fluxo crítico** (Princípio VII):

```bash
# no .env do backend, quebre a chave e reinicie
TMDB_API_KEY=chave-invalida
```

Agora: a busca do painel mostra a frase do TMDb em português; **programar com filme local, criar
sala, publicar e cancelar continuam funcionando**; e comprar, ver ingresso e validar na portaria não
mudam em nada.

## O caminho das salas (US4)

1. `/programacao/salas` → crie "Sala 3" com capacidade `45`.
2. Programe uma sessão nela e abra o mapa pelo fluxo do cliente: 4 fileiras de 10 e uma quinta com 5;
   os **3 últimos lugares da última fileira** são de acessibilidade.
3. Tente capacidade `0` → recusa com frase. Tente `300` → recusa informando o teto de 260.
4. Reserve um lugar nessa sala (como cliente, sem pagar) e volte a `/programacao/salas`: trocar a
   capacidade agora é **recusado**, com frase que diz quantos lugares estão ocupados.
5. Espere a reserva vencer (10 min) ou apague-a; a troca volta a ser permitida.

## O caminho da grade (US5)

1. Programe uma sessão como **rascunho**. Confirme que ela **não** aparece para o cliente.
2. Edite o rascunho — troque horário e preço. Continua rascunho.
3. Publique. Passa a aparecer.
4. Tente editá-la agora: **recusa** com frase que manda cancelar e programar outra.
5. Cancele. Deixa de aparecer para compra.
6. Se alguém já tinha comprado: o ingresso continua em "Meus ingressos" do cliente, e na portaria
   continua dando o mesmo desfecho de antes (FR-031).

## As três provas de recorte

Nenhuma delas é opcional — são o que separa esta feature de ter reaberto o que já estava fechado.

### 1. Negação por papel é do servidor

```bash
# como cliente1, direto na API, sem passar pelo front
curl -i -X POST localhost:8000/api/v1/programacao/sessoes/ \
  -H 'Content-Type: application/json' -b 'sessionid=<cookie do cliente1>' \
  -d '{"filme":1,"sala":1,"inicio":"2026-09-01T20:00:00-03:00","preco":"30.00","publicar":true}'
```

Esperado: **`403`**, com "Apenas organizadores programam sessões." — não `401`, não `302`, não `200`.
Repita com o cookie da `portaria`. Os dois casos estão em `test_programacao_permissoes.py`.

### 2. O conflito de horário é do banco

```bash
cd backend && pytest tests/test_programacao_concorrencia.py -v
```

Duas criações simultâneas da mesma `(sala, horário)`: exatamente uma vence. Se este teste passar
mas houver um `exists()` antes do INSERT em `services/programacao.py`, a garantia é falsa — o teste
prova o resultado, a revisão de código prova o caminho (R4).

### 3. Nada de esquema mudou

```bash
cd backend && python manage.py makemigrations --check --dry-run
```

Esperado: nenhuma migração pendente. Esta feature escreve no banco sem tocar no esquema; qualquer
coluna nova é escopo escorregando (data-model.md).

## O que NÃO pode ter mudado

Rode a suíte inteira — mas estes são os pontos que quebram primeiro se o recorte falhou:

```bash
cd backend && pytest                       # incluindo os testes de concorrência das 007/008/010
cd frontend && npm test && npm run test:e2e
```

| Superfície | Como conferir |
|---|---|
| Home, carrossel, trilhas, busca | `test_highlights_api.py`, `test_home_rows_api.py`, `test_search_api.py`, `rows.test.tsx`, `carousel.test.tsx` — **sem edição** |
| Serializers públicos | Nenhum ganhou `status`, `capacity`, contagem de vendidos ou `tmdb_id` |
| Mapa de assentos e reserva | `test_reservation_concurrency.py`, `seats.test.tsx` — intocados |
| Pagamento e ingresso | `test_payment_concurrency.py`, `test_ticket_signature.py` — intocados |
| Portaria | `test_gate_concurrency.py`, `portaria.test.tsx` — intocados; a portaria **continua** com tela única |
| Cliente pousa no catálogo | `destinoAposEntrada("customer", "/") === "/"` — a regressão mais provável do campo `pousa` |

## O seed, agora

```bash
python manage.py seed_demo        # base vazia: roda. Com grade existente: RECUSA e explica
python manage.py seed_demo --force  # apaga tudo e recria — comportamento de sempre
```

A recusa não é bug. Sem marcador de origem, o comando não sabe distinguir a sessão que ele criou da
que você programou pelo painel, então trata as duas como perda possível (FR-041, FR-042). A primeira
execução, em base vazia, nunca vê o aviso — é o caminho do avaliador.
