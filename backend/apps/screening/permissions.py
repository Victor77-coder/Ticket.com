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


class IsCustomerParaIngressos(IsCustomer):
    """A mesma regra, com a frase da área de ingressos.

    Terceira subclasse pelo mesmo motivo das duas anteriores: "Apenas
    clientes podem reservar lugares." apareceria para quem abriu **Meus
    ingressos**, descrevendo uma tela que a pessoa não acionou.

    E continua sendo `403`, nunca `401`: organizador e portaria ENTRARAM, só
    não têm ingressos. Um `401` os mandaria para a tela de entrada, que é
    caminho sem saída — entrar de novo não muda o papel.
    """

    message = "Apenas clientes têm ingressos."


class IsGate(BasePermission):
    """Só o papel portaria valida ingressos.

    Não herda de `IsCustomer` — é o papel oposto. Um cliente aqui recebe
    `403`, não `401`: ele entrou, só não valida. É a mesma distinção que as
    três permissões acima já fazem, agora do outro lado.

    A recusa importa mais aqui do que nas outras: sem ela, um cliente marca o
    PRÓPRIO ingresso como utilizado e ninguém entra com ele depois.
    """

    message = "Apenas a portaria valida ingressos."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_gate)
