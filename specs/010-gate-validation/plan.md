# Implementation Plan: Validação de Ingressos na Portaria

**Branch**: `main` — sem branch própria, como nas 003–009 | **Date**: 2026-08-12 |
**Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-gate-validation/spec.md`

## Summary

Ler o código do ingresso na entrada — pela câmera ou digitado — e responder com um de quatro
desfechos inequívocos, marcando o uso de forma que ninguém entre duas vezes. É a **etapa 5** da
ordem de construção obrigatória, e depois dela o fluxo ponta a ponta existe inteiro.

**A garantia muda de forma pela primeira vez, e é a decisão que estrutura o plano.** As três
features anteriores fecharam invariantes com índices — `UNIQUE` absoluta na 007, parcial na 008 e na
009. Aqui o invariante é de **transição**, não de coexistência: "esta coluna só sai de nulo uma
vez". Nenhum índice expressa isso. A garantia é um `UPDATE` condicional atômico, e **o número de
linhas afetadas é o desfecho** — `1` é válido, `0` é já utilizado.

**E é justamente aí que mora a armadilha desta feature.** Nas três anteriores, quem pegava o erro
era o banco: a constraint recusava e o teste via a recusa. Aqui **não há constraint para recusar**.
O código que qualquer pessoa escreve primeiro —

```python
if ingresso.used_at is not None:
    return JA_UTILIZADO
ingresso.used_at = timezone.now(); ingresso.save()
```

— é leitura seguida de escrita, passa em todo teste de uma thread só, **lê exatamente como a regra
escrita na spec**, e deixa duas pessoas entrarem com o mesmo ingresso sem que nada no banco
reclame. A única coisa entre o projeto e uma portaria furada é o teste de concorrência, e por isso
ele vem antes do serviço.

**Metade do trabalho já existe.** A 008 emitiu o código assinado, verifica a assinatura em módulo
puro sem tocar o banco, e pôs a identidade da sessão dentro do conteúdo assinado registrando que era
"para que a portaria possa distinguir 'sessão errada' de 'inválido' na feature seguinte". Esta
feature consome tudo isso. Nenhum formato novo, nenhuma chave nova.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 + DRF · Next.js 15 · `qrcode` (008, reaproveitada) ·
**`jsQR` (nova, JavaScript puro, sem dependências transitivas)** — justificada em R6 e em
Complexity Tracking

**Storage**: PostgreSQL 16. **Uma** migração acrescenta `used_at` ao ingresso. Não há constraint
nova: a garantia é a forma da escrita, e o motivo está em R1

**Testing**: `pytest` + `pytest-django` com **transações reais e threads** para a corrida de
validação, e `django_assert_num_queries(0)` em volta do **serviço** para provar que a assinatura é
rejeitada sem tocar o registro de ingressos · Vitest + Testing Library · Playwright

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`. A câmera exige
contexto seguro — `localhost` serve, IP de rede local não (R7)

**Performance Goals**: desfecho em ≤ 3 s da apresentação do código · o laço de leitura não pode
disparar mais de uma validação por apresentação

**Constraints**: nenhuma asserção das features 001–009 removida ou enfraquecida · o formato do
código e a chave de assinatura da 008 **não** mudam — há ingressos emitidos · o estado de uso **não**
aparece nas telas do cliente · disciplina de tokens da 006 · validação funciona com o TMDb fora do ar

**Scale/Scope**: uma porta por vez, dezenas de validações por sessão. A unicidade da validação
precisa valer sob concorrência real

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | Fecha a **etapa 5**, a última da ordem obrigatória — depois dela o caminho catálogo → sessão → assento → pagamento → ingresso → entrada existe inteiro. Sessão não escolhida, câmera negada, campo vazio, lista sem sessões e recusa por papel têm cada um estado próprio em pt-BR. Nada da lista de fora de escopo é construído. |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | Esta feature não toca assento, reserva nem pagamento. A única escrita é o instante de uso, e a unicidade dela é imposta pelo banco por escrita condicional atômica — não por checagem prévia na aplicação. Teste de concorrência obrigatório, que precisa **falhar** se a escrita virar leitura-e-escrita. |
| **III. Ingresso Inforjável e Validação Única (NÃO NEGOCIÁVEL)** | ✅ PASS | É a feature que fecha a segunda metade do princípio. A assinatura é conferida **antes de qualquer consulta ao registro de ingressos**, reusando o módulo puro da 008. A validação é atômica e idempotente: a primeira leitura marca, as seguintes respondem "já utilizado" sem alterar estado. Os quatro desfechos existem e são distinguíveis sem ambiguidade. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Só papel portaria abre a tela e valida; cliente e organizador recebem `403` **do servidor**. A portaria continua sem comprar, reservar ou pagar. Teste de acesso cruzado obrigatório. |
| **V. Interface Autoral** | ✅ PASS | Os quatro desfechos se distinguem por **símbolo e título**, com a cor como quarto sinal (R13) — mesma disciplina que o mapa de assentos aplica às poltronas. Câmera negada, campo vazio e ausência de sessões têm frase própria dizendo o que houve e a próxima ação. Tokens da 006 preservados. |
| **VI. Rastro de Decisão** | ✅ PASS | README ganha a tela, o modelo de sessão da porta, a dependência nova e — obrigatoriamente — a limitação do contexto seguro da câmera (R7). Quatorze decisões em research.md. |
| **VII. Isolamento da API Externa** | ✅ PASS | A validação lê só o banco local e verifica a assinatura localmente. Filme, sessão e sala estão persistidos desde a 001; nenhuma chamada ao TMDb entra neste caminho. |

### O ponto que exige julgamento: a garantia sem constraint

O Princípio II exige que garantias sejam aplicadas "no banco de dados, não apenas na aplicação", e
as três features anteriores cumpriram isso com índices. Esta não tem índice, e a diferença precisa
estar registrada para não parecer afrouxamento:

**O invariante é de outra natureza.** As anteriores proíbem duas linhas coexistirem — um índice
expressa isso. Esta proíbe uma **transição** acontecer duas vezes sobre a mesma linha. Não existe
índice que diga "esta coluna só pode sair de nulo uma vez": uma `CHECK` enxerga o valor final, não a
história.

**A garantia continua sendo do banco.** O `UPDATE ... WHERE used_at IS NULL` é indivisível: o
segundo bloqueia até o primeiro confirmar e reavalia o predicado com a versão nova, encontrando
zero linhas. A aplicação não decide — ela **lê o resultado** da decisão do banco.

**O que tornaria isso falso**, e por isso vira exigência verificável: se o desfecho fosse derivado
de uma leitura anterior em vez do resultado da escrita. É a armadilha de R3, e a verificação
obrigatória é trocar a escrita condicional pelo `if` e conferir que o teste de concorrência
**falha**.

Registrado em Complexity Tracking, para não depender de alguém ler esta seção.

**Nenhuma violação.** Dois itens em Complexity Tracking: a forma da garantia e a dependência nova.

## Project Structure

### Documentation (this feature)

```text
specs/010-gate-validation/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 14 decisões; R3 é a que mais importa
├── data-model.md        # Fase 1 — o campo de uso e a escrita que o protege
├── quickstart.md        # Fase 1 — incluindo forjar um código e reproduzir a corrida
├── contracts/
│   └── gate-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/screening/
│   ├── models.py                        # ALTERADO — Ticket.used_at, com o aviso de R3 ao lado
│   ├── migrations/0005_*.py             # NOVO — só o campo; a garantia é a forma da escrita
│   ├── services/
│   │   ├── portaria.py                  # NOVO — o pipeline e o UPDATE condicional
│   │   └── ingressos.py                 # INTOCADO — puro, e continua sem importar modelo
│   ├── selectors.py                     # ALTERADO — sessoes_da_portaria; NÃO usa sellable() (R11)
│   ├── serializers.py                   # ALTERADO — entrada e saída da validação.
│   │                                    #   TicketSerializer e MeuIngressoSerializer INTOCADOS (R14)
│   ├── permissions.py                   # ALTERADO — IsGate
│   ├── views.py                         # ALTERADO — GateScreeningsView, GateValidateView
│   └── urls.py                          # ALTERADO — dois endereços novos
└── tests/
    ├── test_gate_api.py                 # NOVO — os quatro desfechos, ordem, autorização
    ├── test_gate_concurrency.py         # NOVO — a prova do Princípio III
    ├── test_gate_signature.py           # NOVO — forjado rejeitado sem tocar o registro
    └── test_share_link_leakage.py       # ALTERADO — o campo de uso entra na lista de proibidos

frontend/
├── app/portaria/
│   ├── page.tsx                         # NOVO — Server Component: papel, sessões, estado inicial
│   ├── PortariaCliente.tsx              # NOVO — ilha cliente: câmera, digitação, desfecho
│   └── portaria.module.css              # NOVO
├── app/api/validar/route.ts             # NOVO — proxy, padrão de 002/003/007/008/009
├── components/gate/
│   ├── LeitorDeCodigo.tsx               # NOVO — câmera + laço de leitura + as regras de R8
│   ├── Desfecho.tsx                     # NOVO — símbolo, título e detalhe por situação
│   └── gate.module.css                  # NOVO
├── lib/api.ts                           # ALTERADO — fetchSessoesDaPortaria, postValidacao
├── lib/types.ts                         # ALTERADO — Desfecho, SessaoDaPorta
├── package.json                         # ALTERADO — dependência `jsQR`
└── tests/
    ├── portaria.test.tsx                # NOVO
    ├── desfecho.test.tsx                # NOVO
    └── e2e/portaria.spec.ts             # NOVO

README.md                                # ALTERADO — a tela, a sessão da porta, o contexto seguro
```

**Structure Decision**: a feature continua em `apps/screening`, junto de `Ticket` — o campo de uso é
uma coluna daquele modelo, e a validação é uma operação sobre ele.

`services/portaria.py` é arquivo próprio, e **não** mais uma função em `services/ingressos.py`.
Aquele módulo é **puro** por decisão da 008 — não importa modelo, não toca o banco —, e é essa
ausência que torna verificável a exigência do Princípio III de conferir a assinatura antes de
consultar o banco. A validação escreve. É a mesma separação que a 009 fez com
`services/compartilhamento.py`, pelo mesmo motivo, e agora vira padrão do projeto.

`components/gate/` separa o **leitor** do **desfecho** porque são coisas com ciclos diferentes: o
leitor tem estado de hardware, permissão e laço de quadros; o desfecho é apresentação pura de um
valor. Juntos, o desfecho seria intestável sem simular câmera.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **A garantia é um `UPDATE` condicional, não um índice** — o invariante é de transição, não de
   coexistência, e nenhum índice expressa "esta coluna só sai de nulo uma vez".
2. **O desfecho vem da escrita, nunca da leitura** — `rowcount` 1 é válido, 0 é já utilizado.
3. **A armadilha**: o `if` antes do `save()` passa em todo teste de uma thread, lê como a regra da
   spec, e não é pego por nenhuma constraint — porque não há constraint.
4. **Sessão errada vem antes de já utilizado**, e não escreve. Um ingresso recusado na porta errada
   continua valendo na porta certa.
5. **Os quatro desfechos são `200`** com um campo `situacao` fixo. Nenhum deles é erro da
   requisição; a portaria perguntou e recebeu resposta.
6. **`jsQR`, um caminho só** — `BarcodeDetector` nativo foi rejeitado como caminho único (não existe
   em toda parte) e como preferencial (dois decodificadores, e o de reserva apodrece).
7. **A câmera exige contexto seguro** — `localhost` serve, IP de rede local não. A digitação manual,
   que a constitution já exigia, é o que mantém a portaria funcionando no cenário mais provável de
   demonstração.
8. **Uma apresentação, um desfecho** — sem as regras do laço, o próprio aparelho da pessoa produz
   "válido" seguido de "já utilizado". Idempotência no servidor **não** resolve isso.
9. **A armadilha da 009 volta**: `sellable()` esconde a sessão em andamento, que é exatamente a que a
   porta está recebendo.
10. **O campo de uso não pode vazar para as telas do cliente** — a pressão de crescimento agora vem
    do outro lado, e a página compartilhada é pública.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — o campo de uso, a escrita condicional passo a passo, o
  pipeline com o que cada etapa pode escrever, e a consulta das sessões da porta.
- **[contracts/gate-api.md](./contracts/gate-api.md)** — os dois endereços, os quatro desfechos com
  seus campos, e o que a resposta não pode conter.
- **[quickstart.md](./quickstart.md)** — percorrer a validação, **forjar um código**, provocar os
  quatro desfechos e reproduzir a corrida à mão.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Seis pontos a vigiar na implementação:

- **O desfecho tem de vir do `rowcount`.** Se vier de um `if` sobre o objeto lido, o teste de
  concorrência é a única coisa que pega — e ele só pega se existir antes do serviço.
- **`sessão errada` não escreve.** Consumir um ingresso legítimo na porta errada é pior do que não
  ter a checagem.
- **`services/ingressos.py` continua sem importar modelo.** É o terceiro plano seguido a repetir
  isto, e continua valendo: no dia em que importar, `num_queries == 0` deixa de ser estrutural.
- **`TicketSerializer` e `MeuIngressoSerializer` não ganham o campo de uso.** Uma linha, e
  "utilizado" aparece na página compartilhada **pública** da 009.
- **A lista de sessões da porta não pode usar `sellable()`.** Segunda aparição do mesmo filtro como
  erro natural.
- **O teste de concorrência precisa de transação real.** Herdado da 007, repetido na 008 e na 009:
  sem `transaction=True` as threads compartilham conexão e o teste passa de qualquer jeito.

### Nota sobre o que é verificado à mão

**A leitura por câmera** é conferida manualmente, no quickstart: apontar a câmera para um QR real
exige hardware. O automatizado cobre o resto do caminho — o mesmo código, entregue por digitação,
produz o mesmo desfecho (SC-010), e o e2e percorre a tela inteira pela via digitada.

É a mesma honestidade que a 009 aplicou à legibilidade do QR, e pela mesma razão: o Princípio VI
pede que o buraco esteja escrito, não escondido atrás de um teste que verifica outra coisa.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| **A garantia de unicidade não tem forma de constraint**, ao contrário de 007, 008 e 009 | O invariante é de **transição** — "esta coluna só sai de nulo uma vez" —, e nenhum índice o expressa: uma `CHECK` enxerga o valor final, não a história; uma `UNIQUE` não tem duas linhas para comparar. O `UPDATE ... WHERE used_at IS NULL` é indivisível e continua sendo o **banco** decidindo: o segundo bloqueia, reavalia o predicado e afeta zero linhas. | **`SELECT FOR UPDATE` e depois escrever** foi rejeitado por serem duas instruções — a correção passaria a depender de ninguém as separar. **Tabela de eventos de validação com `UNIQUE(ingresso)`** devolveria o formato de índice à custa de um modelo inteiro para guardar um instante: acrescenta estrutura para não mudar de técnica. **Se a leitura de que a garantia continua sendo do banco não se sustentar em revisão, o caminho é emendar a constitution** — não implementar a divergência em silêncio. |
| **Dependência nova `jsQR`** no front-end | Decodificar QR é um padrão publicado com casos de borda reais — localização de padrões, correção de erro, perspectiva, binarização sob luz irregular. É o outro lado do mesmo argumento que a 008 usou para trazer `qrcode` no servidor: reimplementar seria indefensável. JavaScript puro, sem dependências transitivas, versão fixada. | **`BarcodeDetector` nativo** foi rejeitado como caminho único porque não existe em todo navegador, e como caminho preferencial com reserva porque seriam dois decodificadores com comportamentos diferentes — e o de reserva é o que apodrece sem ninguém notar. **`@zxing/library`** é muito maior para ler um formato só. **Decodificar no servidor** mandaria imagem da fila do cinema pela rede a cada quadro. |
