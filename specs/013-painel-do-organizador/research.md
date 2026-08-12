# Research — Painel do Organizador

Onze decisões. Cada uma existe porque havia mais de um caminho plausível e o errado só apareceria
tarde.

---

## R1 — Onde passa a viver a regra do mapa físico da sala

**Decisão**: extrair para `backend/apps/screening/services/salas.py`, com duas funções puras e uma de
escrita:

```python
posicoes_da_sala(capacity, por_fileira=None) -> list[tuple[str, int]]
lugares_acessiveis(posicoes, cota=None) -> set[tuple[str, int]]
gerar_assentos(room) -> list[Seat]     # apaga e recria; exige zero ocupação
```

`seed_demo._seed_seats` e `_posicoes_da_sala` **deixam de conter a regra** e passam a chamar
`gerar_assentos`. O comando continua dono do reset do cenário; a geometria da sala não é mais dele.

**Racional**: a spec nomeia esta como a armadilha da feature (FR-017). Duas cópias da regra divergem
na primeira correção — e a correção mais provável é justamente a mais sutil: onde ficam os lugares
de acessibilidade quando a última fileira é menor que a cota. Hoje o `min(...)` que protege esse
caso mora numa linha só do seed.

**Alternativas consideradas**:
- *Copiar para o serviço do painel e deixar o seed como está* — é o que a spec proíbe por nome.
- *Método no modelo `Room`* (`room.gerar_assentos()`) — tentador, mas colocaria uma escrita
  destrutiva com pré-condição de ocupação dentro de um modelo que hoje é puro dado; a camada de
  serviço é onde o resto do projeto já põe operação com transação.
- *Manter no seed e o painel importar do comando de management* — importar de `management/commands`
  é acoplamento invertido: o comando é entrada, não biblioteca.

**Consequência testável**: `test_sala_paridade_seed.py` cria uma sala pelo serviço e outra com a
mesma capacidade pelo caminho do seed e compara fileira, número e tipo de cada lugar.

**Uma diferença que a extração NÃO deve apagar.** `_posicoes_da_sala` hoje faz
`total = min(capacity, teto)` — capacidade acima de 260 é **truncada em silêncio**. FR-018 manda o
painel **recusar**. As duas coisas convivem, e a fronteira é:

- `posicoes_da_sala()` é **geometria pura** e continua truncando. É o que mantém o seed funcionando
  sem mudança de comportamento, e o que impede a função de precisar levantar exceção.
- A **recusa** é validação de entrada e mora no serializer da sala, antes de chamar a geometria.

Confundir as duas faria o seed passar a estourar por um valor que ele hoje aceita — regressão numa
feature que declara não mexer no cenário de demonstração além da confirmação destrutiva. E é por
isso que `lugares` e `capacidade` podem divergir numa sala **do seed** e nunca numa sala do painel.

---

## R2 — O que é persistido ao escolher um filme no TMDb

**Decisão**: `catalog/services/programacao_filmes.importar_filme(tmdb_id)` chama
`TMDBClient.movie_detail(tmdb_id)` e entrega o payload a `sync_movie(detalhe)` — o **mesmo**
mapeamento da sincronização de catálogo — com `is_trending=False` e `is_upcoming=False`.

**Racional**: `movie_detail` já usa `append_to_response=videos,release_dates`, então uma única
requisição traz metadados, trailers e classificação indicativa. Reusar `sync_movie` é literalmente
menos código que escrever uma persistência reduzida, e é o que impede um filme de segunda classe:
a 012 construiu as abas **Sobre** e **Trailers** em cima de gêneros, classificação e `Trailer`
(FR-011a).

`sync_movie` já faz `movie.is_trending = movie.is_trending or is_trending` — passar `False` **não
desmarca** um filme que já estava em alta. Importante: reimportar um filme do catálogo pelo painel
não pode rebaixá-lo na home.

**Alternativas consideradas**:
- *Persistência mínima (título, pôster, duração, sinopse)* — rejeitada na clarificação; deixaria
  Sobre e Trailers vazios só para os filmes trazidos pelo painel.
- *Marcar o filme importado como "em cartaz"* — rejeitada: as trilhas da home são decididas pela
  sincronização de catálogo, e programar é operação de grade, não curadoria de vitrine (FR-046).

---

## R3 — Como buscar filme no TMDb

**Decisão**: acrescentar um método ao `TMDBClient`, sem tocar em `_get`:

```python
def search_movies(self, query, page=1):
    return self._get("/search/movie", {"query": query, "page": page, "include_adult": False})
```

Uma página de resultados por busca; sem paginação infinita. Cada resultado é serializado com
`tmdb_id`, título, ano, pôster e **`ja_no_catalogo`** — booleano resolvido por uma consulta única
`Movie.objects.filter(tmdb_id__in=[...])`, não uma por linha.

**Racional**: `_get` já concentra chave, idioma, timeout e a tradução de erro para `TMDBError` em
pt-BR. Todo o comportamento que FR-009 e FR-014 pedem vem de graça — inclusive as frases de
timeout e de chave recusada, que já existem escritas para o organizador.

**Alternativas consideradas**:
- *Buscar no TMDb pelo navegador* — proibido pelo Princípio VII e por FR-010.
- *Paginação infinita* — o objetivo é achar um filme para programar, não navegar o catálogo
  mundial. Uma página mantém o estado vazio ("nada encontrado para este termo") legível.
- *`include_adult=True`* — sem propósito no domínio e traria resultado que a interface teria de
  filtrar depois.

---

## R4 — Conflito de (sala, horário): quem recusa

**Decisão**: tentar o INSERT/UPDATE dentro de `transaction.atomic()` e capturar `IntegrityError`,
identificando a constraint pelo **nome** `uma_sessao_por_sala_e_horario`. A frase bonita — que nomeia
sala e horário — é montada no `except`, e só ali.

```python
try:
    with transaction.atomic():
        screening = Screening.objects.create(...)
except IntegrityError as exc:
    if "uma_sessao_por_sala_e_horario" in str(exc):
        raise ConflitoDeHorario(sala, inicio) from exc
    raise
```

**Racional**: FR-025 e SC-004. `if Screening.objects.filter(room=..., starts_at=...).exists()` antes
do INSERT é o padrão que a concorrência quebra — as duas requisições verificam, nenhuma encontra,
ambas gravam. Este projeto já rejeitou esse padrão três vezes (007, 008, 009) e o comentário de
`Reservation.idempotency_key` o descreve por escrito.

O `transaction.atomic()` **interno** é obrigatório e não decorativo: sem ele, a transação inteira
fica marcada como inutilizável depois do `IntegrityError` e qualquer consulta seguinte estoura
`TransactionManagementError` — o `except` não conseguiria nem montar a mensagem.

**Alternativas consideradas**:
- *Validação no serializer com `UniqueTogetherValidator`* — pode ficar **em adição**, para dar erro
  de campo no caminho feliz, mas nunca como a garantia. O teste de concorrência é o que separa uma
  da outra.
- *Comparar por `str(exc)` sem o nome da constraint* — frágil; a mensagem do PostgreSQL muda entre
  versões e locales. O nome da constraint é nosso e está no modelo.

**Consequência testável**: `test_programacao_concorrencia.py` dispara duas criações simultâneas da
mesma `(sala, horário)` e prova que exatamente uma vence — o mesmo formato dos testes de
concorrência das 007/008/010.

---

## R5 — Trocar a capacidade de uma sala

**Decisão**: a operação é `salas.alterar_capacidade(room, nova)` e faz, nesta ordem, dentro de uma
transação:

1. lê ocupação viva de **todas** as sessões da sala via `selectors.ocupacoes_vivas()` filtrada por
   `screening__room=room`, e recusa se houver qualquer linha;
2. apaga os `Seat` da sala e recria com `gerar_assentos`.

`Seat` é PROTECT em `ReservedSeat.seat`, então o passo 2 falharia sozinho se o passo 1 errasse — a
recusa explícita existe para dar **frase**, não para dar garantia.

**Racional**: FR-020 e FR-021. "Ocupação viva" tem dois termos (paga **ou** não vencida) e mora em
`Reservation.OCUPANDO`; o comentário do modelo explica que ela já esteve escrita três vezes e foi
consolidada. Redefini-la aqui reabriria exatamente o erro que aquele comentário registra.

Reserva **vencida e não paga** não bloqueia: o lugar não está ocupado, e é a mesma leitura que o
mapa de assentos usa.

**Alternativas consideradas**:
- *Preservar os assentos existentes e só acrescentar/remover a diferença* — parece mais gentil e é
  pior: com zero ocupação não há nada a preservar, e a lógica incremental teria de decidir quais
  lugares de acessibilidade migram — uma segunda regra de geometria, que R1 existe para evitar.
- *Confiar só no PROTECT* — daria `ProtectedError` cru, que viola o Princípio V (mensagem escrita
  para o usuário final).
- *Bloquear a troca sempre* — mais simples, mas a spec pede a troca quando não há ocupação (FR-019).

---

## R6 — A grade do painel sem N+1

**Decisão**: `selectors.grade_do_organizador()` devolve as sessões com
`select_related("movie", "room")` e anota a ocupação com um `Count` sobre `reserved_seats` filtrado
por `Reservation.OCUPANDO` — uma consulta, não uma por sessão.

**Racional**: `Screening.seats_taken` é uma property que consulta o banco por instância. Correta
para uma sessão (é como o mapa a usa), desastrosa para uma grade de dezenas. A regra continua a
mesma — o `Q` de `OCUPANDO` é reusado dentro do `filter` da agregação, não reescrito.

**Alternativas consideradas**:
- *Chamar `seats_taken` na serialização* — N+1 silencioso; funciona no cenário do desafio e é o tipo
  de coisa que a revisão final acha e não dá tempo de consertar.
- *Materializar um contador em `Screening`* — proibido pela mesma razão que o modelo já registra:
  ocupação é valor derivado, nunca coluna.

---

## R7 — Onde mora a permissão de organizador

**Decisão**: `backend/apps/accounts/permissions.py` com `IsOrganizer`, mais subclasses só para trocar
a frase, seguindo o padrão que `screening/permissions.py` já estabeleceu (`IsCustomer`,
`IsCustomerParaPagar`, `IsCustomerParaIngressos`).

```python
class IsOrganizer(BasePermission):
    message = "Apenas organizadores programam sessões."
```

**Racional**: a programação atravessa dois apps — filme é `catalog`, sala e sessão são `screening`.
A permissão é de **papel**, não de domínio: `accounts` é onde o papel é definido. Duas classes
idênticas em dois apps seria a decisão de autorização morando em dois lugares, que é o erro que o
Princípio IV existe para fechar.

E continua `403`, nunca `401` — cliente e portaria **entraram**, só não programam. O comentário de
`IsCustomer` já explica por que confundir os dois códigos manda o front para um caminho sem saída.

**Alternativas consideradas**:
- *`IsAdminUser` do DRF* — o seed marca o organizador com `is_staff=True`, então funcionaria por
  acidente. Rejeitada: acopla autorização de produto ao flag do admin do Django, e um cliente
  promovido a staff por qualquer motivo ganharia a programação inteira.
- *Checagem inline em cada view* — esconde a regra e não dá frase por operação.

---

## R8 — Superfície de API: prefixo e verbos

**Decisão**: tudo sob `/api/v1/programacao/`, com transições de estado como **ações**, não como
`PATCH status`:

```
GET    /api/v1/programacao/filmes/                    catálogo local, para escolher
GET    /api/v1/programacao/filmes/busca/?q=           busca no TMDb (back-end)
POST   /api/v1/programacao/filmes/                    { tmdb_id } → importa e devolve o filme
GET    /api/v1/programacao/salas/                     nome, capacidade, lugares, ocupação
POST   /api/v1/programacao/salas/                     { nome, capacidade }
PATCH  /api/v1/programacao/salas/<id>/                { nome?, capacidade? }
GET    /api/v1/programacao/sessoes/                   a grade, todos os estados
POST   /api/v1/programacao/sessoes/                   { filme, sala, inicio, preco, publicar }
PATCH  /api/v1/programacao/sessoes/<id>/              só rascunho
POST   /api/v1/programacao/sessoes/<id>/publicar/
POST   /api/v1/programacao/sessoes/<id>/cancelar/
```

**Racional**: o prefixo torna a regra de autorização legível de fora — tudo sob `programacao/` exige
organizador, e um endpoint novo nasce coberto por estar ali. Publicar e cancelar como ações
carregam pré-condições próprias (horário futuro; sala com lugares) que um `PATCH status=published`
esconderia dentro de validação de campo.

**Alternativas consideradas**:
- *ViewSets + router do DRF* — o projeto inteiro usa `APIView` explícita; introduzir router aqui
  criaria dois estilos de roteamento sem ganho.
- *`DELETE /sessoes/<id>/`* — apagar sessão está fora de escopo; cancelar é a saída (FR-030).

---

## R9 — O seed que passa a recusar

**Decisão**: `seed_demo` ganha `--force`. Sem a flag, se `Screening.objects.exists()`, o comando
**não** executa: escreve o que seria apagado (quantas sessões, reservas e ingressos) e como
prosseguir. Com a flag, o comportamento é exatamente o de hoje.

**Racional**: FR-041 a FR-044. Sem marcador de origem — que FR-042 proíbe criar — não há como
distinguir a sessão do seed da sessão do painel, então a leitura é conservadora: qualquer sessão
conta como perda possível. A primeira execução, em base vazia, não vê nada disso.

`_reset_demo_state` **não muda por dentro**. A ordem de remoção (ingresso → pagamento → reserva →
sessão) continua obrigatória por causa dos PROTECT, e o comentário que a explica continua válido.

**Alternativas consideradas**:
- *Perguntar interativamente* — quebraria execução não interativa, que é como o comando roda em
  script e em CI.
- *Preservar seletivamente* — exige a coluna de origem. Registrado em Complexity Tracking.

---

## R10 — `CASA_DO_PAPEL`: um fato vira dois

**Decisão**: o registro passa a ser `{ href, rotulo, pousa, telaUnica }`.

| Papel | `pousa` | `telaUnica` | Leitura |
|---|---|---|---|
| `customer` | `false` | `false` | circula pelo site; pousa no catálogo porque entra para comprar |
| `gate` | `true` | `true` | pousa na portaria e não alcança mais nada |
| `organizer` | `true` | `false` | **pousa** no painel, mas o catálogo público continua aberto |

`destinoAposEntrada` passa a consultar `pousa`; `devolverParaCasa` e `temTelaUnica` continuam
consultando `telaUnica` e **não mudam de comportamento** — o middleware segue negando por padrão só
para quem tem tela única.

**Racional**: FR-002 e FR-004. O organizador precisa conferir no catálogo público que a sessão que
publicou apareceu à venda; registrá-lo com `telaUnica: true` o trancaria fora dela. O docstring
atual afirma que os três fatos "andam juntos de propósito" — essa afirmação era verdadeira enquanto
só a portaria existia, e o organizador é o contraexemplo que a divide. A tabela continua **uma**.

**Alternativas consideradas**:
- *Reusar `telaUnica: true`* — quebra FR-004 e o organizador perde a home.
- *Reusar `telaUnica: false` e tratar o pouso na página de entrada* — devolveria a decisão de
  destino para fora da tabela, que é exatamente o vazamento que o docstring diz já ter acontecido
  duas vezes neste projeto.

---

## R11 — Recusa por papel na tela, sem esconder botão

**Decisão**: `/programacao` repete o padrão de `/portaria`: sem cookie → `redirect("/entrar?next=…")`;
`401` → mesma coisa; **`403` → painel de recusa renderizado**, com frase própria e link de volta ao
catálogo. Os proxies em `app/api/programacao/**` repassam status e corpo **sem alteração**.

**Racional**: FR-008, FR-033 e FR-037. A distinção entre `401` e `403` é a mesma que a 009 e a 010 já
aplicam: quem entrou e tem o papel errado não pode ser mandado para a entrada, porque entrar de novo
não muda o papel — caminho sem saída. E a tela de recusa existe **porque** a autorização é do
servidor: ela é a apresentação de um `403` real, não um botão escondido.

**Alternativas consideradas**:
- *Bloquear no middleware por papel* — o middleware é produto, não segurança, e negar `/programacao`
  para cliente ali daria a impressão errada de que a proteção está no front.
- *Redirecionar o papel errado para a home* — apagaria a informação de por que ele não entrou.
