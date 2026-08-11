"""Views de autenticação.

`LoginView` é pública por natureza; as outras duas resolvem o usuário a partir
do cookie de sessão que o Next repassa. O padrão do projeto é negar por
padrão (ver REST_FRAMEWORK em config/settings/base.py), então o acesso aberto
é declarado aqui, explicitamente.
"""

from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import LoginSerializer, SessionSerializer
from apps.accounts.services import throttle

# Uma única frase para os três motivos de recusa — identificador inexistente,
# senha errada e conta inativa (FR-004). Diferenciá-los revelaria quais contas
# existem, que é metade de um ataque de força bruta.
CREDENCIAL_INVALIDA = "Usuário ou senha incorretos."


# O CSRF do Django é dispensado aqui porque a proteção acontece uma camada
# acima: o navegador só fala com o Next, na mesma origem, e o cookie de sessão
# é SameSite=Lax. Este salto é servidor-a-servidor e não carrega credencial
# ambiente do navegador. Ver R1 em research.md.
@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    """POST /api/v1/auth/login/"""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # Campo faltando é erro de formulário: não consome tentativa.
            return Response(
                {"detail": _primeiro_erro(serializer.errors), "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = serializer.validated_data["username"]
        password = serializer.validated_data["password"]
        origem = throttle.origem_da_requisicao(request)

        if throttle.esta_bloqueado(origem, username):
            espera = throttle.segundos_restantes(origem, username)
            return Response(
                {
                    "detail": (
                        f"Muitas tentativas. Tente novamente em {max(espera // 60, 1)} minutos."
                    ),
                    "retry_after_seconds": espera,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # `authenticate` devolve None para usuário inexistente, senha errada e
        # conta inativa. Os três convergem sozinhos — não há mensagem a
        # unificar à mão, que é onde este requisito costuma vazar depois.
        user = authenticate(request, username=username, password=password)

        if user is None:
            throttle.registrar_falha(origem, username)
            return Response(
                {"detail": CREDENCIAL_INVALIDA},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # `login` rotaciona a chave de sessão, o que anula fixação de sessão.
        login(request, user)
        throttle.limpar(origem, username)

        return Response(
            {
                "session_key": request.session.session_key,
                "expires_at": request.session.get_expiry_date(),
                "user": SessionSerializer(user).data,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class LogoutView(APIView):
    """POST /api/v1/auth/logout/"""

    permission_classes = [AllowAny]

    def post(self, request):
        # 204 mesmo sem sessão: encerrar algo que já não existe é o resultado
        # desejado, não erro.
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class SessionView(APIView):
    """GET /api/v1/auth/me/

    O 401 aqui é estado normal, não falha: é assim que o cabeçalho descobre
    que deve mostrar "Entrar" (FR-017).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Sessão não encontrada."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(SessionSerializer(request.user).data)


def _primeiro_erro(errors):
    """Primeira mensagem de validação, para exibir no topo do formulário."""
    for mensagens in errors.values():
        if mensagens:
            return str(mensagens[0])
    return "Verifique os campos informados."
