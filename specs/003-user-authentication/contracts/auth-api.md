# Contract — Auth API

**Feature**: `003-user-authentication` | **Date**: 2026-08-11

Dois níveis. O **Django** expõe a autenticação; o **Next** expõe ao navegador apenas o que ele
precisa, emitindo o cookie. O navegador nunca fala com o Django direto (R1).

```
navegador ──cookie de sessão──> Next (/api/entrar, /api/sair)
                                  │  chamada servidor-a-servidor
                                  └──> Django (/api/v1/auth/...)
```

---

# Django — `/api/v1/auth/`

## `POST /api/v1/auth/login/`

**Autenticação**: nenhuma. Público por natureza.

### Requisição

```json
{ "username": "cliente1", "password": "desafio2026" }
```

### `200 OK`

```json
{
  "session_key": "8f2b1c...",
  "expires_at": "2026-08-25T20:14:00-03:00",
  "user": { "nome": "Camila Souza", "papel": "customer" }
}
```

`session_key` existe para o Next colocá-lo no cookie `httpOnly`. Ele **nunca** chega a script no
navegador.

### `400 Bad Request` — campo faltando

```json
{ "detail": "Informe o usuário e a senha." }
```

### `401 Unauthorized` — credencial inválida

```json
{ "detail": "Usuário ou senha incorretos." }
```

**Idêntica** para identificador inexistente, senha errada e conta inativa (FR-004). Os três
convergem naturalmente porque `authenticate()` devolve `None` nos três casos — ver R3.

### `429 Too Many Requests` — tentativas excedidas

```json
{ "detail": "Muitas tentativas. Tente novamente em 15 minutos.", "retry_after_seconds": 900 }
```

---

## `POST /api/v1/auth/logout/`

**Autenticação**: cookie de sessão repassado pelo Next.

`204 No Content` sempre — inclusive quando não havia sessão. Encerrar algo que já não existe é o
resultado desejado, não erro.

Efeito: a linha em `django_session` é apagada; a chave antiga deixa de resolver (FR-014).

---

## `GET /api/v1/auth/me/`

**Autenticação**: cookie de sessão repassado pelo Next.

### `200 OK` — sessão válida

```json
{ "nome": "Camila Souza", "papel": "customer" }
```

### `401 Unauthorized` — sem sessão, ou sessão expirada

```json
{ "detail": "Sessão não encontrada." }
```

O `401` aqui é **estado normal**, não falha: é assim que o cabeçalho descobre que deve mostrar
"Entrar". O front-end nunca renderiza erro por causa dele (FR-017).

---

# Next — rotas que o navegador conhece

## `POST /api/entrar`

Recebe `{ username, password }`, repassa ao Django e, em caso de sucesso, emite:

```
Set-Cookie: sessionid=<session_key>;
            HttpOnly; SameSite=Lax; Path=/; Max-Age=1209600
            [; Secure  — fora de desenvolvimento]
```

| Atributo | Por quê |
|---|---|
| `HttpOnly` | script na página não alcança o identificador (FR-018) |
| `SameSite=Lax` | o navegador não envia o cookie em requisição vinda de outro site (FR-019) |
| `Secure` fora de dev | impede o cookie de trafegar em texto claro |
| `Max-Age` | casa com a validade da sessão no Django (FR-016) |

Repassa o status e o corpo do Django sem alterá-los — `401` e `429` chegam ao navegador com a
mesma frase em pt-BR.

## `POST /api/sair`

Chama o Django e apaga o cookie (`Max-Age=0`). Responde `204`.

**`POST`, nunca `GET`**: um `GET` que encerra sessão pode ser disparado por pré-carregamento de
link ou por uma imagem hospedada em outro site.

---

# Campos proibidos nas respostas

Gate do **Princípio IV**. Nenhuma resposta desta feature pode conter:

- `password`, hash de senha, ou qualquer fragmento dele
- `id` do usuário, `email`, `last_login`, `is_staff`, `is_superuser`
- dados de qualquer usuário que não seja o da sessão corrente
- `session_key` em resposta que chegue ao navegador — ele existe **apenas** no salto
  Django → Next, e daí direto para dentro do cookie

Deve existir teste que faça a entrada, serialize a resposta inteira e afirme a ausência de cada
item acima (SC-006).

---

# O que o contrato deliberadamente não tem

| Ausente | Por quê |
|---|---|
| `POST /auth/register/` | Sem auto-cadastro (decisão do usuário, 2026-08-11) |
| `POST /auth/password-reset/` | O desafio exclui recuperação de senha |
| `refresh_token` | Não há JWT; a sessão do Django já renova pelo `expire_date` |
| Permissões no corpo da resposta | O papel escolhe **o que apresentar**; autorização é sempre decidida no servidor a cada requisição (FR-022) |
