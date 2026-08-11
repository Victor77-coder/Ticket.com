"""Serializers de autenticação.

GATE DO PRINCÍPIO IV — nenhuma resposta daqui pode conter senha, hash,
identificador interno, e-mail, `last_login`, `is_staff`, `is_superuser` nem
dados de outro usuário. A lista completa está em
`specs/003-user-authentication/contracts/auth-api.md` e é verificada por
`tests/test_auth_api.py`.
"""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    """Valida a presença dos campos antes de qualquer tentativa de autenticar.

    FR-006: campo faltando é erro de formulário, não credencial inválida — e
    não deve consumir uma tentativa do limite.
    """

    username = serializers.CharField(
        max_length=150,
        error_messages={
            "required": "Informe o usuário.",
            "blank": "Informe o usuário.",
        },
    )
    password = serializers.CharField(
        max_length=128,
        trim_whitespace=False,
        error_messages={
            "required": "Informe a senha.",
            "blank": "Informe a senha.",
        },
    )


class SessionSerializer(serializers.Serializer):
    """Descrição da sessão ativa — exatamente dois campos.

    `papel` desce para a interface escolher **o que apresentar**, nunca para
    conceder acesso (FR-022). Toda autorização continua sendo decidida no
    servidor a cada requisição.
    """

    nome = serializers.SerializerMethodField()
    papel = serializers.CharField(source="role")

    def get_nome(self, user):
        """Nome de exibição já montado no servidor.

        Cai para o `username` quando a conta não tem nome preenchido, para que
        o cabeçalho nunca exiba espaço em branco no lugar da identificação.
        """
        return user.get_full_name().strip() or user.get_username()
