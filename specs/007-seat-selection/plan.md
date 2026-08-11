# Implementation Plan: Escolha de Assentos

**Branch**: `main` (o projeto trabalha sem branches de feature) | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-seat-selection/spec.md`

## Summary

Criar o mapa de assentos, a reserva temporária e — **na mesma migração** — a constraint que
impede vender o mesmo lugar duas vezes.

A decisão que estrutura tudo: **a constraint é absoluta, não condicional**. `UNIQUE(sessão,
assento)` sem predicado. Isso parece conflitar com a expiração, porque uma reserva vencida
deixaria a linha bloqueando o lugar para sempre — e a saída não é enfraquecer a constraint, é
**remover a linha morta sob bloqueio, dentro da própria transação de reserva**.

O ganho é grande: o banco vira árbitro final e incondicional. Se a aplicação errar, a violação de
unicidade estoura — e essa exceção é resultado **esperado**, traduzida em "este lugar acabou de
ser tomado". É o que torna o teste de concorrência uma prova de verdade, não uma encenação.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 + DRF · Next.js 15 — **nenhuma dependência nova**

**Storage**: PostgreSQL 16. Uma migração cria `Seat`, `Reservation`, `ReservedSeat` e a
constraint — **as quatro coisas juntas**, porque separá-las é o que o Princípio II proíbe

**Testing**: `pytest` + `pytest-django` com **transações reais e threads** para o teste de
concorrência · Vitest + Testing Library · Playwright

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Performance Goals**: mapa de 60 lugares carregando em ≤ 1 s · reserva confirmada em ≤ 1 s ·
a consulta de disponibilidade não pode fazer uma consulta por assento

**Constraints**: nenhuma asserção das features 001–006 pode mudar · disciplina de tokens mantida ·
o mapa funciona com o TMDb fora do ar · autorização no servidor

**Scale/Scope**: salas de 40 e 60 lugares, dezenas de sessões. Escala de avaliação, mas a
garantia de unicidade precisa valer sob concorrência real.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo** | ✅ PASS | Sessão esgotada, lugar recém-tomado, sessão cancelada e reserva vencida têm cada um mensagem própria. O caminho termina em handoff explícito ao pagamento, não em beco sem saída. |
| **II. Integridade da Reserva (NÃO NEGOCIÁVEL)** | ✅ PASS | `UNIQUE(sessão, assento)` **absoluta**, criada na mesma migração dos modelos. Transição sob `SELECT FOR UPDATE` dentro de transação. Teste de concorrência com threads reais e conexões separadas — **é prova obrigatória, não diferencial**. |
| **III. Ingresso Inforjável** | ➖ N/A | Nenhum ingresso é emitido. Explicitamente fora de escopo (FR-029). |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | Só papel cliente reserva; organizador e portaria recebem recusa **do servidor**. Um cliente não alcança reserva de outro. Teste de acesso cruzado obrigatório. |
| **V. Interface Autoral** | ✅ PASS | Quatro estados distinguíveis por forma e rótulo, não só por cor. Mensagens em pt-BR dizendo o que houve e a próxima ação. Tokens da 006 preservados. |
| **VI. Rastro de Decisão** | ✅ PASS | A denormalização que carrega a constraint, a escolha da constraint absoluta e a limitação da demonstração ficam registradas com o motivo. |
| **VII. Isolamento da API Externa** | ✅ PASS | Sala, sessão e assentos são dados locais. O mapa funciona com o TMDb fora do ar. |

**Nenhuma violação.** Uma denormalização deliberada está registrada em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-seat-selection/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0 — 12 decisões, com a de concorrência no centro
├── data-model.md        # Fase 1 — os três modelos e onde a garantia vive
├── quickstart.md        # Fase 1 — incluindo como reproduzir a corrida à mão
├── contracts/
│   └── reservation-api.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/screening/
│   ├── models.py                       # ALTERADO — Seat, Reservation, ReservedSeat + constraint
│   ├── migrations/0002_*.py            # NOVO — os três modelos e a constraint, juntos
│   ├── selectors.py                    # NOVO — mapa da sessão e disponibilidade
│   ├── services/
│   │   └── reservas.py                 # NOVO — a transação que é o coração da feature
│   ├── serializers.py                  # NOVO
│   ├── views.py                        # NOVO — mapa (público) e reserva (só cliente)
│   └── urls.py                         # NOVO
├── apps/catalog/management/commands/
│   └── seed_demo.py                    # ALTERADO — gera os assentos das salas
└── tests/
    ├── test_seat_map_api.py            # NOVO — mapa, estados, acesso público
    ├── test_reservation_api.py         # NOVO — autorização, validação, mensagens
    └── test_reservation_concurrency.py # NOVO — a prova do Princípio II

frontend/
├── app/sessoes/[id]/
│   ├── page.tsx                        # NOVO — a tela do mapa
│   └── sessao.module.css               # NOVO
├── app/api/reservar/route.ts           # NOVO — proxy, padrão da 002/003
├── components/seats/
│   ├── SeatMap.tsx                     # NOVO — a sala
│   ├── Seat.tsx                        # NOVO — um lugar, quatro estados
│   ├── SelectionSummary.tsx            # NOVO — seleção, total e confirmar
│   └── seats.module.css                # NOVO
├── app/filmes/[slug]/page.tsx          # ALTERADO — sessão passa a levar ao mapa
└── tests/seats.test.tsx                # NOVO
```

**Structure Decision**: a feature vive em `apps/screening`, não em `catalog`. Assento, reserva e
sessão são o mesmo domínio — sala e horário —, enquanto `catalog` cuida de filme e do TMDb. A
separação por domínio já estabelecida na 001 continua valendo.

`services/reservas.py` existe porque a transação de reserva é lógica de negócio com regra de
concorrência, não serialização nem roteamento. Deixá-la na view a tornaria intestável sem HTTP,
justo onde o teste precisa de threads.

## Phase 0 — Research

Consolidado em [research.md](./research.md). As decisões que mais importam:

1. **Constraint absoluta, não condicional** — `UNIQUE(sessão, assento)` sem predicado. Um índice
   parcial sobre "reserva viva" seria a saída óbvia e é **impossível**: o predicado dependeria de
   `now()`, que o PostgreSQL não aceita em índice.
2. **A linha morta é removida sob bloqueio, na própria transação de reserva** — é isso que
   concilia constraint absoluta com expiração, sem rotina agendada.
3. **A violação de unicidade é resultado esperado**, não bug: traduzida em "este lugar acabou de
   ser tomado". É a rede que pega o que o bloqueio deixar passar.
4. **`ReservedSeat` carrega `screening` denormalizado** — o Django não expressa constraint através
   de travessia de chave estrangeira, e a garantia precisa estar na linha que representa ocupação.
5. **Assentos persistidos por sala**, gerados da capacidade, com tipo comum ou acessibilidade.
6. **Disponibilidade em uma consulta**, nunca uma por assento.
7. **Teste de concorrência com threads reais e conexões separadas** — `pytest.mark.django_db`
   com transação real. Sem isso o teste roda numa transação só e não prova nada.
8. **Idempotência do envio duplo por chave de idempotência**, não por checar antes.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — `Seat`, `Reservation`, `ReservedSeat`; onde vive a
  garantia; a máquina de estados da reserva; e por que a denormalização é o menor mal.
- **[contracts/reservation-api.md](./contracts/reservation-api.md)** — `GET` do mapa e `POST` da
  reserva, com os códigos de recusa e os campos proibidos.
- **[quickstart.md](./quickstart.md)** — percorrer o fluxo, e **como reproduzir a corrida à mão**
  para ver a constraint agindo.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Quatro pontos a vigiar na implementação:

- **A constraint e os modelos entram na mesma migração.** Dois commits, um com o modelo e outro
  com a constraint, deixariam uma janela em que existe escrita de assento sem proteção — que é
  literalmente o que o Princípio II proíbe.
- **O teste de concorrência precisa de transação real.** Rodando dentro da transação de teste
  padrão, as duas threads compartilham conexão e o teste passa sem provar nada. É o modo mais
  fácil de ter um teste verde que não testa.
- **A remoção da linha vencida acontece sob `SELECT FOR UPDATE`**, nunca antes de bloquear. Sem o
  bloqueio, duas transações removem a mesma linha e ambas seguem para inserir.
- **`seats_taken` da 004 deixa de retornar zero.** A propriedade foi escrita prevendo isto; agora
  passa a contar de verdade, sem migração de dados.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| `ReservedSeat` guarda `screening` além de apontar para `Reservation`, que já tem a sessão | A constraint precisa viver na linha que representa a ocupação, e o Django não expressa unicidade através de travessia de chave estrangeira. Sem a coluna, não há como declarar `UNIQUE(sessão, assento)`. | Unicidade só em `(reserva, assento)` não impede duas reservas diferentes tomarem o mesmo lugar — que é exatamente a falha que o Princípio II existe para prevenir. Validar na aplicação foi rejeitado pela constitution, que exige a garantia no banco. |
| Alterar `seed_demo`, que pertence à 001 | Sem assentos gerados, o mapa não tem o que exibir e o cenário do desafio não é percorrível. | Criar os assentos numa migração de dados prenderia a disposição da sala ao histórico de migrações, e mudá-la exigiria nova migração em vez de rodar o seed de novo. |
