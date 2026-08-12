from django.urls import path

from apps.screening.views import (
    MyTicketsView,
    PaymentCreateView,
    ReservationCreateView,
    ReservationDetailView,
    SeatMapView,
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
]
