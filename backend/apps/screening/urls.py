from django.urls import path

from apps.screening.views import (
    GateScreeningsView,
    GateValidateView,
    MyTicketsView,
    PaymentCreateView,
    ReservationCreateView,
    ReservationDetailView,
    SalaDetailView,
    SalasView,
    SeatMapView,
    SessoesView,
    SharedTicketView,
    TicketDetailView,
    TicketShareLinkView,
)

app_name = "screening"

urlpatterns = [
    path("sessoes/<int:pk>/mapa/", SeatMapView.as_view(), name="seat-map"),
    path("reservas/", ReservationCreateView.as_view(), name="reservation-create"),
    path(
        "reservas/<int:pk>/",
        ReservationDetailView.as_view(),
        name="reservation-detail",
    ),
    path(
        "reservas/<int:pk>/pagamento/",
        PaymentCreateView.as_view(),
        name="payment-create",
    ),
    path("meus-ingressos/", MyTicketsView.as_view(), name="my-tickets"),
    path(
        "ingressos/<uuid:public_id>/",
        TicketDetailView.as_view(),
        name="ticket-detail",
    ),
    # Gerar (POST) e revogar (DELETE) no MESMO endereço: são criar e apagar o
    # mesmo recurso.
    path(
        "ingressos/<uuid:public_id>/link/",
        TicketShareLinkView.as_view(),
        name="ticket-share-link",
    ),
    # O ÚNICO endereço público de ingresso. O token vai no caminho, não em
    # query string: query strings vazam com mais facilidade em log de proxy e
    # em histórico, e um caminho é o que quem cola espera ver.
    path(
        "ingressos-compartilhados/<str:token>/",
        SharedTicketView.as_view(),
        name="shared-ticket",
    ),
    # Portaria (010). A validação é a única escrita da feature.
    path(
        "portaria/sessoes/",
        GateScreeningsView.as_view(),
        name="gate-screenings",
    ),
    path("portaria/validar/", GateValidateView.as_view(), name="gate-validate"),
    # Programação (013). Todo endereço sob `programacao/` exige o papel
    # organizador, e é o prefixo que torna a regra legível de fora: um endpoint
    # de programação colocado FORA dele é falha de FR-034, ainda que declare a
    # permissão certa. A outra metade da cobertura é herdar de
    # `ProgramacaoViewBase` — ver o docstring dela.
    path("programacao/salas/", SalasView.as_view(), name="programacao-salas"),
    path(
        "programacao/salas/<int:pk>/",
        SalaDetailView.as_view(),
        name="programacao-sala-detalhe",
    ),
    path("programacao/sessoes/", SessoesView.as_view(), name="programacao-sessoes"),
]
