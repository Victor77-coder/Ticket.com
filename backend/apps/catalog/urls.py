from django.urls import path

from apps.catalog.views import (
    CatalogoDoPainelView,
    HighlightsView,
    HomeRowsView,
    MovieDetailView,
    SearchView,
)

app_name = "catalog"

urlpatterns = [
    path("highlights/", HighlightsView.as_view(), name="highlights"),
    path("home/", HomeRowsView.as_view(), name="home-rows"),
    path("busca/", SearchView.as_view(), name="busca"),
    # Programação (013). Todo endereço sob `programacao/` exige o papel
    # organizador — o prefixo é o que torna a regra legível de fora, e um
    # endpoint de programação colocado fora dele é falha de FR-034 ainda que
    # declare a permissão certa.
    path(
        "programacao/filmes/",
        CatalogoDoPainelView.as_view(),
        name="programacao-filmes",
    ),
    path("filmes/<slug:slug>/", MovieDetailView.as_view(), name="movie-detail"),
]
