# Contrato: O Cartão de Sessão e os Dois Painéis

**Feature**: 014 | **Date**: 2026-08-13

Este é contrato de **interface**, não de API: define o que a tela promete a quem usa, incluindo
quem usa só o teclado ou só o leitor de tela. É o que os testes de apresentação verificam.

---

## O cartão de sessão

### Estrutura

```
┌──────────────────────────────────────────────────────────────┐
│  Sala 2                              [⌗ Assentos]  [$ Preços] │  ← cabeçalho + ações
├──────────────────────────────────────────────────────────────┤  ← régua
│                                                              │
│   ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐             │
│   │ 13:30  │  │ 16:00  │  │ 19:00  │  │ 21:50  │             │  ← alvos
│   │R$ 32,00│  │R$ 32,00│  │R$ 38,00│  │ Esgot. │             │
│   └────────┘  └────────┘  └────────┘  └────────┘             │
└──────────────────────────────────────────────────────────────┘
```

### Promessas

| # | Promessa | Como se verifica |
|---|---|---|
| C1 | Um cartão por **sala**, dentro do dia ativo | Filme com duas salas → dois cartões, cada um nomeando a sua |
| C2 | O nome da sala é cabeçalho, e nomeia o cartão para tecnologia assistiva | O cartão é uma região rotulada pelo nome da sala |
| C3 | As ações trazem **rótulo em texto**, não só ícone | Os nomes acessíveis são "Assentos" e "Preços" |
| C4 | As ações identificam **qual sessão** operam | Ver "Qual sessão o painel mostra", abaixo |
| C5 | Horário disponível continua sendo link para o mapa, com o nome acessível da 007 | `/^Escolher lugares —/` continua casando |
| C6 | Horário esgotado se distingue **sem depender só de cor** | Texto "Esgotada" + borda tracejada, como já era |
| C7 | O preço aparece em cada horário | Já entregue antes desta feature; o cartão preserva |

### Qual sessão o painel mostra

O cartão agrupa **vários horários** da mesma sala, e as ações ficam no topo do cartão — então
"Assentos" precisa saber de qual horário se trata.

**Decisão**: as ações do topo operam sobre o **primeiro horário disponível** do cartão, e o painel
aberto traz um seletor dos demais horários daquele cartão. Sem horário disponível, as ações
continuam acessíveis e o painel abre no primeiro horário, informando que está esgotado.

**Por que não uma ação por horário**: multiplicaria três alvos por horário numa grade que pode ter
doze. A grade viraria formulário, que é exatamente o que a recomposição da 012 tirou dela.

---

## O painel de assentos

### Promessas

| # | Promessa | Como se verifica |
|---|---|---|
| A1 | Desenha a sala com **livre** e **ocupado** distinguíveis sem depender só de cor | Mesma verificação em escala de cinza que a 007 aplica ao mapa |
| A2 | Informa **quantos lugares livres** restam | Número visível, batendo com o mapa |
| A3 | É **somente leitura** — nenhum assento é acionável | Nenhum assento é botão, link ou campo |
| A4 | Oferece caminho para o mapa real, **exceto** se esgotada | Sessão com lugares → o caminho existe; esgotada → diz que não há lugares |
| A5 | Enquanto carrega, **comunica espera** | Estado anunciado a leitor de tela |
| A6 | Se falhar, **explica em português** o que houve e a próxima ação | Nunca painel vazio, nunca "algo deu errado" |
| A7 | Sala sem lugares diz isso | Nunca desenha sala vazia sem explicação |

### Fonte dos dados

`GET /api/v1/sessoes/<id>/mapa/` — **o mesmo do mapa de seleção**, sem endpoint novo (R4).

Campos consumidos: `sala.nome`, `esgotada`, `fileiras[].letra`, `fileiras[].assentos[].numero`,
`fileiras[].assentos[].situacao`.

**A situação é consumida como vem.** Nenhuma reinterpretação de "quem está ocupando" acontece no
painel — essa regra tem dono, e ele já existe.

---

## O painel de preços

### Promessas

| # | Promessa | Como se verifica |
|---|---|---|
| P1 | Exibe **inteira** e **meia** com valores | Sessão de R$ 32,00 → "R$ 32,00" e "R$ 16,00" |
| P2 | Os valores são **daquela sessão** | Duas sessões com preços diferentes → duas tabelas diferentes |
| P3 | Declara que a meia é conferida na entrada mediante documento | Frase presente |
| P4 | O valor exibido é o que será cobrado | Mesma derivação do servidor, tabela de casos compartilhada |

---

## Regras comuns aos dois painéis

Estas valem para os dois, e são a parte que costuma faltar em modal feito às pressas:

| # | Regra | Como se verifica |
|---|---|---|
| M1 | Fecha com `Esc` | Tecla fecha, painel some |
| M2 | Fecha por controle visível, com nome acessível | Botão "Fechar", alcançável por teclado |
| M3 | **Prende o foco** enquanto aberto | Tabulação circula dentro do painel |
| M4 | **Devolve o foco** à ação que o abriu | Depois de fechar, o foco está no botão de origem |
| M5 | É anunciado como diálogo, com nome | Papel de diálogo, rotulado pelo título do painel |
| M6 | Um painel por vez | Abrir Preços com Assentos aberto fecha o primeiro |
| M7 | Nenhum valor solto de cor, espaço, raio ou duração | `tokens.test.ts` |

> **M3 e M4 são a razão de existir o componente `Sobreposicao`.** `<dialog>` nativo já entrega M1 e
> M3; M4 é o que quase sempre falta, e é o que faz a navegação por teclado não se perder no topo da
> página depois de fechar.

---

## O que o cartão NÃO tem

Registrado aqui porque a ausência é decisão, não esquecimento (FR-005, R8):

| Elemento da referência | Por que não |
|---|---|
| Nome e endereço de cinema | A plataforma modela um cinema; o local é a sala |
| Selo "DUBLADO" / "LEGENDADO" | O TMDb não fornece por sessão; selo fixo seria placeholder |
| Coração de favoritar | Recurso de conta que não existe e que o desafio não pede |
| Ação "Detalhes" | A página do filme já tem Sobre e Trailers desde a 012 |
