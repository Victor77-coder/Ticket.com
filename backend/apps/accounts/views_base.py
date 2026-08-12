"""A base de view da programação — de PAPEL, como a permissão ao lado.

MORA AQUI PELO MESMO MOTIVO QUE `IsOrganizer`: a programação atravessa dois
apps — filme é `catalog`, sala e sessão são `screening` —, e as duas metades
da cobertura (a permissão e a tradução do `401`) precisam ser uma só. Deixar
esta classe em `screening/views.py` obrigaria `catalog` a importar de
`screening`, e `screening` já importa `catalog` para conhecer `Movie`: os dois
apps passariam a depender um do outro por causa de uma classe de três linhas.

Copiá-la nos dois apps seria pior — a frase do `401` teria duas redações, e a
que alguém corrigisse seria a que aparece na metade das telas.
"""

from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.authentication import SessionAuthenticationSemCsrf
from apps.accounts.permissions import IsOrganizer

ENTRE_PARA_PROGRAMAR = {"detail": "Entre para programar sessões."}


class ProgramacaoViewBase(APIView):
    """O que TODA rota de programação compartilha: quem entra e como recusa.

    Mesma autenticação sem CSRF de 007, 008, 009 e 010 — quem chama é o Next,
    servidor a servidor —, e a mesma tradução do `401`, com a frase desta área.

    A TRADUÇÃO NÃO É ENFEITE: o DRF converte "não autenticado" em `403` quando
    o autenticador não oferece `WWW-Authenticate`, que é o caso da sessão. Sem
    ela, visitante e papel errado sairiam iguais, e o front não saberia quando
    conduzir à entrada e quando renderizar a recusa. Conduzir um cliente à
    entrada por causa de um `403` é caminho sem saída: entrar de novo não muda
    o papel (R11).

    HERDAR DAQUI É METADE DA COBERTURA DE FR-034. A outra é o prefixo
    `/api/v1/programacao/`: juntos, fazem a regra legível de fora, em vez de
    depender de alguém lembrar de declarar a permissão em cada view nova.
    """

    authentication_classes = [SessionAuthenticationSemCsrf]
    permission_classes = [IsAuthenticated, IsOrganizer]

    def handle_exception(self, exc):
        if isinstance(exc, NotAuthenticated):
            return Response(ENTRE_PARA_PROGRAMAR, status=401)
        return super().handle_exception(exc)
