from django.urls import path

from apps.catalog.views import HighlightsView, MovieDetailView, SearchView

app_name = "catalog"

urlpatterns = [
    path("highlights/", HighlightsView.as_view(), name="highlights"),
    path("busca/", SearchView.as_view(), name="busca"),
    path("filmes/<slug:slug>/", MovieDetailView.as_view(), name="movie-detail"),
]
