# Implementation Plan: Autenticação e Acesso à Conta

**Branch**: `main` (o projeto trabalha sem branches de feature) | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-user-authentication/spec.md`

## Summary

Entregar entrada, saída e sessão para os três papéis já existentes no modelo, e montar no
cabeçalho o ponto de acesso à conta que a feature 002 deixou escrito e desmontado.

A decisão estruturante é **reusar a autenticação do Django em vez de inventar uma**: hash de
senha, invalidação de sessão, prazo de validade e mensagem uniforme para credencial inválida já
existem e são testados há anos. O que este plano acrescenta é a ponte entre o navegador e esse
mecanismo, seguindo o padrão de proxy que a feature 002 já estabeleceu — o navegador fala apenas
com o Next, e o Next fala com o Django.

O cookie de sessão é emitido **pelo Next**, não repassado do Django. Isso mantém o navegador com
uma única origem (`localhost:5003`) e torna o `SameSite=Lax` uma defesa real contra requisição
forjada, em vez de depender de sincronizar o CSRF do Django através de um proxy.

## Technical Context

**Language/Version**: Python 3.12 (back-end) · TypeScript 5.x / Node 20 (front-end)

**Primary Dependencies**: Django 5 (`django.contrib.auth`, `django.contrib.sessions`) + DRF ·
Next.js 15 App Router — **nenhuma dependência nova**

**Storage**: PostgreSQL 16. Sessões na tabela `django_session`; contador de tentativas no cache

**Testing**: `pytest` + `pytest-django` · Vitest + Testing Library · Playwright

**Target Platform**: Web. Interface em `localhost:5003`, API em `localhost:8000`

**Project Type**: Web application (front-end + back-end separados)

**Performance Goals**: entrada concluída em ≤ 1 s · resolução da sessão no cabeçalho sem atraso
perceptível na renderização de qualquer página

**Constraints**: identificador de sessão inacessível a scripts · mensagem idêntica para os três
motivos de falha · retorno após entrada só para endereços internos · nenhum papel conduzido a
área inexistente

**Scale/Scope**: 4 contas semeadas, escala de avaliação. Duas telas novas (entrada e o menu de
conta), quatro endpoints.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Avaliado contra a Constitution v1.0.0.

| Princípio | Status | Como este plano satisfaz |
|---|---|---|
| **I. Fluxo Completo Antes de Profundidade** | ✅ PASS | Entrar, sair e expirar são entregues juntos. Entrar sem sair seria o beco sem saída proibido. A expiração tem comportamento definido (FR-017), não é caso omitido. |
| **II. Integridade da Reserva** | ➖ N/A | Nenhuma escrita de assento. |
| **III. Ingresso Inforjável** | ➖ N/A | Nenhum ingresso emitido ou validado. |
| **IV. Papéis e Autorização no Servidor** | ✅ PASS | É o princípio que esta feature realiza. O papel devolvido ao cliente escolhe **o que apresentar**, nunca concede acesso (FR-022). Gate: teste provando que a resposta de sessão nunca contém senha nem hash, e que o papel vem do servidor a cada requisição — nunca de valor guardado no navegador. |
| **V. Interface Autoral (Anti AI-Slop)** | ✅ PASS | A tela de entrada usa os tokens já definidos. Mensagens em pt-BR dizendo o que houve e a próxima ação. Visitante e autenticado se distinguem por texto, não só por cor (FR-026) — o `AccountButton` da 002 já resolve isso mostrando o nome. |
| **VI. Rastro de Decisão Versionado** | ✅ PASS | Artefatos versionados; o README precisa perder a linha "Não há autenticação" e ganhar as credenciais como utilizáveis de fato. |
| **VII. Isolamento da API Externa** | ➖ N/A | Nenhuma chamada ao TMDb. |

**Nenhuma violação sem justificativa.** Duas alterações em código de outra feature estão
registradas em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-user-authentication/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── auth-api.md      # Endpoints do Django e do proxy do Next
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — gerado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── apps/accounts/
│   ├── models.py             # User com role — já existe, não muda
│   ├── serializers.py        # NOVO — entrada e descrição da sessão
│   ├── services/
│   │   └── throttle.py       # NOVO — contador de tentativas no cache
│   ├── views.py              # NOVO — LoginView, LogoutView, SessionView
│   └── urls.py               # NOVO — /api/v1/auth/
├── config/
│   ├── settings/base.py      # sessão, DRF, throttle
│   └── urls.py               # registra apps.accounts.urls
└── tests/
    ├── test_auth_api.py      # NOVO — entrada, saída, papéis, vazamento
    └── test_auth_throttle.py # NOVO — limite de tentativas

frontend/
├── app/
│   ├── entrar/
│   │   ├── page.tsx          # NOVO — tela de entrada
│   │   └── entrar.module.css # NOVO
│   ├── api/
│   │   ├── entrar/route.ts   # NOVO — proxy de entrada; emite o cookie
│   │   └── sair/route.ts     # NOVO — proxy de saída; apaga o cookie
│   └── layout.tsx            # passa a sessão ao cabeçalho
├── components/header/
│   ├── SiteHeader.tsx        # ALTERADO — preenche o espaço de conta (T037 da 002)
│   ├── AccountButton.tsx     # já existe — não muda
│   └── AccountMenu.tsx       # NOVO — ilha cliente: abre o menu e encerra a sessão
├── lib/
│   ├── session.ts            # NOVO — lê o cookie e resolve a sessão no servidor
│   └── types.ts              # ganha o tipo de sessão
└── tests/
    ├── auth.test.tsx         # NOVO — tela de entrada e menu de conta
    ├── header.test.tsx       # ALTERADO — ponto de conta agora montado
    └── e2e/header.spec.ts    # ALTERADO — percurso de entrada (T038 da 002)
```

**Structure Decision**: a autenticação vive em `apps/accounts`, onde o modelo de usuário já
está. O front-end segue o padrão de proxy que a 002 estabeleceu: rotas de navegador em
`app/api/`, e a resolução de sessão em `lib/session.ts` para que componentes de servidor a
consultem sem duplicar lógica.

## Phase 0 — Research

Consolidado em [research.md](./research.md). Decisões principais:

1. **Sessão do Django, cookie emitido pelo Next** — o navegador vê uma origem só; o
   `SameSite=Lax` passa a ser defesa real contra requisição forjada, sem propagar o CSRF do
   Django através do proxy.
2. **Nenhuma dependência nova** — `django.contrib.auth` já traz hash de senha, verificação em
   tempo constante e recusa de conta inativa.
3. **Mensagem uniforme sai de graça** — `authenticate()` devolve `None` para usuário inexistente,
   senha errada e conta inativa. Os três caminhos convergem sem código extra, o que é mais seguro
   do que unificar mensagens à mão.
4. **Limite de tentativas por contador no cache**, chaveado por origem e identificador. Sem
   `django-axes`: uma dependência a menos para um requisito de vinte linhas.
5. **Prazo de validade de duas semanas** — é exatamente o padrão do Django
   (`SESSION_COOKIE_AGE = 1209600`), e coincide com a suposição do spec.
6. **Cabeçalho resolve a sessão no servidor** — sem piscar entre "Entrar" e o nome do usuário.
7. **Retorno após entrada validado por forma** — aceita apenas caminho começando por `/` e não
   por `//` nem `/\`, que é o que fecha o redirecionamento para fora do site.

## Phase 1 — Design & Contracts

- **[data-model.md](./data-model.md)** — o que já existe (`User.role`), o que o Django fornece
  (`django_session`) e por que **nenhuma migração nova** é necessária.
- **[contracts/auth-api.md](./contracts/auth-api.md)** — `POST /api/v1/auth/login/`,
  `POST /api/v1/auth/logout/`, `GET /api/v1/auth/me/` e os dois Route Handlers do Next, com a
  lista de campos proibidos na resposta.
- **[quickstart.md](./quickstart.md)** — percorrer entrada, troca de papel e saída com as quatro
  contas do seed.

### Post-Design Constitution Re-check

Reavaliado: **nenhuma violação nova**. Três pontos a vigiar na implementação:

- A resposta de sessão **não pode** ganhar campo algum além de nome de exibição e papel. Qualquer
  acréscimo passa pelo gate do Princípio IV.
- O papel **não pode** ser lido de valor guardado no navegador para decidir o que mostrar em
  página de servidor — sempre da sessão resolvida no servidor. Guardá-lo no cliente criaria a
  ilusão de que dá para confiar nele.
- O cookie precisa de `secure` quando não for desenvolvimento. Deixar isso amarrado ao `DEBUG`
  evita entregar cookie de sessão em texto claro num deploy.

## Complexity Tracking

> Duas alterações em código pertencente à feature `002-site-header-navigation`.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Alterar `SiteHeader.tsx` e `header.test.tsx`, que pertencem à feature 002 | É exatamente o desbloqueio previsto: T037 e T038 estão marcadas `🚧 NÃO EXECUTAR AINDA` esperando a rota de entrada. O SC-009 desta feature só fecha quando elas fecharem. | Criar um segundo cabeçalho com conta seria duplicar a faixa em toda página. Deixar o `AccountButton` desmontado manteria o pedido do usuário sem atender. |
| Criar `AccountMenu.tsx`, que a 002 não previu | O `AccountButton` autenticado expõe `onAbrirConta`, um callback sem dono. Encerrar a sessão exige estado de abertura e uma ação — ambos de cliente. O `SiteHeader` é server component e não pode hospedá-los. | Transformar o `SiteHeader` inteiro em client component arrastaria o layout para o bundle e desfaria uma decisão explícita da 002. A ilha cliente isolada preserva as duas coisas. |
