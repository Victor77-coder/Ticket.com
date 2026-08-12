"""Duas abas programando a mesma (sala, horário) — SC-004, R4.

UMA DAS TRÊS PROVAS DE RECORTE DA 013, e a mais fácil de fazer passar pelo
motivo errado: um `Screening.objects.filter(room=..., starts_at=...).exists()`
antes do INSERT passa em qualquer teste sequencial e falha exatamente aqui —
as duas conexões verificam, nenhuma encontra, e ambas gravam.

Mesmo formato dos testes de concorrência das 007, 008 e 010: threads reais,
conexões reais, `TransactionTestCase` para que cada thread enxergue o que a
outra confirmou. Com `pytest.mark.django_db` comum, a transação de teste
isolaria as threads e o teste passaria sem provar nada.

O QUE ESTE ARQUIVO NÃO PROVA: que não existe um `exists()` no caminho. Ele
prova o RESULTADO; o caminho é responsabilidade da revisão de código, e está
escrito no docstring de `services/programacao.py`.
"""

import threading
from datetime import timedelta
from decimal import Decimal

from django.db import connections
from django.test import TransactionTestCase
from django.utils import timezone

from apps.catalog.models import Movie
from apps.screening.models import Room, Screening
from apps.screening.services import programacao


class ProgramarAoMesmoTempo(TransactionTestCase):
    """Duas criações simultâneas: exatamente uma sessão fica gravada."""

    def setUp(self):
        self.sala = Room.objects.create(name="Sala 1", capacity=60)
        self.filme = Movie.objects.create(
            tmdb_id=99001, title="A Odisseia", slug="a-odisseia"
        )
        self.inicio = timezone.now() + timedelta(hours=6)

    def _programar(self, resultados, indice):
        try:
            programacao.criar_sessao(
                filme=self.filme,
                sala=self.sala,
                inicio=self.inicio,
                preco=Decimal("32.00"),
                publicar=True,
            )
            resultados[indice] = "gravou"
        except programacao.ConflitoDeHorario as recusa:
            resultados[indice] = recusa.mensagem
        finally:
            # Cada thread abre a própria conexão; deixá-la aberta trava o
            # encerramento do teste.
            connections.close_all()

    def test_exatamente_uma_vence_e_a_outra_recebe_a_frase(self):
        resultados = [None, None]
        threads = [
            threading.Thread(target=self._programar, args=(resultados, i))
            for i in range(2)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert Screening.objects.count() == 1, "a constraint deixou passar a duplicata"

        vencedoras = [r for r in resultados if r == "gravou"]
        perdedoras = [r for r in resultados if r != "gravou"]
        assert len(vencedoras) == 1
        assert len(perdedoras) == 1

        # A perdedora recebe uma FRASE, não um erro de banco: ela nomeia a sala
        # e o horário, porque "já existe sessão nesse horário" obrigaria a
        # pessoa a descobrir sozinha qual conflito ela criou.
        assert "Sala 1" in perdedoras[0]
        assert "Escolha outro horário ou outra sala" in perdedoras[0]

    def test_a_recusa_nao_deixa_a_transacao_inutilizavel(self):
        """O `transaction.atomic()` interno, provado pelo efeito.

        Sem ele, a transação fica marcada como quebrada depois do
        `IntegrityError` e a primeira consulta seguinte estoura
        `TransactionManagementError` — inclusive a que monta a mensagem, que
        toca a sala. Programar de novo logo em seguida é o que demonstra que a
        conexão continua utilizável.
        """
        programacao.criar_sessao(
            filme=self.filme,
            sala=self.sala,
            inicio=self.inicio,
            preco=Decimal("32.00"),
            publicar=True,
        )

        try:
            programacao.criar_sessao(
                filme=self.filme,
                sala=self.sala,
                inicio=self.inicio,
                preco=Decimal("32.00"),
                publicar=True,
            )
        except programacao.ConflitoDeHorario as recusa:
            assert "Sala 1" in recusa.mensagem

        outra = programacao.criar_sessao(
            filme=self.filme,
            sala=self.sala,
            inicio=self.inicio + timedelta(hours=3),
            preco=Decimal("32.00"),
            publicar=True,
        )
        assert outra.pk is not None
