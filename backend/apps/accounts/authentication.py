"""Autenticação por sessão para as rotas que o Next chama de servidor.

`SessionAuthentication` do DRF exige o par `csrftoken`/`X-CSRFToken` em toda
requisição de escrita. Aqui essa exigência não protege nada e quebra tudo: o
navegador nunca fala com o Django direto — ele fala com o Next, na mesma
origem, e o Next repassa o cookie numa chamada **servidor-a-servidor**, que
não carrega credencial ambiente de navegador nenhum.

É a mesma decisão que a `003` registrou em R1 e aplicou no login com
`csrf_exempt`. A defesa contra requisição forjada está uma camada acima: o
cookie é `httpOnly` e `SameSite=Lax`, emitido pelo próprio Next.

**Isto não desliga o CSRF do projeto** — só destas rotas, e só porque o
navegador não é quem as chama.
"""

from rest_framework.authentication import SessionAuthentication


class SessionAuthenticationSemCsrf(SessionAuthentication):
    def enforce_csrf(self, request):
        return None
