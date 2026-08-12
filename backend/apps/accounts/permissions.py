"""Permissões de PAPEL — não de domínio.

`screening/permissions.py` guarda as permissões de quem COMPRA e de quem
valida, e elas moram lá porque reserva, pagamento e ingresso são daquele app.
A programação atravessa dois: filme é `catalog`, sala e sessão são
`screening`. Escrever `IsOrganizer` duas vezes, uma em cada app, colocaria a
decisão de autorização em dois lugares — exatamente o erro que o Princípio IV
existe para fechar. O papel é definido em `accounts`, e é aqui que ele decide
(R7).

`403`, NUNCA `401`. Cliente e portaria ENTRARAM; só não programam. Um `401`
mandaria o front conduzi-los à tela de entrada, e entrar de novo não muda o
papel — caminho sem saída. É a mesma distinção que `IsCustomer` e `IsGate` já
aplicam, e o comentário de `IsCustomer` explica por extenso.
"""

from rest_framework.permissions import BasePermission


class IsOrganizer(BasePermission):
    """Só o papel organizador programa filmes, salas e sessões.

    NÃO usa `is_staff`. O seed marca o organizador com `is_staff=True`, então
    `IsAdminUser` funcionaria por acidente — e acoplaria autorização de produto
    ao flag do admin do Django: um cliente promovido a staff por qualquer
    motivo ganharia a programação inteira.
    """

    message = "Apenas organizadores programam sessões."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_organizer)
