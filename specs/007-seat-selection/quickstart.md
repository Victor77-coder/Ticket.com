# Quickstart — Escolha de Assentos

**Feature**: `007-seat-selection` | **Date**: 2026-08-11

Percorrer o mapa da sala e a reserva, e — o que mais importa aqui — **reproduzir a corrida à mão**
para ver a constraint agindo. Pressupõe o ambiente já de pé; ver o [README](../../README.md) para
o setup completo.

---

## Pré-requisitos

```bash
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py sync_tmdb --limit 20
docker compose exec backend python manage.py seed_demo
```

Esta feature **introduz migração** — `Seat`, `Reservation`, `ReservedSeat` e a constraint, os
quatro na mesma. Rodar `migrate` não é opcional aqui.

`seed_demo` passa a gerar os assentos das salas. Sem rodá-lo de novo, o mapa abre vazio.

### Conferir que a constraint existe

Antes de qualquer outra coisa. É ela que a feature inteira existe para criar:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\d screening_reservedseat"
```

**Esperado**: entre os índices, `unico_assento_por_sessao` como `UNIQUE (screening_id, seat_id)`.
**Sem predicado `WHERE`** — se houver um, é a versão errada (R1).

---

## Contas

Senha **`desafio2026`** em todas:

| Papel | Usuário | Nesta feature |
|---|---|---|
| Cliente | `cliente1` | reserva |
| Cliente | `cliente2` | o outro lado da corrida |
| Organizador | `organizador` | **deve receber recusa** |
| Portaria | `portaria` | **deve receber recusa** |

---

## 1. Chegar ao mapa

1. Abrir <http://localhost:5003>.
2. Abrir um filme do carrossel — **A Odisseia**, **Homem-Aranha** ou **Minions** têm sessões.
3. Na lista de sessões, acionar um horário.
4. **Esperado**: o mapa da sala, com a tela indicada no topo, fileiras A em diante, e o corredor
   entre o quinto e o sexto lugar.

**SC-001**: uma interação da sessão até o mapa. Se precisar de duas, o critério falhou.

## 2. Os quatro estados

Olhar o mapa e localizar cada um:

| Estado | Onde |
|---|---|
| Livre | maioria dos lugares |
| Selecionado | acionar um livre |
| Tomado | aparece depois do passo 3 — ou reservando por `cliente2` primeiro |
| Acessibilidade | três lugares na **última** fileira |

**A verificação que vale**: olhar o mapa **em escala de cinza** (ferramentas do navegador →
Rendering → Emulate vision deficiencies → Achromatopsia). Os quatro continuam distinguíveis?
Se dois viram a mesma coisa, FR-008 falhou.

Para repetir a conferência sem abrir as ferramentas à mão, com a aplicação no ar:

```bash
cd frontend && node tests/e2e/acromatopsia.mjs <id-da-sessao> /tmp/mapa
```

Gera `/tmp/mapa-cor.png` e `/tmp/mapa-cinza.png`. **A comparação entre os dois é a verificação** —
a captura em cor sozinha não diz nada sobre FR-008. A sessão escolhida precisa ter lugar tomado,
senão o estado 3 não entra na imagem.

### Resultado medido — 2026-08-11 (SC-007)

Sessão com um lugar selecionado, dois tomados e três de acessibilidade, em acromatopsia:

| Estado | Como se lê sem cor |
|---|---|
| Livre | contorno claro, número visível |
| Selecionado | preenchimento claro + marca de conferido escura |
| Tomado | preenchimento escuro + traço diagonal, sem número |
| Acessibilidade | contorno **tracejado** + silhueta recortada |

Os quatro continuam distinguíveis. **Nenhum par depende de cor para se separar.**

> **Armadilha da medição, encontrada aqui**: a primeira captura pegou o lugar selecionado **no
> meio da transição** de cor e ele apareceu quase apagado — o que parecia violação de FR-008 era
> o obturador rápido demais. O script espera a transição terminar antes de capturar. Se a
> verificação for feita à mão, selecionar o lugar e **esperar** antes de olhar.

Acionar um lugar **tomado**: nada acontece, e o motivo aparece. Acionar um de **acessibilidade**:
idem, com o motivo próprio dele.

## 3. Reservar

1. Entrar como `cliente1`.
2. Selecionar dois lugares livres.
3. Conferir que o resumo mostra **quantidade e total**.
4. Confirmar.
5. **Esperado**: reserva criada, com os lugares nomeados (A1, A3…), até quando vale, e um caminho
   claro para o pagamento.

**Nenhum ingresso é emitido** (FR-029). O caminho para o pagamento leva à feature seguinte.

## 4. O que o outro cliente vê

Em janela anônima, entrar como `cliente2` e abrir **o mesmo mapa**.

**Esperado**: os lugares do `cliente1` constam como **tomados** — e **sem dizer de quem são**. O
mapa nunca nomeia quem ocupou.

## 5. Seleção parcialmente tomada

1. Com `cliente2`, selecionar um lugar livre **e** um dos que o `cliente1` pegou (ainda visível
   como livre se o mapa foi aberto antes).
2. Confirmar.
3. **Esperado**: **nenhum** dos dois é reservado, e a mensagem nomeia qual causou a recusa.

Se o livre for reservado e o outro não, FR-019 falhou — reservar "o que sobrou" entrega algo
diferente do que a pessoa escolheu.

## 6. Visitante

1. Sem sessão ativa, abrir o mapa direto pela URL.
2. **Esperado**: a sala aparece normalmente (FR-010).
3. Selecionar e confirmar.
4. **Esperado**: conduzido a `/entrar`, com o motivo. Ao entrar, volta **ao mesmo mapa**.

## 7. Papéis que não compram

Entrar como `organizador` e tentar reservar. Depois `portaria`.

**Esperado**: recusa nos dois casos. E a recusa tem de vir do **servidor** — botão escondido não
conta:

```bash
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://localhost:8000/api/v1/reservas/ \
  -H 'Content-Type: application/json' \
  -b "sessionid=<sessão do organizador>" \
  -d '{"sessao":1,"assentos":[101],"chave_idempotencia":"11111111-1111-4111-8111-111111111111"}'
```

**Esperado**: `403`. Um `201` aqui é violação de FR-025, mesmo com a interface impecável.

## 8. Envio duplo

Repetir o `curl` do passo anterior — como `cliente1`, com **a mesma** `chave_idempotencia` — duas
vezes.

**Esperado**: `201` na primeira, `200` na segunda, **com o mesmo `id` de reserva**. Duas reservas
distintas violam FR-023.

---

## Reproduzir a corrida à mão

O ponto alto. Duas reservas do **mesmo lugar**, ao mesmo tempo, de clientes diferentes.

Guardar os cookies de sessão dos dois clientes primeiro:

```bash
curl -s -c /tmp/c1.txt -X POST http://localhost:5003/api/entrar \
  -H 'Content-Type: application/json' -d '{"username":"cliente1","password":"desafio2026"}'
curl -s -c /tmp/c2.txt -X POST http://localhost:5003/api/entrar \
  -H 'Content-Type: application/json' -d '{"username":"cliente2","password":"desafio2026"}'
```

Descobrir uma sessão vendável e um assento livre pelo próprio mapa:

```bash
curl -s http://localhost:8000/api/v1/sessoes/1/mapa/ | python3 -m json.tool | head -40
```

Disparar as duas ao mesmo tempo — o `&` é o que importa:

```bash
SESSAO=1; ASSENTO=101

curl -s -o /tmp/r1.json -w 'cliente1 %{http_code}\n' -b /tmp/c1.txt \
  -X POST http://localhost:5003/api/reservar -H 'Content-Type: application/json' \
  -d "{\"sessao\":$SESSAO,\"assentos\":[$ASSENTO],\"chave_idempotencia\":\"$(uuidgen)\"}" &

curl -s -o /tmp/r2.json -w 'cliente2 %{http_code}\n' -b /tmp/c2.txt \
  -X POST http://localhost:5003/api/reservar -H 'Content-Type: application/json' \
  -d "{\"sessao\":$SESSAO,\"assentos\":[$ASSENTO],\"chave_idempotencia\":\"$(uuidgen)\"}" &

wait
```

**Esperado**: um `201` e um `409`. Nunca dois `201`.

E a prova que não depende da resposta HTTP:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT screening_id, seat_id, count(*) FROM screening_reservedseat
   GROUP BY 1,2 HAVING count(*) > 1;"
```

**Esperado**: `(0 rows)`. Qualquer linha aqui é o Princípio II quebrado — e não deveria ser
possível, porque a constraint recusaria a inserção antes.

> Dois `curl` do host não garantem colisão real: o disparo tem *jitter* de milissegundos e um pode
> terminar antes do outro começar. Se os dois derem `201` em **assentos diferentes**, a corrida não
> aconteceu — repita. **A prova formal é o teste automatizado**, com barreira sincronizando as duas
> threads no ponto crítico; o exercício manual serve para ver o `409` com os próprios olhos.

### Resultado medido — 2026-08-11

```
cliente1 409
cliente2 201
```

`cliente1` recebeu `O lugar A1 acabou de ser reservado por outra pessoa. Escolha outro.` com
`assentos_indisponiveis: [{"fileira": "A", "numero": 1}]`. A consulta de duplicatas devolveu
`(0 rows)`.

### O que esta caminhada manual pegou e nenhum teste pegava

Na primeira execução, **`cliente1` e `cliente2` receberam `403` "Apenas clientes podem reservar
lugares."** — dois clientes legítimos, recusados por papel. Não era papel: era **CSRF**.

A `SessionAuthentication` do DRF exige o par `csrftoken`/`X-CSRFToken` em toda escrita, e o Next
chama servidor-a-servidor, sem token nenhum. A falha vinha como `PermissionDenied`, indistinguível
da recusa por papel.

Os 27 testes de API passavam porque o `Client()` do Django marca a requisição com
`_dont_enforce_csrf_checks`, e a `SessionAuthentication` respeita a marca. **A suíte inteira
concordava com uma rota que recusava o proxy em produção.**

Corrigido com `SessionAuthenticationSemCsrf` em `apps/accounts/authentication.py` — mesma decisão
que a `003` já tinha registrado em R1 e aplicado no login. E o teste que faltava,
`test_reserva_funciona_com_a_checagem_de_csrf_ligada`, usa `Client(enforce_csrf_checks=True)`:
verificado que ele **falha com `403`** se o autenticador padrão voltar.

---

## A expiração

Não dá para ver acontecer: o prazo é de 10 minutos e não é configurável — decisão registrada em
[spec.md](./spec.md#limitação-assumida-da-demonstração). Esperar parado dez minutos não é
demonstração.

O que dá para fazer é forçar o vencimento no banco:

```bash
docker compose exec backend python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from apps.screening.models import Reservation
r = Reservation.objects.latest('created_at')
r.expires_at = timezone.now() - timedelta(minutes=1); r.save()
print('vencida:', r.id)
"
```

Recarregar o mapa: os lugares dela voltam a constar **livres**, e `cliente2` consegue reservá-los
(FR-021). A linha antiga só é removida quando alguém tenta aquele assento — sob bloqueio, dentro
da transação (R2).

O comportamento é provado por `tests/test_reservation_api.py`, não por demonstração.

---

## Testes

```bash
docker compose exec backend pytest tests/test_seat_map_api.py tests/test_reservation_api.py
docker compose exec backend pytest tests/test_reservation_concurrency.py
docker compose exec frontend npm run test
```

### Linha de base — antes da feature 007

Medida em 2026-08-11, com a `006` fechada e a árvore limpa. É contra estes números que SC-012
é verificado no fim: nenhuma asserção das features 001–006 pode mudar nem falhar.

| Suíte | Asserções |
|---|---|
| Back-end (`pytest`) | **141 passed** |
| Front-end (`vitest`) | **97 passed** em 6 arquivos |

> O `vitest` também acusa **1 unhandled error** pré-existente — `el.scrollBy is not a function`
> em `components/rows/MovieRow.tsx:59`, porque o jsdom não implementa `scrollBy`. Vem da `004`,
> não desta feature, e está registrado aqui para não ser atribuído à `007` no fim.

### Contagem final — com a 007 fechada

| Suíte | Antes | Depois | Diferença |
|---|---|---|---|
| Back-end (`pytest`) | 141 passed | **202 passed** | +61, nenhuma falha |
| Front-end (`vitest`) | 97 passed em 6 arquivos | **116 passed** em 7 arquivos | +19, nenhuma falha |

Nenhuma asserção das features 001–006 mudou de texto nem de resultado (SC-012, FR-033, FR-034).
O `unhandled error` do `scrollBy` continua exatamente um, e continua vindo da `004`.

### Provar que o teste de concorrência testa alguma coisa

Um teste de concorrência verde é fácil de conseguir sem provar nada (R4). A verificação:

1. comentar a `UniqueConstraint` em `apps/screening/models.py`
2. gerar e aplicar a migração
3. rodar `tests/test_reservation_concurrency.py`

**Esperado: FALHA.** Se passar, o teste não está exercitando concorrência — provavelmente as duas
threads estão compartilhando a conexão da transação de teste, e ele passaria com ou sem a
garantia.

Desfazer a alteração e a migração depois.

### Resultado medido — 2026-08-11

Executado durante a implementação, com a constraint comentada e a migração de remoção aplicada:

```
6 failed, 2 passed in 2.58s
```

| Teste | Sem a constraint |
|---|---|
| `duas_reservas_simultaneas_do_mesmo_lugar_uma_so_vence` | **FALHOU** — as duas venceram |
| `a_corrida_nao_deixa_duplicata_no_banco` | **FALHOU** — duas ocupações do mesmo lugar |
| `corrida_sobre_lugar_com_reserva_vencida` | **FALHOU** |
| `corrida_com_selecao_sobreposta_nao_reserva_pela_metade` | **FALHOU** |
| `insercao_direta_de_duplicata_e_recusada_pelo_banco` | **FALHOU** — o banco aceitou |
| `a_constraint_existe_no_banco_com_este_nome` | **FALHOU** |
| `lugares_diferentes_nao_se_atrapalham` | passou (não depende da constraint) |
| `mesma_chave_em_duas_threads_cria_uma_reserva_so` | passou (depende da outra constraint) |

**O achado que merece registro**: `corrida_sobre_lugar_com_reserva_vencida` também falhou — e é
o teste que exercita o caminho do **bloqueio**, não o da constraint. Isso mostra que nem o
`SELECT FOR UPDATE` basta sozinho: a segunda transação trava a linha vencida, mas quando a
primeira a apaga e comita, o que a segunda tinha travado deixou de existir e ela segue para
inserir. Sob *read committed*, a constraint é o árbitro final **também** no caminho do bloqueio.

É exatamente o que R3 previu, agora com medida em vez de argumento.

Migração de remoção desfeita e apagada em seguida; `showmigrations` de volta a `0002`, e a
constraint conferida no banco.

---

## Problemas comuns

**O mapa abre vazio** — os assentos não foram gerados. Rodar `seed_demo` de novo.

**O teste de concorrência passa em qualquer configuração** — falta `transaction=True`; as threads
estão na mesma transação e na mesma conexão. Ver R4.

**Reserva criada e o mapa continua mostrando o lugar livre** — provável cache de rota no Next.
A página do mapa não pode ser estática.

**`IntegrityError` chegando como 500** — a violação de unicidade é resultado **esperado** e deve
virar `409` com frase própria (R3). Como `500` ela vira erro genérico, o que também quebra FR-031.

**Os dois `curl` da corrida dão `201`** — pegaram assentos diferentes, ou um terminou antes do
outro começar. Conferir que `$ASSENTO` é o mesmo nos dois e repetir.
