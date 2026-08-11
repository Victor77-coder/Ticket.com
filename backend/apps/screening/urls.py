from django.urls import path

from apps.screening.views import SeatMapView

app_name = "screening"

urlpatterns = [
    path("sessoes/<int:pk>/mapa/", SeatMapView.as_view(), name="seat-map"),
]
