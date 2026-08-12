from django.urls import path

from apps.screening.views import (
    PaymentCreateView,
    ReservationCreateView,
    ReservationDetailView,
    SeatMapView,
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
]
