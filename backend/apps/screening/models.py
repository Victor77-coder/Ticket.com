"""Salas, sessões, assentos e reservas.

Da 001 até a 006 este arquivo carregou um aviso: escrita de ocupação de
assento não entrava sem a constraint UNIQUE(screening, seat) que a protege,
porque criar uma sem a outra é o que o Princípio II proíbe.

A feature 007 atravessou a fronteira, e o aviso saiu porque foi cumprido:
ReservedSeat e `unico_assento_por_sessao` nasceram na mesma migração. A
garantia continua sendo a razão de o modelo poder existir — ver a seção
"onde a garantia vive" em specs/007-seat-selection/data-model.md.

A feature 008 fez o mesmo com o par seguinte: `Payment` e `Ticket` nasceram
na mesma migração que as constraints que os protegem, porque "pagamento
aprovado DEVE emitir o ingresso; não existe estado intermediário durável em
que o assento esteja preso sem dono" é a mesma exigência lida do outro lado.

A 009 acrescenta `TicketShareLink` — de novo modelo e constraint na mesma
migração, e aqui a consequência de separar seria menor que nas duas
anteriores (nenhum assento é vendido duas vezes por causa de um link). A
regra vale assim mesmo: abrir exceção nela é como as regras acabam.

O QUE A 009 NÃO FAZ, E É O MAIS IMPORTANTE DAQUI: o token do link NÃO deriva
do código do QR e não conhece a `TICKET_SIGNING_KEY`. São dois segredos com
ciclos de vida independentes — revogar um convite não pode queimar uma
entrada paga, e o ingresso não pode depender de link nenhum para valer na
portaria. `services/ingressos.py` continua sem saber que link existe, e
`TicketShareLink` continua sem saber que existe assinatura.
"""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.functions import Now
from django.utils import timezone


class Room(models.Model):
    name = models.CharField(max_length=60)
    capacity = models.PositiveIntegerField()

    class Meta:
        verbose_name = "sala"
        verbose_name_plural = "salas"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ScreeningQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Screening.Status.PUBLISHED)

    def upcoming(self):
        return self.filter(starts_at__gt=timezone.now())

    def sellable(self):
        """Sessões que um cliente pode efetivamente comprar agora."""
        return self.published().upcoming()


class Screening(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        PUBLISHED = "published", "Publicada"
        CANCELLED = "cancelled", "Cancelada"

    # PROTECT: apagar um filme com sessão agendada deve falhar, não cascatear.
    movie = models.ForeignKey(
        "catalog.Movie", related_name="screenings", on_delete=models.PROTECT
    )
    room = models.ForeignKey(Room, related_name="screenings", on_delete=models.PROTECT)
    starts_at = models.DateTimeField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ScreeningQuerySet.as_manager()

    class Meta:
        verbose_name = "sessão"
        verbose_name_plural = "sessões"
        ordering = ["starts_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "starts_at"],
                name="uma_sessao_por_sala_e_horario",
            ),
        ]
        indexes = [
            # Exatamente o filtro da consulta de elegibilidade ao destaque.
            models.Index(fields=["status", "starts_at"], name="idx_sessao_status_inicio"),
        ]

    def __str__(self):
        return f"{self.movie.title} — {self.starts_at:%d/%m/%Y %H:%M}"

    @property
    def seats_taken(self):
        """Assentos ocupados por reserva viva.

        Valor derivado por consulta, nunca coluna materializada — foi assim
        que a 004 escreveu esta propriedade prevendo a feature de reserva, e
        é por isso que a 007 pôde preenchê-la sem migração de dados.

        Reserva vencida não conta: a liberação é por consulta, sem depender
        de rotina agendada ter passado. Reserva PAGA conta sempre — o lugar
        vendido não volta ao estoque no vencimento original.

        A regra vem de `Reservation.OCUPANDO`, e é consumida daqui, não
        copiada: ver o comentário de lá.
        """
        return self.reserved_seats.filter(
            reservation__in=Reservation.objects.filter(Reservation.OCUPANDO)
        ).count()

    @property
    def has_available_seats(self):
        return self.seats_taken < self.room.capacity


class Seat(models.Model):
    """Um lugar físico da sala. O mesmo em todas as sessões dela."""

    class Kind(models.TextChoices):
        COMMON = "common", "Comum"
        ACCESSIBLE = "accessible", "Acessibilidade"

    room = models.ForeignKey(Room, related_name="seats", on_delete=models.CASCADE)
    row = models.CharField(max_length=2)
    number = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.COMMON)

    class Meta:
        verbose_name = "assento"
        verbose_name_plural = "assentos"
        ordering = ["row", "number"]
        constraints = [
            models.UniqueConstraint(
                fields=["room", "row", "number"],
                name="unico_lugar_por_posicao_na_sala",
            ),
        ]

    def __str__(self):
        return f"{self.row}{self.number}"

    @property
    def label(self):
        return f"{self.row}{self.number}"


class Reservation(models.Model):
    """Intenção de compra de um cliente para uma sessão.

    É a unidade que segue para o pagamento: um cliente comprando três
    lugares tem uma reserva, não três.
    """

    class Status(models.TextChoices):
        HELD = "held", "Reservada"
        EXPIRED = "expired", "Expirada"
        CANCELLED = "cancelled", "Cancelada"
        # Terminal: não há estorno nem cancelamento de compra nesta feature.
        PAID = "paid", "Paga"

    screening = models.ForeignKey(
        Screening, related_name="reservations", on_delete=models.PROTECT
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL, related_name="reservations", on_delete=models.PROTECT
    )
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    expires_at = models.DateTimeField()

    # A idempotência é resolvida por esta constraint, nunca por consulta
    # prévia: "já existe reserva parecida?" é justamente o padrão que a
    # concorrência quebra — duas requisições verificam, nenhuma encontra,
    # ambas criam.
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    # A regra de ocupação viva, em UM lugar só.
    #
    # Antes da 008 ela era só o prazo, e estava escrita TRÊS vezes: aqui via
    # `Screening.seats_taken`, em `selectors.ocupacoes_vivas` e em Python
    # dentro de `services/reservas._liberar_ou_recusar`. Uma regra de dois
    # termos copiada três vezes é uma regra que alguém corrige em duas.
    #
    # Os dois termos são necessários e nenhum basta:
    #   - só o prazo  → a reserva PAGA não mexe em `expires_at`, então dez
    #                   minutos depois da compra o lugar VENDIDO volta ao
    #                   estoque — e `_liberar_ou_recusar` apaga a ocupação
    #                   dele sem violar constraint nenhuma, porque apagar
    #                   antes de inserir é operação legal para o banco;
    #   - só o status → o lugar ficaria preso até alguém marcar a expiração,
    #                   e marcar exigiria a rotina agendada que a 007 evitou
    #                   justamente para não ter a janela que ela cria.
    #
    # `Now()` é a função do banco, não `timezone.now()`: este `Q` é avaliado
    # uma vez na importação do módulo, e um instante do Python congelaria o
    # relógio na subida do processo.
    OCUPANDO = Q(status=Status.PAID) | Q(expires_at__gt=Now())

    class Meta:
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reserva {self.pk} — {self.customer} — {self.screening}"

    @property
    def is_expired(self):
        """Vencimento é sempre lido do relógio, nunca do campo `status`.

        `status` é registro histórico e serve à feature de pagamento para
        distinguir "venceu" de "foi paga". Ele não é o que libera o lugar —
        se fosse, haveria uma janela entre o vencimento e a rotina que o
        marcasse, e nessa janela o lugar apareceria tomado sem estar.
        """
        return self.expires_at <= timezone.now()


class ReservedSeat(models.Model):
    """A ocupação de um lugar por uma reserva.

    É esta tabela que carrega o Princípio II.
    """

    reservation = models.ForeignKey(
        Reservation, related_name="seats", on_delete=models.CASCADE
    )
    # Denormalizado de propósito: `reservation.screening` já tem a
    # informação, mas a constraint precisa das duas colunas na MESMA tabela,
    # e nem o Django nem o PostgreSQL declaram unicidade através de
    # travessia de chave estrangeira. Preenchido num único ponto do código
    # (services/reservas.py) e nunca editado depois.
    screening = models.ForeignKey(
        Screening, related_name="reserved_seats", on_delete=models.PROTECT
    )
    seat = models.ForeignKey(Seat, related_name="occupations", on_delete=models.PROTECT)

    class Meta:
        verbose_name = "assento reservado"
        verbose_name_plural = "assentos reservados"
        constraints = [
            # A garantia do Princípio II. ABSOLUTA, sem `condition`.
            #
            # O índice parcial sobre "reserva viva" seria a saída natural
            # para conciliar com a expiração e é IMPOSSÍVEL: o PostgreSQL
            # exige predicado imutável em índice parcial, e now() não é.
            #
            # A conciliação está em services/reservas.py: a linha vencida é
            # apagada sob SELECT FOR UPDATE, dentro da própria transação de
            # reserva. Ver R1 e R2 em specs/007-seat-selection/research.md.
            models.UniqueConstraint(
                fields=["screening", "seat"],
                name="unico_assento_por_sessao",
            ),
        ]

    def __str__(self):
        return f"{self.seat} — sessão {self.screening_id}"


class Payment(models.Model):
    """Uma tentativa de cobrança simulada sobre uma reserva.

    Sem transação financeira real e sem provedor externo (FR-005). O
    desfecho é decidido pelo número do cartão, por tabela fixa em
    `settings.PAYMENT_TEST_CARDS` — determinístico, nunca por sorteio, porque
    a constitution exige que os dois caminhos sejam exercitáveis pelo
    avaliador e recusa por sorteio não é exercitável nem testável.
    """

    class Status(models.TextChoices):
        APPROVED = "approved", "Aprovado"
        DECLINED = "declined", "Recusado"

    class DeclineReason(models.TextChoices):
        """Chave, não frase.

        A redação em português vive na camada de apresentação. Motivo gravado
        como texto livre diverge da tela na primeira revisão de redação.
        """

        INSUFFICIENT_FUNDS = "saldo_insuficiente", "Saldo insuficiente"
        EXPIRED_CARD = "cartao_expirado", "Cartão expirado"
        ISSUER_DECLINED = "recusado_pelo_emissor", "Recusado pelo emissor"

    reservation = models.ForeignKey(
        Reservation, related_name="payments", on_delete=models.PROTECT
    )
    status = models.CharField(max_length=12, choices=Status.choices)
    decline_reason = models.CharField(
        max_length=32, choices=DeclineReason.choices, blank=True, default=""
    )
    # Congelado no instante da cobrança, calculado pelo servidor a partir do
    # preço da sessão e da quantidade de lugares. Valor vindo do cliente não é
    # aceito em nenhuma forma, nem para conferência (FR-003).
    amount = models.DecimalField(max_digits=8, decimal_places=2)

    # SÓ ISTO do cartão. Não há cobrança real, então guardar o número não tem
    # nem a desculpa de recobrança — seria risco puro sem contrapartida
    # (FR-011). O número completo e o CVV não são persistidos em lugar nenhum.
    card_last4 = models.CharField(max_length=4)
    card_brand = models.CharField(max_length=16)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "pagamento"
        verbose_name_plural = "pagamentos"
        ordering = ["-created_at"]
        constraints = [
            # Metade da garantia do Princípio II nesta feature.
            #
            # ÍNDICE PARCIAL, e aqui ele é possível — ao contrário da 007.
            # Lá o predicado seria `expira_em > now()`, e o PostgreSQL exige
            # predicado IMUTÁVEL em índice parcial: `now()` não é, e a
            # constraint teve de ser absoluta. Aqui o predicado é uma coluna
            # comparada a um literal, que é imutável.
            #
            # É essa diferença que permite guardar TODAS as tentativas
            # recusadas, como o FR-012 exige, sem que a unicidade as proíba.
            # Uma `UNIQUE(reservation)` sem condição impediria a segunda
            # tentativa — justamente o que a US2 promete ao cliente.
            models.UniqueConstraint(
                fields=["reservation"],
                condition=models.Q(status="approved"),
                name="um_pagamento_aprovado_por_reserva",
            ),
        ]

    def __str__(self):
        return f"Pagamento {self.pk} — reserva {self.reservation_id} — {self.status}"


class Ticket(models.Model):
    """O direito de UMA pessoa entrar na sala.

    Um ingresso por LUGAR reservado, nunca um por reserva: quem entra é uma
    pessoa por assento, e é o ingresso que a portaria lê na catraca. Uma
    reserva de três lugares gera três ingressos com QR próprio (FR-014).

    NENHUM campo `used`/`used_at` aqui, e a ausência é deliberada: a
    transição para "utilizado" e a garantia de validação única nascem juntas
    na feature da portaria — o mesmo cuidado que a 007 teve com `ReservedSeat`
    e sua constraint. Acrescentar a coluna agora criaria um estado que nada
    transiciona e nada protege.
    """

    # Identidade pública, e é ela que vai dentro do código assinado.
    # UUID e não a chave primária: sequencial revelaria quantos ingressos
    # existem e convidaria a tentar o vizinho (FR-032).
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    # A OUTRA METADE da garantia. `OneToOneField` É `UNIQUE` na coluna, e é
    # ABSOLUTA, sem predicado: nenhuma sequência de operações produz dois
    # ingressos para o mesmo assento reservado.
    #
    # NÃO TROCAR POR ForeignKey. A troca não muda uma linha de lógica visível
    # e remove a garantia inteira — é a mesma classe de erro que enfraquecer
    # a constraint da 007 com um `condition`.
    #
    # A ligação é com a ocupação, e não com (reserva, assento), porque
    # `ReservedSeat` já é a linha que diz "este lugar, nesta sessão, é desta
    # reserva" e já carrega a constraint da 007. Pendurar o ingresso nela faz
    # a unicidade do ingresso herdar a unicidade do assento.
    reserved_seat = models.OneToOneField(
        ReservedSeat, related_name="ticket", on_delete=models.PROTECT
    )
    payment = models.ForeignKey(Payment, related_name="tickets", on_delete=models.PROTECT)
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "ingresso"
        verbose_name_plural = "ingressos"
        # Ordenação por LUGAR, que é a certa dentro de UMA compra: dois
        # ingressos da mesma reserva se leem como "F11 e F12".
        #
        # A lista de "Meus ingressos" da 009 precisa da outra ordenação — por
        # horário de sessão — e a declara explicitamente. Herdar esta daria
        # uma lista ordenada por poltrona: plausível, e errada.
        ordering = ["reserved_seat__seat__row", "reserved_seat__seat__number"]

    def __str__(self):
        return f"Ingresso {self.public_id} — {self.reserved_seat}"


class TicketShareLink(models.Model):
    """A autorização de leitura pública de UM ingresso.

    Compartilhar ingresso é entregar o direito de entrar: a página do link
    exibe o QR, porque uma página compartilhada sem ele seria decorativa. A
    consequência é assumida, não contornada — o link é CREDENCIAL AO
    PORTADOR, e daí saem as duas exigências que este modelo carrega: o token
    é não adivinhável, e o dono pode revogá-lo e gerar outro.

    O TOKEN NÃO É O CÓDIGO DO QR, e a distinção é a razão de este modelo
    existir em vez de uma coluna em `Ticket`. Revogar um link não pode
    invalidar o ingresso na catraca, e o ingresso não pode depender de link
    para valer. Dois segredos, dois ciclos de vida: este não conhece a
    `TICKET_SIGNING_KEY`, e `services/ingressos.py` não conhece este.

    E A LINHA REVOGADA NUNCA É APAGADA. É o que faz duas coisas serem
    estrutura em vez de sorte:
      - "revogado nunca volta a valer" — o token morto continua ocupando o
        espaço dele sob a `UNIQUE` da coluna, então nem o gerador nem um bug
        de reatribuição conseguem ressuscitá-lo;
      - token revogado e token inexistente respondem igual — os dois saem
        como o mesmo `None` da consulta, sem `if` nenhum decidindo.
    """

    # CASCADE, e é a única do módulo — todo o resto usa PROTECT.
    #
    # PROTECT existe onde apagar destruiria histórico de venda: ingresso,
    # pagamento, reserva. Um link não é histórico, é autorização de leitura.
    # Se um dia um ingresso for apagado, seus links TÊM de morrer junto: um
    # link sobrevivendo ao ingresso seria credencial órfã.
    ticket = models.ForeignKey(
        Ticket, related_name="share_links", on_delete=models.CASCADE
    )

    # `secrets.token_urlsafe(32)` — 256 bits, 43 caracteres. Preenchido num
    # ponto só (services/compartilhamento.py) e nunca editado depois.
    #
    # Não deriva de NADA: nem da chave primária, nem do `public_id`, nem da
    # reserva, nem do pagamento, e sobretudo nem do código assinado.
    #
    # `unique` ABSOLUTA, sem condição, incluindo os revogados — ver o
    # docstring da classe.
    token = models.CharField(max_length=64, unique=True, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    # Nulo é o estado ativo. Preenchido é terminal: não há "reativar".
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)

    class Meta:
        verbose_name = "link de compartilhamento"
        verbose_name_plural = "links de compartilhamento"
        ordering = ["-created_at"]
        constraints = [
            # ÍNDICE PARCIAL. Terceiro capítulo da mesma história, e a forma
            # muda por limitação do PostgreSQL, nunca por preferência:
            #
            #   007 — UNIQUE(sessão, assento), ABSOLUTA. O predicado natural
            #         seria `expira_em > now()`, e índice parcial exige
            #         predicado IMUTÁVEL: `now()` não é.
            #   008 — UNIQUE(reserva) WHERE aprovado, PARCIAL. `status =
            #         'approved'` é coluna comparada a literal, imutável.
            #   009 — esta. `revoked_at IS NULL` é teste de nulidade sobre
            #         coluna, imutável.
            #
            # É o `condition` que permite PRESERVAR os revogados. Uma
            # UNIQUE(ticket) sem condição impediria gerar um link novo depois
            # de revogar o anterior — justamente o que a feature promete ao
            # dono. NÃO REMOVER O `condition` "para simplificar".
            models.UniqueConstraint(
                fields=["ticket"],
                condition=models.Q(revoked_at__isnull=True),
                name="um_link_ativo_por_ingresso",
            ),
        ]

    def __str__(self):
        estado = "revogado" if self.revoked_at else "ativo"
        return f"Link {estado} — ingresso {self.ticket_id}"

    @property
    def is_active(self):
        return self.revoked_at is None
