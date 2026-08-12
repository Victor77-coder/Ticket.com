# Quickstart — Meus Ingressos e Compartilhamento por Link

**Feature**: `009-my-tickets-sharing` | **Date**: 2026-08-12

Percorrer as três superfícies, **ler o QR com o celular de verdade**, **revogar um link ao vivo** e
conferir que o código do ingresso não mudou. Pressupõe o ambiente já de pé; ver o
[README](../../README.md) para o setup completo.

---

## Pré-requisitos

Esta feature **não introduz variável de ambiente nova** e **não traz dependência nova**. O token é
`secrets.token_urlsafe`, biblioteca padrão.

### 1. Subir e migrar

```bash
docker compose up -d
docker compose exec backend python manage.py migrate
```

A migração cria `TicketShareLink` e seu índice parcial — **os dois juntos**, mesma disciplina de 007
e 008.

### 2. Conferir que a constraint existe

Antes de qualquer outra coisa. É ela que impede dois links ativos para o mesmo ingresso:

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\d screening_ticketsharelink"
```

**Esperado**:

| Índice | Forma |
|---|---|
| `um_link_ativo_por_ingresso` | `UNIQUE (ticket_id) WHERE (revoked_at IS NULL)` |
| unicidade de `token` | `UNIQUE (token)` — **sem `WHERE`** |

A primeira **tem** predicado; a segunda **não pode ter**. Se a primeira estiver sem `WHERE`, gerar um
link depois de revogar o anterior vai falhar — que é justamente o que FR-032 promete ao dono. Se a
segunda tiver predicado, um token revogado pode ser reemitido, e FR-031 cai.

### 3. Ter um ingresso emitido

Se você ainda não comprou nada nesta base:

```bash
docker compose exec backend python manage.py seed_demo
```

Depois, entrar como `cliente1` (senha `desafio2026`), escolher uma sessão, reservar **dois** lugares e
pagar com `4242 4242 4242 4242`. Dois lugares, e não um, porque o cenário de compartilhamento da US4 é
"comprei para mim e para quem vai comigo".

---

## Percurso 1 — A área existe e ordena certo

1. Entrar como **`cliente1`**.
2. Abrir o menu da conta no cabeçalho → **Meus ingressos**.

**Esperado**:

- Os dois ingressos da compra aparecem, **um por lugar** — nunca um cartão só com um QR (FR-004).
- Cada um mostra filme, dia, hora, sala e lugar sem precisar clicar em nada (FR-005).
- Cada um tem seu **próprio** QR e seu próprio código, e os dois códigos são **diferentes**.

### O teste de ordenação, que precisa de mais de uma sessão

Compre também um ingresso para uma sessão **mais distante** e recarregue a lista.

**Esperado**: o ingresso da sessão que acontece **primeiro** está no topo (FR-007). Se a lista estiver
ordenada por poltrona (`A1`, `B4`, `F12`…) em vez de por horário, é o `Ticket.Meta.ordering` da 008
vazando — a lista precisa declarar a ordenação por sessão explicitamente (R10, corolário).

### O grupo dos passados

```bash
docker compose exec backend python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from apps.screening.models import Ticket
i = Ticket.objects.first()
s = i.reserved_seat.screening
s.starts_at = timezone.now() - timedelta(days=2)
s.save(update_fields=['starts_at'])
print('sessão movida para o passado:', s)
"
```

Recarregue a lista.

**Esperado**: o ingresso aparece no grupo **"já aconteceram"**, íntegro, com o QR (FR-009). A
distinção entre os dois grupos é visível **sem depender de cor** — há título de seção, não só um tom
mais apagado (FR-006).

**Se o ingresso sumiu**, é a armadilha herdada: alguma consulta desta feature está usando
`sellable()`, que exclui toda sessão já iniciada (R10). É o defeito que este passo existe para pegar.

### A sessão cancelada

```bash
docker compose exec backend python manage.py shell -c "
from apps.screening.models import Screening, Ticket
i = Ticket.objects.first()
s = i.reserved_seat.screening
s.status = Screening.Status.CANCELLED
s.save(update_fields=['status'])
print('sessão cancelada:', s)
"
```

**Esperado**: o ingresso **continua na lista**, com aviso em português de que a sessão foi cancelada
(FR-011). Se ele sumiu, é `sellable()` de novo — e é o pior caso, porque some justamente o ingresso
sobre o qual o cliente precisa de explicação.

> Desfazer: `docker compose exec backend python manage.py seed_demo` devolve a grade ao início.

---

## Percurso 2 — O estado vazio

Entrar como **`cliente2`** (que não comprou nada) e abrir **Meus ingressos**.

**Esperado**:

- Frase em português dizendo que ele ainda não tem ingressos e qual é a próxima ação (FR-012).
- Um caminho para o catálogo, a **uma** interação (SC-004).
- Nenhuma área em branco, nenhum "Nenhum resultado", nenhum ícone genérico.

E o contra-teste que importa: **quem só tem ingressos de sessões passadas não vê o estado vazio**
(FR-013). Se depois de mover a sessão para o passado no percurso anterior a lista de `cliente1`
mostrar "você ainda não tem ingressos", a condição do estado vazio está olhando só o grupo dos
futuros.

---

## Percurso 3 — Ler o QR com o celular *(verificação manual de SC-005)*

Este passo **não é automatizado**, e a razão está no plano: decodificar QR em teste exigiria uma
biblioteca nativa (`zbar` e afins) só para esta asserção. O automatizado cobre o que é estrutural
(SVG vetorial, tamanho mínimo renderizado, contraste do fundo, código em texto igual ao assinado); a
leitura por leitor de terceiro é conferida aqui, à mão.

1. Abrir **Meus ingressos** no navegador do desktop.
2. Estreitar a janela para **320px** de largura (DevTools → dispositivo → 320×568).
3. Pegar o celular, abrir a câmera ou um aplicativo leitor de QR **de terceiro** — não algo deste
   projeto — e apontar para a tela.

**Esperado**:

- O leitor decodifica de primeira, sem zoom manual (SC-005).
- O texto decodificado é **idêntico** ao que aparece em "Código para digitação" logo abaixo do QR.
  Se forem diferentes, a imagem parou de representar o código, e a portaria da próxima feature vai
  validar uma coisa enquanto a pessoa mostra outra.
- O QR mantém **fundo claro** mesmo no tema escuro. É decisão da 008, com token próprio
  (`--cor-fundo-qr`): leitor precisa do contraste entre módulo escuro e fundo claro, e inverter para
  combinar com o tema quebraria a leitura na catraca.

4. Repetir com a imagem do QR bloqueada (DevTools → Network → bloquear `data:` ou desabilitar
   imagens).

**Esperado**: o código continua visível em texto, inteiro, sem truncamento (FR-018, FR-019). É o que
a portaria digita quando a câmera falha.

---

## Percurso 4 — Gerar o link e abrir sem conta

1. Como `cliente1`, na lista, abrir **um** dos ingressos (`/meus-ingressos/<id>`).
2. Gerar o link e copiar.

**Esperado**: o endereço vem **completo** (`http://localhost:5003/ingresso/<token>`), pronto para
colar num aplicativo de mensagens (FR-024).

3. Pedir o link **de novo**, sem revogar.

**Esperado**: o **mesmo** endereço (FR-028). Se vier um segundo endereço diferente e os dois
funcionarem, existem duas credenciais ativas para o mesmo ingresso e a constraint não está fazendo
efeito.

4. Abrir o link numa **janela anônima**, ou em outro navegador, sem sessão nenhuma.

**Esperado**:

- O ingresso aparece, com **filme, sessão, sala, lugar e o QR** (FR-037).
- A página **não pede** para entrar e não tem caminho para a entrada (FR-036).
- O QR é lido pelo celular — é o mesmo ingresso, não uma imagem decorativa (US4-3).

5. Na mesma janela anônima, procurar o que **não** pode estar lá:

**Esperado — nada disso aparece** (FR-038 a FR-041):

- o nome ou e-mail de `cliente1`;
- o **outro** ingresso da mesma compra, nem link para ele;
- valor pago, bandeira, final do cartão;
- identificador de reserva, de pagamento ou o `public_id` do ingresso.

6. Ver o código-fonte da página (`Ctrl+U`) e conferir o mesmo — o vazamento pode estar num `<script>`
   de estado que não aparece na tela. É por isso que o teste de FR-042 inspeciona a resposta
   **inteira**, não o que está renderizado.

7. Conferir a instrução aos buscadores:

```bash
curl -s http://localhost:5003/ingresso/<token> | grep -i 'robots\|referrer'
```

**Esperado**: `noindex` e `no-referrer` (FR-044, R9). O endereço **é** a credencial: indexado, passa a
ser encontrável por quem nunca o recebeu.

---

## Percurso 5 — Revogar ao vivo, e o que NÃO pode mudar

Este é o percurso que prova a decisão 2 da spec — os dois segredos têm ciclos de vida separados.

1. **Antes de revogar**, anotar o código do ingresso (o texto sob "Código para digitação").
2. Como `cliente1`, no ingresso, **revogar** o link.
3. Voltar à janela anônima com o link antigo aberto e **recarregar**.

**Esperado**:

- A página **não exibe mais o ingresso** (FR-031).
- A mensagem é uma frase em português — "Este link não vale mais. Peça um novo a quem enviou o
  ingresso." — e **não** a 404 genérica do site (FR-052).
- A revogação vale **na primeira recarga**, sem esperar nada (SC-009). Se o link continuar abrindo, o
  banco está certo e o **cache** está servindo a credencial: falta `force-dynamic` na rota (R13). É a
  falha mais discreta da feature — nenhum teste de back-end a pegaria.

4. Comparar o **código do ingresso** com o que você anotou no passo 1.

**Esperado**: **idêntico** (FR-033, SC-010). Revogar um convite não pode queimar uma entrada paga. Se
o código mudou, os dois segredos foram fundidos em algum ponto, e a próxima feature valida na catraca
um código que o cliente não tem mais.

5. Inventar um token e abrir `http://localhost:5003/ingresso/eu-inventei-isso-aqui`.

**Esperado**: **exatamente a mesma tela** do link revogado (FR-043). Se as duas telas forem
diferentes, quem está adivinhando descobre quando um palpite chegou perto.

6. Gerar um link **novo** e conferir que o endereço é **diferente** do revogado (FR-032); abrir o
   revogado outra vez e conferir que continua morto (FR-031).

---

## Percurso 6 — Cada um só mexe no que é seu

Com o `<public_id>` de um ingresso de `cliente1` em mãos, e a sessão de **`cliente2`**, `organizador`
ou `portaria`:

```bash
# Entrar e guardar o cookie
curl -s -c /tmp/c2.txt -X POST http://localhost:8000/api/v1/auth/entrar/ \
  -H 'Content-Type: application/json' \
  -d '{"usuario":"cliente2","senha":"desafio2026"}'

# 1. Listar (deve trazer só os DELE, nenhum de cliente1)
curl -s -b /tmp/c2.txt http://localhost:8000/api/v1/meus-ingressos/

# 2. Abrir ingresso alheio  → 404
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/c2.txt \
  http://localhost:8000/api/v1/ingressos/<public_id_do_cliente1>/

# 3. Gerar link para ingresso alheio → 404, e NENHUM link é criado
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/c2.txt -X POST \
  http://localhost:8000/api/v1/ingressos/<public_id_do_cliente1>/link/

# 4. Revogar link alheio → 404, e o link continua ativo
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/c2.txt -X DELETE \
  http://localhost:8000/api/v1/ingressos/<public_id_do_cliente1>/link/
```

**Esperado**: `404` nos três — **não `403`**. Um `403` confirmaria que aquele `public_id` existe, e
`public_id` é exatamente o valor que vai dentro do código assinado do QR.

Repetir com `organizador` e `portaria`. **Esperado**: `403` com "Apenas clientes têm ingressos." — eles
entraram, só não têm ingressos. Um `401` os mandaria para a tela de entrada, que é caminho sem saída:
entrar de novo não muda o papel.

Sem cookie nenhum: `401` com "Entre para ver seus ingressos.".

**As chamadas acima batem no Django direto**, sem passar pela interface. É esse o ponto: esconder o
botão nunca é o controle de acesso (FR-050).

---

## Percurso 7 — A corrida, à mão

O teste automatizado (`test_share_link_concurrency.py`) é a prova. Para ver acontecer:

```bash
TOKEN_URL=http://localhost:8000/api/v1/ingressos/<public_id>/link/
for i in 1 2 3 4 5; do
  curl -s -b /tmp/c1.txt -X POST "$TOKEN_URL" &
done
wait
```

**Esperado**: as cinco respostas trazem o **mesmo** `endereco`. Uma delas terá vindo com `201` e as
demais com `200` — ou todas com `200`, dependendo de quem chegou primeiro.

Conferir no banco:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT count(*) FROM screening_ticketsharelink WHERE revoked_at IS NULL;"
```

**Esperado**: exatamente **1** por ingresso. Se aparecer mais de um, o índice parcial não está lá — e
a partir daí existem credenciais ativas que o dono vê uma e revoga uma, achando que revogou tudo.

---

## Percurso 8 — Com o TMDb fora do ar

```bash
docker compose exec backend sh -c 'TMDB_API_KEY=chave-invalida python -c "print(1)"'
```

Ou, mais direto: derrubar a rede do container do back-end para fora, ou apenas confiar em que
nenhuma destas rotas chama o TMDb.

1. Abrir **Meus ingressos**.
2. Abrir um ingresso.
3. Abrir a página compartilhada.

**Esperado**: as três funcionam **idênticas** (FR-014, FR-045, SC-017). Filme, sessão, sala e lugar
estão persistidos localmente desde a 001 — é o Princípio VII, e o caminho crítico não pode ficar
refém de terceiro durante a avaliação.

---

## A suíte

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
docker compose exec frontend npx playwright test
```

**Os quatro testes que esta feature não pode entregar sem**:

| Arquivo | O que prova | Falha se… |
|---|---|---|
| `test_share_link_leakage.py` | FR-042 — a resposta pública não contém nada da lista de proibidos | alguém acrescentar campo ao `TicketSerializer` |
| `test_share_link_concurrency.py` | FR-029 — pedidos simultâneos produzem **um** link ativo | o índice parcial for removido |
| `test_ticket_signature.py` (ampliado) | SC-010 — revogar não altera o código do QR | os dois segredos forem fundidos |
| `test_my_tickets_api.py` | FR-009/FR-011 — passado e sessão cancelada continuam na lista | alguma consulta usar `sellable()` |

O de concorrência precisa de `transaction=True`. Herdado da 007 e repetido na 008: sem transação
real, as threads compartilham conexão e o teste passa com ou sem a constraint — ou seja, prova nada.

> Rodar a suíte muitas vezes consome a grade semeada; `seed_demo` devolve o cenário ao início.

---

## O que NÃO existe nesta feature, de propósito

- **Nenhum estado "já utilizado"** no ingresso. A transição e a garantia de validação única nascem
  **juntas** na feature da portaria — mesma disciplina que criou `ReservedSeat` com sua constraint na
  007 e pagamento com emissão na 008. Um selo que nada escreve seria tela pela metade.
- **Nenhum prazo no link.** Vale até ser revogado.
- **Nenhum contador de aberturas.** Contar seria telemetria sobre quem recebeu o ingresso, e a feature
  existe para que essa pessoa não precise se identificar.
- **Nenhuma transferência de titularidade.** Compartilhar é exibir; o ingresso continua de quem
  comprou. Revenda está fora de escopo pelo Princípio I.
