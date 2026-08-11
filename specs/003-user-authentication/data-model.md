# Phase 1 — Data Model: Autenticação e Acesso à Conta

**Feature**: `003-user-authentication` | **Date**: 2026-08-11

**Nenhuma migração nova.** Tudo de que esta feature precisa já existe: o modelo de usuário veio
com a feature 001 e a tabela de sessões vem do Django. Este documento registra o que existe, por
que basta, e o que deliberadamente não é criado.

---

## `accounts.User` — já existe, não muda

Criado em `catalog`… não: criado em `apps/accounts/models.py` pela feature 001, antes da primeira
migração, porque o Django não permite trocar `AUTH_USER_MODEL` depois sem recriar o banco.

| Campo | Origem | Uso nesta feature |
|---|---|---|
| `username` | `AbstractUser` | identificador de entrada (FR-002) |
| `password` | `AbstractUser` | hash PBKDF2; **nunca** sai do servidor |
| `first_name` / `last_name` | `AbstractUser` | compõem o nome de exibição no cabeçalho |
| `is_active` | `AbstractUser` | conta inativa é recusada com a mesma mensagem (FR-004) |
| `role` | próprio | `organizer` \| `customer` \| `gate` (FR-021) |
| `last_login` | `AbstractUser` | atualizado pelo Django na entrada |

**Nada é adicionado.** A tentação seria criar campos de controle de tentativa (`failed_attempts`,
`locked_until`) na tabela de usuários. Isso é recusado em R4: escrever no banco a cada senha
errada transforma uma tentativa de força bruta em carga de escrita, e o bloqueio precisa
considerar a origem, que não é atributo do usuário.

---

## Sessão — fornecida pelo Django

Tabela `django_session`, criada pela migração `sessions.0001` já aplicada.

| Coluna | Significado |
|---|---|
| `session_key` | identificador opaco; é o valor guardado no cookie emitido pelo Next |
| `session_data` | carga assinada, contendo o id do usuário autenticado |
| `expire_date` | quando a sessão deixa de valer (FR-016, FR-017) |

**Ciclo de vida**

| Momento | O que acontece |
|---|---|
| Entrada bem-sucedida | `login()` cria a linha e **rotaciona** a chave, o que anula fixação de sessão |
| Cada requisição autenticada | o Django resolve o usuário a partir da chave; nada é reescrito |
| Saída | `logout()` apaga a linha — a chave antiga deixa de resolver (FR-014) |
| Expiração | `expire_date` no passado; o Django trata como não autenticado, sem erro (FR-017) |

**Prazo**: `SESSION_COOKIE_AGE = 1209600` (duas semanas), o padrão do Django.

---

## Contador de tentativas — cache, não banco

Chave: `auth:tentativas:{origem}:{identificador}`
Valor: inteiro
Validade: 15 minutos, renovada a cada falha

| Regra | Valor |
|---|---|
| Falhas seguidas antes do bloqueio | 5 |
| Duração do bloqueio | 15 min |
| Entrada bem-sucedida | zera a chave |

Chaveado pelos **dois** valores de propósito (R4): só pela origem, alguém numa rede compartilhada
bloquearia contas alheias; só pelo identificador, trocar de usuário contornaria o limite.

**Limitação registrada**: o cache é local em memória, então reiniciar o back-end zera os
bloqueios. Aceitável no escopo de avaliação — vai para as limitações conhecidas do README.

---

## O que NÃO é criado

| Não criado | Por quê |
|---|---|
| Modelo de cadastro / convite | Sem auto-cadastro nesta feature (decisão do usuário, 2026-08-11) |
| Token de recuperação de senha | O desafio exclui recuperação de senha explicitamente |
| Modelo de perfil separado | `User` já carrega nome e papel; um perfil vazio seria indireção sem conteúdo |
| Permissões por objeto | Não há objeto a proteger ainda. Chegam com reserva e portaria |
| `Seat`, `Reservation`, `Ticket` | Fronteira da feature de reserva — ver `001/data-model.md` |

---

## Forma da sessão exposta à interface

Não é uma entidade persistida; é o que `GET /api/v1/auth/me/` devolve e o que o cabeçalho consome.

```
Sessao {
  nome:  string   # nome de exibição, já montado no servidor
  papel: "organizer" | "customer" | "gate"
}
```

**Dois campos, e só.** Qualquer acréscimo passa pelo gate do Princípio IV — a lista de proibidos
está em [contracts/auth-api.md](./contracts/auth-api.md).

O `papel` desce para a interface **escolher o que apresentar**, nunca para conceder acesso
(FR-022). Ele é resolvido no servidor a cada requisição; guardá-lo no navegador criaria a ilusão
de que dá para confiar nele.
