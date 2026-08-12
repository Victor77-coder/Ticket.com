# Quickstart — Marca sem Laranja

**Feature**: `011-marca-sem-laranja` | **Date**: 2026-08-12

Percorrer as dez superfícies, **quebrar o contraste de propósito** e conferir que o teste pega.
Pressupõe o ambiente já de pé; ver o [README](../../README.md) para o setup completo.

---

## Pré-requisitos

Esta feature **não introduz variável de ambiente, migração nem alteração de banco**. Traz **uma
família tipográfica nova**, auto-hospedada.

```bash
docker compose up -d --build frontend
```

O `--build` importa: a família da marca entra em `frontend/public/fontes/`.

---

## Percurso 1 — A cor antiga não existe mais

```bash
grep -rn "ff5c39\|ff7a5c\|255, *92, *57" frontend --exclude-dir=node_modules --exclude-dir=.next
```

**Esperado**: nada. Se aparecer qualquer linha, é FR-004 violado.

```bash
grep -rn "cor-destaque\|cor-sobre-destaque" frontend/styles/tokens.css
```

**Esperado**: os cinco nomes de sempre, com valores novos. Se um nome mudou, FR-005 caiu — e os 12
consumidores teriam de ser tocados, que é exatamente o que a feature evita.

```bash
grep -rEn "#[0-9a-fA-F]{6}|rgba\(" frontend/components frontend/app --include=*.css | grep -v "var(--"
```

**Esperado**: nada de cor de marca. É a disciplina da 006 verificada em vez de confiada — e o que
garante que os 12 arquivos consumidores não precisaram ser editados.

---

## Percurso 2 — A prova que mede *(o percurso mais importante)*

```bash
docker compose exec frontend npm run test -- tokens
```

**Esperado**: verde, cobrindo contraste (C1–C7), distância de estado (D1–D3) e ausência da cor
antiga (A1–A2). Os limites estão em
[`contracts/contraste.md`](./contracts/contraste.md).

### Quebrar de propósito — três vezes

**Esta é a verificação central da feature**, porque nenhum outro teste do projeto pega estes
defeitos. Os 197 testes de front-end continuam verdes com a interface quebrada.

**(a) Apagar o foco de teclado.** Em `tokens.css`, escurecer `--cor-destaque-forte` para algo como
`#6b0033`:

```bash
docker compose exec frontend npm run test -- tokens
```

**Esperado**: falha em **C3**, nomeando o par e quanto faltou. Restaure.

Rode agora a suíte inteira **com o valor quebrado ainda no lugar**, uma vez, para ver o problema:

```bash
docker compose exec frontend npm run test
```

**Esperado**: **tudo verde.** Nenhum dos 197 testes percebe que o contorno de foco sumiu. É por isso
que o teste de tokens existe. Restaure antes de seguir.

**(b) Harmonizar a marca com o alerta.** Trocar `--cor-destaque` por `#ffd447` (o âmbar que a
pesquisa descartou):

**Esperado**: falha em **D2** — ΔE 8 contra o mínimo de 25. É a mesma medida que eliminou o âmbar da
disputa, agora congelada como regra. Restaure.

**(c) Deixar um vestígio.** Colocar `#ff5c39` em qualquer arquivo de componente:

**Esperado**: falha em **A1**. Restaure.

---

## Percurso 3 — As dez superfícies

Entrar como `cliente1` (senha `desafio2026`) e percorrer. Em cada uma, procurar **um respingo da cor
antiga** e conferir que a ação principal está na cor nova.

| # | Superfície | O que conferir |
|---|---|---|
| 1 | Home | Ação do painel de destaque; substituto de cartaz quando o filme não tem arte |
| 2 | Filme | Borda da sessão escolhida |
| 3 | Assentos | Assento selecionado, ação de confirmar |
| 4 | Pagamento | Botão principal, contorno do campo em foco |
| 5 | Meus ingressos | Lugar em destaque, ação do estado vazio |
| 6 | Ingresso do dono | Botão do painel de link |
| 7 | Ingresso compartilhado | **O QR** — ver percurso 4 |
| 8 | Entrar | Botão Entrar |
| 9 | Portaria — escolha da porta | Horário em destaque, borda da opção |
| 10 | Portaria — desfecho | Detalhes do ingresso; os quatro desfechos |

**Esperado**: nenhuma fica para trás (FR-028). Uma superfície na cor antiga é o defeito mais visível
que esta feature pode produzir.

---

## Percurso 4 — O que NÃO pode ter mudado

### O fundo do QR

Abrir qualquer ingresso e olhar o código.

**Esperado**: **fundo branco**. É a superfície que mais parece fora do lugar numa feature de paleta,
e a única que não pode ser harmonizada — leitor de QR depende do contraste entre módulo escuro e
fundo claro. Se alguém a tingiu de magenta "para combinar", a catraca para de ler.

```bash
grep -n "cor-fundo-qr" frontend/styles/tokens.css
```

**Esperado**: `#ffffff`.

### Assentos sem depender de cor

Abrir o mapa de uma sessão e aplicar um filtro de escala de cinza (DevTools → Rendering → Emulate
vision deficiencies → Achromatopsia).

**Esperado**: disponível, selecionado, tomado e indisponível continuam distinguíveis — cada um tem
forma própria, contorno ou preenchimento. Se o selecionado virou indistinguível do tomado, o ajuste
fino da cor nova comeu a forma, e FR-030 caiu.

### Os quatro desfechos da portaria

Mesmo filtro, na tela de validação. Provocar os quatro (ver
`specs/010-gate-validation/quickstart.md`).

**Esperado**: distinguíveis por símbolo e título antes de qualquer cor.

### O destino da marca por papel

Entrar como `portaria` e acionar a marca no cabeçalho.

**Esperado**: vai para `/portaria`, não para o catálogo. É o comportamento que a 010 entregou, e o
que se perde ao reescrever o componente de marca do zero.

---

## Percurso 5 — A marca

### Tela larga

**Esperado**: marca gráfica e nome formando um conjunto; o nome em família visivelmente diferente do
texto da interface; nenhum brilho, halo ou sombra em volta.

### 320px

```text
DevTools → dispositivo → 320×568
```

**Esperado**: a variante compacta aparece, continua reconhecível, e nenhuma superfície ganha rolagem
lateral.

### Ícone de aba

**Esperado**: a variante compacta, legível a 16px.

### Antes de a fonte chegar

```text
DevTools → Network → throttling "Slow 3G", recarregar
```

**Esperado**: o nome aparece legível na substituta e **o cabeçalho não salta** quando a família da
marca chega (FR-018). A marca gráfica desenha igual desde o primeiro quadro — ela é caminho vetorial,
não texto.

### Leitor de tela

**Esperado**: um rótulo coerente que nomeia o site, e não "imagem" nem o nome do arquivo.

---

## Percurso 6 — Nada de comportamento mudou

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
cd frontend && npx playwright test --workers=2
```

**Esperado**: **360 / 197+ / 41**, os mesmos números da 010 mais o que esta feature acrescentou.

**Se um teste de comportamento falhar, a mudança visual está errada — não o teste.** Ajuste de
seletor é aceitável quando um elemento mudou de forma; afrouxar verificação de regra de negócio não
é, em nenhuma circunstância (FR-036).

Percorrer o fluxo inteiro uma vez: comprar → pagar → ver ingresso → compartilhar → validar.

**Esperado**: idêntico ao de antes, em outra cor.

---

## Percurso 7 — A checagem anti-slop

Seguir [`contracts/anti-slop-review.md`](./contracts/anti-slop-review.md) e registrar o resultado
naquele arquivo.

É o **único** critério desta feature que depende de julgamento humano, e é por isso que ele tem
procedimento escrito: para que outra pessoa chegue ao mesmo veredito, e para que "não passou" venha
com motivo.

As duas perguntas finais:

1. Numa galeria ao lado de cinco catálogos de streaming, dá para apontar qual é o nosso?
2. Mostrando a home por dois segundos, a pessoa diz o nome do site?

---

## O que NÃO existe nesta feature, de propósito

- **Nenhuma mudança de comportamento.** APIs, seed, limites, regras de trilha e o fluxo inteiro
  ficam como estão.
- **Nenhum teste visual por comparação de imagem.** Travaria qualquer ajuste de estilo futuro e não
  responde à pergunta que importa — se a tela tem identidade. O que é objetivo é medido; o que não é,
  tem procedimento humano escrito.
- **Nenhuma redistribuição do significado das cores de estado.** A cor nova ocupa exatamente os
  papéis que a antiga ocupava. Aproveitar a feature para mudar o que a cor comunica misturaria duas
  decisões e tornaria qualquer regressão difícil de atribuir.
- **Nenhum tema claro.**
