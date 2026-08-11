# Quickstart — Autenticação e Acesso à Conta

**Feature**: `003-user-authentication` | **Date**: 2026-08-11

Percorrer entrada, troca de papel e saída com as contas do seed. Pressupõe o ambiente já de pé —
ver o [README](../../README.md) para o setup completo.

---

## Pré-requisitos

```bash
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py sync_tmdb --limit 20
docker compose exec backend python manage.py seed_demo
```

Nenhuma migração nova é introduzida por esta feature — o modelo de usuário e a tabela de sessões
já existem.

---

## Contas

Todas com a senha **`desafio2026`**:

| Papel | Usuário |
|---|---|
| Organizador | `organizador` |
| Cliente | `cliente1` |
| Cliente | `cliente2` |
| Portaria | `portaria` |

---

## 1. Entrar

1. Abrir <http://localhost:5003>.
2. No canto direito do cabeçalho, o ícone de pessoa exibe **Entrar**.
3. Acioná-lo → chega a `/entrar`.
4. Informar `cliente1` / `desafio2026`.
5. **Esperado**: volta para a home, e o cabeçalho passa a exibir **Camila Souza** no lugar de
   "Entrar".

## 2. A sessão acompanha a navegação

1. Autenticado, abrir um filme pelo carrossel.
2. Usar a busca do cabeçalho e abrir outro filme.
3. **Esperado**: o nome continua no cabeçalho em todas as páginas, sem pedir credenciais de novo.

## 3. Voltar de onde partiu

1. Encerrar a sessão (passo 5) e abrir a página de um filme direto pela URL.
2. Acionar o ícone de conta a partir dali.
3. Entrar.
4. **Esperado**: volta para a **página do filme**, não para a home.

## 4. Credencial inválida

Tentar as três situações:

| Tentativa | Esperado |
|---|---|
| usuário que não existe | "Usuário ou senha incorretos." |
| `cliente1` com senha errada | **exatamente a mesma frase** |
| campo vazio | aponta qual campo falta, antes de tentar autenticar |

As duas primeiras produzirem mensagens diferentes é violação de FR-004 — é o que permite
descobrir quais contas existem.

## 5. Sair

1. Autenticado, acionar o ponto de conta no cabeçalho.
2. Escolher **Sair**.
3. **Esperado**: o cabeçalho volta a exibir "Entrar".
4. Recarregar e acionar o botão "voltar" do navegador.
5. **Esperado**: continua como visitante; nada da sessão anterior reaparece.

## 6. Trocar de papel

Repetir o passo 1 com `organizador` e depois com `portaria`.

**Esperado**: os três entram, e os três voltam para a mesma página de onde partiram. Nenhum papel
é conduzido a uma área que ainda não existe — as áreas de organizador e portaria chegam com as
features que lhes dão conteúdo.

---

## Verificações de segurança

Valem a pena porque são requisitos, não detalhes.

### O identificador de sessão está fora do alcance de scripts

No console do navegador, autenticado:

```js
document.cookie;
```

**Esperado**: o cookie de sessão **não** aparece. Se aparecer, o `HttpOnly` não está sendo
aplicado (FR-018).

### O retorno não leva para fora do site

```
http://localhost:5003/entrar?next=//exemplo.com
http://localhost:5003/entrar?next=/\exemplo.com
http://localhost:5003/entrar?next=https://exemplo.com
```

**Esperado**: nos três casos, entrar leva à **home**. Levar ao site externo é redirecionamento
aberto — serve para phishing convincente, porque o link parte do site legítimo (FR-011).

### Nenhuma resposta carrega senha

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login/ \
  -H 'Content-Type: application/json' \
  -d '{"username":"cliente1","password":"desafio2026"}' | grep -i "password\|pbkdf2" \
  && echo "FALHA: vazou credencial" || echo "OK: nenhuma credencial na resposta"
```

### O limite de tentativas funciona

Errar a senha de `cliente1` seis vezes seguidas.

**Esperado**: da sexta em diante, mensagem informando quando será possível tentar de novo, em vez
de "Usuário ou senha incorretos.".

> Reiniciar o back-end zera os bloqueios — o contador vive no cache em memória. Registrado nas
> limitações conhecidas.

---

## Testes

```bash
docker compose exec backend pytest tests/test_auth_api.py tests/test_auth_throttle.py
docker compose exec frontend npm run test
```

Ponta a ponta, a partir do host (a imagem é Alpine e os navegadores do Playwright são glibc):

```bash
cd frontend && npx playwright test e2e/header.spec.ts
```

---

## Problemas comuns

**Entrei, mas o cabeçalho continua mostrando "Entrar"** — o cookie não foi emitido ou não está
sendo lido no servidor. Conferir na aba Network se a resposta de `/api/entrar` traz `Set-Cookie`
e se o `Path` é `/`.

**Volto a ser visitante ao trocar de página** — provável `SameSite` restritivo demais ou `Path`
errado no cookie. Deve ser `SameSite=Lax` e `Path=/`.

**Todas as tentativas respondem 429** — o contador ficou preso de um teste anterior. Reiniciar o
back-end limpa: `docker compose restart backend`.

**`/entrar` mostra o formulário mesmo já autenticado** — FR-008 exige o redirecionamento; se
acontecer, a checagem de sessão na página não está rodando.
