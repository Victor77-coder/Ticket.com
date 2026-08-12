"""Permissões do domínio de sessão e reserva.

A autorização é do servidor — esconder o botão na interface não conta
(Princípio IV, FR-025). Quem não compra e chama a API direto recebe
recusa explícita, não silêncio.
"""

from rest_framework.permissions import BasePermission


class IsCustomer(BasePermission):
    """Só o papel cliente reserva e consulta reserva própria.

    Organizador e portaria chegam autenticados, então a recusa é `403`,
    não `401`: eles entraram, só não podem comprar. Confundir os dois
    códigos faria o front conduzir um organizador à tela de entrada —
    caminho sem saída, porque a entrada não muda o papel.
    """

    message = "Apenas clientes podem reservar lugares."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_customer)


class IsCustomerParaPagar(IsCustomer):
    """A mesma regra, com a frase do pagamento.

    Só a mensagem muda. "Apenas clientes podem reservar lugares." apareceria
    para quem tentou **pagar**, e mandaria o organizador procurar um botão de
    reserva que não é o que ele acionou — mensagem de erro que descreve outra
    tela é o tipo de texto que o Princípio V proíbe.
    """

    message = "Apenas clientes podem pagar reservas."
