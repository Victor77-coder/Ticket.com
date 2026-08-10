from django.urls import path

from apps.catalog.views import HighlightsView, MovieDetailView

app_name = "catalog"

urlpatterns = [
    path("highlights/", HighlightsView.as_view(), name="highlights"),
    path("filmes/<slug:slug>/", MovieDetailView.as_view(), name="movie-detail"),
]
