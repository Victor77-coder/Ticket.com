# Quickstart — Validação de Ingressos na Portaria

**Feature**: `010-gate-validation` | **Date**: 2026-08-12

Percorrer a portaria, **provocar os quatro desfechos de propósito**, **forjar um código** e
reproduzir a corrida à mão. Pressupõe o ambiente já de pé; ver o [README](../../README.md) para o
setup completo.

---

## Pré-requisitos

Esta feature **não introduz variável de ambiente nova**. Traz **uma dependência nova** no front-end e
**uma migração**.

### 1. Subir, instalar e migrar

```bash
docker compose up -d --build frontend
docker compose exec backend python manage.py migrate
```

O `--build` é necessário: `jsQR` entrou em `package.json`. Sem ele, a leitura por câmera não carrega
— e a digitação manual continua funcionando, o que é exatamente o ponto dela.

A migração acrescenta **só a coluna** de uso ao ingresso. **É a primeira migração da série sem uma
constraint junto**, e a ausência é decisão registrada: o invariante desta feature é de transição, não
de coexistência, e nenhum índice o expressa. Ver `data-model.md`.

### 2. Conferir que a coluna existe e está vazia

```bash
docker compose exec db psql -U ingressos -d ingressos -c "\d screening_ticket" | grep used_at
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT count(*) FILTER (WHERE used_at IS NULL) AS nao_usados, count(*) AS total FROM screening_ticket;"
```

**Esperado**: a coluna aparece como `timestamp with time zone`, nulável, e todos os ingressos já
emitidos estão não utilizados. Nenhum ingresso antigo pode nascer marcado.

### 3. Ter um ingresso para validar

Entrar como `cliente1` (senha `desafio2026`), comprar **dois** lugares numa sessão de hoje e abrir
**Meus ingressos**. Copie o **código em texto** de um deles — é o mesmo que vai dentro do QR, e é o
que a digitação manual aceita.

> Se não houver sessão hoje na grade semeada, rode
> `docker compose exec backend python manage.py seed_demo` e confira em `/portaria` quais sessões
> aparecem.

---

## Percurso 1 — Abrir o posto e escolher a sessão

1. Sair da conta de cliente e entrar como **`portaria`** (senha `desafio2026`).
2. Abrir `http://localhost:5003/portaria`.

**Esperado**:

- A tela **não** pede código ainda. Ela explica, em português, que é preciso escolher qual sessão
  esta porta está recebendo, e lista as sessões do dia (FR-002, FR-003).
- A lista **inclui sessões que já começaram** (US1-1). Se as sessões em andamento sumiram, alguma
  consulta está usando o filtro de vendabilidade — é a armadilha da 009 voltando, e este passo existe
  para pegá-la.
- Sessões canceladas **não** aparecem.

3. Escolher a sessão da compra do `cliente1`.

**Esperado**: a tela passa ao estado de leitura, e filme, horário e sala da sessão escolhida ficam
visíveis o tempo todo (FR-004).

4. Recarregar a página.

**Esperado**: a sessão escolhida **continua escolhida** (FR-006). Trocar de porta é decisão do
operador, não efeito de recarregar.

---

## Percurso 2 — Os quatro desfechos, um por um

Todos pela **digitação manual**, que está sempre visível (FR-010). A leitura por câmera é o percurso
5, e é manual.

### **Válido**

Cole o código do ingresso do `cliente1` e confirme.

**Esperado**:

- Título grande dizendo que **pode entrar**, com o **lugar** (FR-020).
- Legível a um braço de distância, sem ler texto pequeno (FR-019, SC-004).
- O símbolo e o título distinguem o desfecho **sem depender de cor** (FR-017).

### **Já utilizado**

Cole **o mesmo código** de novo.

**Esperado**:

- **Já utilizado**, com o **instante** do primeiro uso (FR-021).
- Repita mais duas vezes: o instante **nunca muda** (FR-033).
- O desfecho é distinguível de **inválido** sem ler o texto inteiro (US4-5) — são situações
  diferentes e exigem reações diferentes do operador.

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT public_id, used_at FROM screening_ticket WHERE used_at IS NOT NULL ORDER BY used_at DESC LIMIT 3;"
```

**Esperado**: exatamente um registro para aquele ingresso, com o instante da **primeira** validação.

### **Sessão errada**

Troque a sessão da porta para **outra** sessão do dia e cole o código do **segundo** ingresso do
`cliente1` (o que ainda não foi usado).

**Esperado**:

- **Sessão errada**, informando **a qual sessão** aquele ingresso pertence — filme, horário e sala
  (FR-022).
- O ingresso **não** foi marcado:

```bash
docker compose exec db psql -U ingressos -d ingressos -c \
  "SELECT count(*) FROM screening_ticket WHERE used_at IS NULL;"
```

Volte a sessão da porta para a correta e valide o mesmo código.

**Esperado**: **válido**. A recusa anterior não consumiu o ingresso (US6-4, FR-031). Se aqui vier
"já utilizado", o passo de sessão errada está escrevendo — e um ingresso legítimo foi queimado na
porta errada.

### **Inválido**

Cole um código adulterado — o mesmo de antes com **um caractere trocado**:

```bash
CODIGO='<cole aqui o código de um ingresso>'
echo "${CODIGO%?}X"
```

**Esperado**: **inválido**, com frase que deixa claro que **não é para deixar entrar**.

Repita com um código inventado do zero (`abc:def:ghi`) e com um código assinado por outro segredo:

```bash
docker compose exec backend python manage.py shell -c "
from django.core import signing
falso = signing.Signer(key='chave-de-atacante', salt='ingresso.qr').sign('eyJzIjoxLCJ0IjoiMDAwMDAwMDAtMDAwMC0wMDAwLTAwMDAtMDAwMDAwMDAwMDAwIn0')
print(falso)
"
```

**Esperado**: os três produzem o **mesmo** desfecho **inválido**, com a **mesma** frase. Se algum
deles disser algo diferente, quem tenta adivinhar descobre onde chegou perto (FR-029).

---

## Percurso 3 — O campo vazio não é "inválido"

Com a sessão escolhida, confirme com o campo de código **vazio**.

**Esperado**: aviso de **preenchimento**, distinto de **inválido** (FR-014). Nada foi apresentado —
dizer "ingresso não reconhecido" faria o operador procurar defeito no ingresso da pessoa.

Cole um código com espaços e quebra de linha nas pontas.

**Esperado**: aceito normalmente (FR-013).

---

## Percurso 4 — Só a portaria valida

```bash
# cliente1
curl -s -c /tmp/c1.txt -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' -d '{"username":"cliente1","password":"desafio2026"}' -o /dev/null

curl -s -o /dev/null -w 'cliente listar sessoes: %{http_code}\n' -b /tmp/c1.txt \
  http://localhost:8000/api/v1/portaria/sessoes/

curl -s -o /dev/null -w 'cliente validar: %{http_code}\n' -b /tmp/c1.txt -X POST \
  http://localhost:8000/api/v1/portaria/validar/ \
  -H 'Content-Type: application/json' -d "{\"codigo\":\"$CODIGO\",\"sessao\":272}"
```

**Esperado**: `403` nos dois, com "Apenas a portaria valida ingressos.". Repita com o organizador —
mesmo resultado. Sem cookie nenhum: `401`.

**E o mais importante**: rode a validação como `cliente1` contra um ingresso **dele mesmo** e confira
no banco que `used_at` continua nulo. Um cliente marcando o próprio ingresso como usado é a falha que
esta recusa previne.

Abra `/portaria` no navegador autenticado como `cliente1`.

**Esperado**: uma explicação de que aquela área é da portaria — e **não** um redirecionamento para a
entrada (FR-041). Entrar de novo não muda o papel; o caminho não teria saída.

---

## Percurso 5 — A câmera *(verificação manual)*

Este passo **não é automatizado**: apontar uma câmera para um QR real exige hardware. O automatizado
cobre o resto — o mesmo código, entregue por digitação, produz o mesmo desfecho (SC-010), e o e2e
percorre a tela inteira pela via digitada.

1. Abra `/portaria` em **`http://localhost:5003`** e autorize a câmera.
2. Abra "Meus ingressos" do `cliente1` em outro aparelho (ou imprima o QR) e aponte a câmera.

**Esperado**:

- O desfecho aparece em até 3 segundos (SC-002).
- **Deixe o QR parado na frente da câmera por dez segundos.** Aquela apresentação produz **um único**
  desfecho (FR-015, SC-012). Se a tela mostrar "válido" e logo em seguida "já utilizado", o laço de
  leitura está disparando várias validações — o sistema está correto e a portaria vê uma
  contradição.

3. Negue a permissão da câmera (nas configurações do navegador) e recarregue.

**Esperado**: frase em português explicando que a leitura por câmera não está disponível e apontando
a digitação, **sem área em branco** (FR-011). O campo de digitação continua onde estava — ele nunca
esteve escondido atrás da falha.

> **Limitação real, e ela vai para o README**: `getUserMedia` exige contexto seguro. `localhost`
> conta; **o IP da rede local não**, e nenhuma configuração da aplicação muda isso. Quem abrir a
> portaria pelo celular via IP da rede — que é o gesto natural para testar — **não terá câmera**, e a
> digitação manual é o caminho. A exigência da constitution que parecia redundante é justamente a que
> mantém a portaria funcionando no cenário mais provável de demonstração.

---

## Percurso 6 — A corrida, à mão

O teste automatizado (`test_gate_concurrency.py`) é a prova. Para ver acontecer, com um ingresso
**ainda não utilizado**:

```bash
# Entrar como portaria e guardar o cookie
curl -s -c /tmp/porta.txt -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' -d '{"username":"portaria","password":"desafio2026"}' -o /dev/null

CODIGO='<código de um ingresso NÃO utilizado>'
SESSAO=272

for i in 1 2 3 4 5; do
  curl -s -b /tmp/porta.txt -X POST http://localhost:8000/api/v1/portaria/validar/ \
    -H 'Content-Type: application/json' \
    -d "{\"codigo\":\"$CODIGO\",\"sessao\":$SESSAO}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["situacao"])' &
done
wait
```

**Esperado**: exatamente **um** `valido` e quatro `ja_utilizado`. Se aparecer mais de um `valido`, a
marcação virou leitura seguida de escrita — e a portaria deixa passar dois com o mesmo ingresso.

---

## Percurso 7 — Com o TMDb fora do ar

Nenhuma rota desta feature chama o TMDb: filme, sessão, sala e assento estão persistidos localmente
desde a 001, e a assinatura é verificada localmente.

1. Abrir `/portaria` e escolher a sessão.
2. Validar um código.

**Esperado**: as duas coisas funcionam **idênticas** (FR-008, SC-014).

---

## A suíte

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
cd frontend && npx playwright test --workers=2
```

**Os três testes que esta feature não pode entregar sem**:

| Arquivo | O que prova | Falha se… |
|---|---|---|
| `test_gate_concurrency.py` | Princípio III — uma validação por ingresso | a escrita condicional virar leitura-e-escrita |
| `test_gate_signature.py` | Princípio III — forjado rejeitado sem tocar o registro | alguém consultar o banco antes de conferir a assinatura |
| `test_gate_api.py` | os quatro desfechos, a ordem entre eles, e quem não escreve | "sessão errada" passar a consumir o ingresso |

### A verificação que prova que a prova prova

**Esta é a mais importante da feature**, porque aqui não há constraint para remover. Troque o
`UPDATE` condicional pelo `if` natural:

```python
# EM services/portaria.py — TEMPORARIAMENTE, para verificar o teste
if ingresso.used_at is not None:
    return JA_UTILIZADO
ingresso.used_at = timezone.now()
ingresso.save(update_fields=["used_at"])
return VALIDO
```

Rode `test_gate_concurrency.py`.

**Esperado**: ele **falha**, com mais de um `valido`. Restaure em seguida.

Se ele **passar** com esse código, o teste não está provando nada — provavelmente falta
`transaction=True`, e as threads estão compartilhando conexão. É a mesma armadilha herdada da 007 e
repetida na 008 e na 009, e aqui ela é fatal: sem constraint, o teste é a **única** coisa que
protege a garantia.

> Os testes ponta a ponta desta feature **marcam ingressos como usados**, e uso é definitivo. Rodar a
> suíte muitas vezes consome os ingressos da grade semeada; `seed_demo` devolve o cenário ao início.

---

## O que NÃO existe nesta feature, de propósito

- **O cliente não vê "utilizado".** "Meus ingressos" e a página compartilhada continuam como a 009 as
  entregou. O campo passa a existir aqui; exibi-lo ao cliente é decisão de outra feature.
- **Nenhum registro de qual operador validou.** Seria auditoria, e nenhum dos quatro desfechos
  depende disso.
- **Nenhum contador de leituras nem telemetria.**
- **Nenhum modo offline.** Validar offline exigiria decidir o uso no aparelho e reconciliar depois, e
  reconciliação é exatamente onde a validação única se perde.
- **Nenhum quinto desfecho.** Sessão cancelada é informação **dentro** de "sessão errada".
