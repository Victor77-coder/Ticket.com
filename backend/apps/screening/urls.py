from django.urls import path

from apps.screening.views import (
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
]
