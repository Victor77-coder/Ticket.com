# Phase 0 — Research: Autenticação e Acesso à Conta

**Feature**: `003-user-authentication` | **Date**: 2026-08-11

Cada item registra a decisão, o motivo e o que foi descartado. Nenhum `NEEDS CLARIFICATION`
permanece aberto ao fim desta fase.

---

## R1. Onde a sessão vive e quem emite o cookie

**Decision**: a sessão é do **Django** (tabela `django_session`), mas o cookie que o navegador
guarda é emitido pelo **Next**, no Route Handler de entrada. O Next guarda a chave de sessão em
um cookie `httpOnly`, `sameSite=lax`, `path=/`, e `secure` fora de desenvolvimento. Em cada
requisição que precisa da sessão, o Next lê esse cookie e o repassa ao Django como cookie de
sessão na chamada servidor-a-servidor.

**Rationale**:

- O navegador **não consegue** falar com o Django. Dentro do Compose o back-end atende em
  `http://backend:8000`, nome que só resolve na rede interna. A feature 002 já resolveu isso com
  o proxy `/api/busca`; a autenticação segue o mesmo padrão em vez de inventar um segundo.
- Com o cookie emitido pelo Next, o navegador enxerga **uma única origem**. Isso torna o
  `SameSite=Lax` uma defesa real contra requisição forjada de outro site (FR-019), sem precisar
  propagar o par `csrftoken` + `X-CSRFToken` do Django através do proxy — que é onde esse tipo de
  arranjo costuma quebrar de forma silenciosa.
- A comunicação Next → Django é servidor-a-servidor e não carrega credencial ambiente do
  navegador, então não existe vetor de CSRF naquele salto.
- `httpOnly` atende FR-018 diretamente: script na página não alcança o identificador.

**Alternatives considered**:

- **Repassar o `Set-Cookie` do Django tal como veio** — parece mais simples, mas o atributo
  `Domain` e o `Path` passam a depender de como o Django enxerga o host, e o cookie fica sujeito
  a divergir entre desenvolvimento e deploy. Descartado por fragilidade, não por complexidade.
- **JWT em cookie** — dispensaria a tabela de sessão, mas invalidar no logout exigiria uma lista
  de revogação, ou seja, reconstruir estado de sessão do zero com outro nome. FR-014 exige que
  encerrar realmente invalide. Descartado.
- **NextAuth / Auth.js** — resolveria o transporte, mas moveria a verdade da autenticação para
  fora do Django, onde estão o modelo de usuário e os papéis. Uma dependência grande para
  substituir algo que já existe no projeto.

---

## R2. Nenhuma dependência nova

**Decision**: usar `django.contrib.auth` e `django.contrib.sessions`, ambos já em
`INSTALLED_APPS`. Nenhum pacote é adicionado.

**Rationale**: hash de senha com PBKDF2, comparação em tempo constante, recusa de conta inativa,
rotação de chave de sessão no login e invalidação no logout já estão implementados e testados.
Reescrever qualquer um deles seria trocar código testado por código novo em um requisito onde o
erro é caro.

---

## R3. A mensagem uniforme não precisa ser construída

**Decision**: usar `django.contrib.auth.authenticate()` e devolver **uma única** mensagem quando
ele retornar `None`.

**Rationale**: o `ModelBackend` devolve `None` nos três casos que FR-004 exige indistinguíveis —
identificador inexistente, senha errada e conta inativa. Não é preciso unificar mensagens à mão,
o que é justamente onde esse requisito costuma vazar: alguém adiciona um `if not user` com texto
diferente e a enumeração de contas volta.

O `ModelBackend` também executa o hash mesmo quando o usuário não existe, o que mantém o tempo de
resposta parecido nos dois casos — parte de SC-005.

**Consequência assumida**: a mensagem não ajuda quem esqueceu qual das quatro contas do seed
estava usando. É o preço correto: revelar quais identificadores existem é entregar metade de um
ataque de força bruta.

---

## R4. Limite de tentativas

**Decision**: contador no cache do Django, chaveado por `(origem, identificador)`, com janela
deslizante. Cinco falhas seguidas bloqueiam novas tentativas daquele par por 15 minutos, com
mensagem em português informando quando poderá tentar de novo. Uma entrada bem-sucedida zera o
contador.

**Rationale**: FR-007 pede o comportamento, não um mecanismo. São cerca de vinte linhas contra
uma dependência (`django-axes`) que traz modelos, migrações, admin e configuração que este
projeto não usaria.

Chavear pelos dois valores — e não só pela origem — evita que um atacante em uma rede
compartilhada bloqueie contas alheias, e evita que trocar de identificador contorne o limite.

**Alternatives considered**:

- **`django-axes`** — completo, com bloqueio persistente e painel. Excesso para o escopo.
- **Throttle do DRF por escopo** — funciona por requisição, mas não distingue tentativa
  malsucedida de bem-sucedida; limitaria também quem acerta a senha de primeira.

**Consequência assumida**: o contador vive no cache local em memória. Reiniciar o back-end zera
os bloqueios. Aceitável no escopo de avaliação; num deploy real o cache seria compartilhado.

---

## R5. Prazo de validade da sessão

**Decision**: duas semanas — `SESSION_COOKIE_AGE = 1209600`, que é o padrão do Django, com
`SESSION_EXPIRE_AT_BROWSER_CLOSE = False`.

**Rationale**: FR-016 exige persistir entre reaberturas do navegador; FR-017 exige expirar. O
padrão do Django já é exatamente a suposição registrada no spec, então não há valor em divergir.
Duas semanas cobrem folgadamente o período de avaliação sem virar sessão eterna.

---

## R6. Como o cabeçalho sabe quem está autenticado

**Decision**: `SiteHeader` continua server component. Um módulo `lib/session.ts` lê o cookie com
`cookies()` e resolve a sessão chamando `GET /api/v1/auth/me/` no Django. O resultado desce por
props até o `AccountButton`.

**Rationale**:

- Resolver no servidor elimina o piscar entre "Entrar" e o nome do usuário, que é o defeito mais
  visível de fazer isso no cliente.
- Mantém a decisão da 002 de não arrastar o layout para o bundle: só o menu de conta é ilha
  cliente.
- FR-022 e o Princípio IV ficam naturalmente satisfeitos: o papel é resolvido no servidor a cada
  requisição, nunca lido de algo guardado no navegador.

**Consequência assumida**: ler `cookies()` torna o layout dinâmico em toda página. O projeto já é
dinâmico por outras razões (elegibilidade ao destaque depende do relógio), então não há perda.

**Alternatives considered**:

- **Contexto de cliente com fetch no `useEffect`** — traz o piscar e coloca o estado de sessão em
  lugar onde ele parece confiável para decisões de interface. Descartado.
- **Middleware do Next resolvendo a sessão** — rodaria em toda requisição, inclusive assets, e
  colocaria uma chamada de rede no caminho crítico de navegação.

---

## R7. Segurança do retorno após a entrada

**Decision**: o destino de retorno é aceito **apenas** se começar com `/` e não começar com `//`
nem com `/\`. Qualquer outro valor é descartado em favor de `/`.

**Rationale**: FR-011. `//evil.com` e `/\evil.com` são interpretados por navegadores como
endereços absolutos — é a forma clássica de transformar um parâmetro de retorno em
redirecionamento aberto, que serve para phishing convincente porque o link parte do site legítimo.

A validação é por forma, não por lista de destinos permitidos: qualquer rota interna futura
continua funcionando sem manutenção.

---

## R8. Onde fica a ação de sair

**Decision**: um componente cliente `AccountMenu` envolve o `AccountButton`. Ele controla a
abertura do menu e dispara `POST /api/sair`, seguido de recarga da rota para que o cabeçalho
volte ao estado de visitante.

**Rationale**: o `AccountButton` da 002 já prevê o estado autenticado com um `onAbrirConta` — um
callback deliberadamente sem dono, esperando esta feature. Estado de abertura e ação de rede são
de cliente; o `SiteHeader` é de servidor. A ilha isolada resolve os dois sem desfazer a decisão
da 002.

**Detalhe**: sair usa `POST`, não `GET`. Um `GET` que encerra sessão pode ser disparado por
pré-carregamento de link ou por uma imagem em outro site.

---

## R9. Estratégia de testes

| Alvo | Tipo | Por quê |
|---|---|---|
| Resposta de sessão sem senha nem hash | back-end | Gate do Princípio IV (FR-023, SC-006) |
| Mensagem idêntica para inexistente, senha errada e inativo | back-end | FR-004, SC-005 — o requisito mais fácil de quebrar em manutenção |
| Entrada bem-sucedida para os quatro papéis semeados | back-end | SC-002 |
| Limite de tentativas: bloqueia, informa, e zera ao acertar | back-end | FR-007 |
| Saída invalida a sessão de fato | back-end | FR-014 |
| Retorno rejeita `//evil.com`, `/\evil.com` e endereço absoluto | front-end | FR-011 — falha aqui é redirecionamento aberto |
| Cabeçalho nos dois estados, e volta a visitante ao expirar | front-end | FR-024 a FR-026, e o FR-024 da 002 |
| Percurso visitante → entrada → autenticado → saída | e2e | T038 da 002, SC-009 |

**Rationale**: concentra onde a constitution exige prova (Princípio IV) e onde o erro tem
consequência de segurança, não onde é fácil escrever teste.
