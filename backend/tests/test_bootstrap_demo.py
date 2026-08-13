from io import StringIO
from unittest.mock import patch

from django.core.management import call_command


def test_bootstrap_nao_mexe_quando_catalogo_e_grade_ja_existem(make_movie, make_screening):
    filme = make_movie()
    make_screening(filme)

    with patch("apps.catalog.management.commands.bootstrap_demo.call_command") as mocked:
        saida = StringIO()
        call_command("bootstrap_demo", stdout=saida)

    mocked.assert_not_called()
    assert "ignorado" in saida.getvalue()
