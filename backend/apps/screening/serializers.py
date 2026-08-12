"""Serializers de sessão, assento e reserva.

GATE DO PRINCÍPIO IV — o mapa é público. Nenhum campo abaixo pode dizer
**quem** ocupou um lugar, nem expor dado de gestão: status da sessão,
identificador de reserva, prazo de reserva alheia, custo ou capacidade.
`contracts/reservation-api.md` lista as proibições e
`tests/test_seat_map_api.py` as verifica.
"""

from django.conf import settings
from rest_framework import serializers

from apps.catalog.models import Movie
from apps.screening.models import (
    Payment,
    Reservation,
    Room,
    Screening,
    Seat,
    Ticket,
)
from apps.screening.services import ingressos as ingressos_service
from apps.screening.services import programacao as programacao_service


class SeatSerializer(serializers.Serializer):
    """Um lugar do mapa.

    `tipo` e `situacao` são campos distintos de propósito. Um lugar de
    acessibilidade pode estar livre ou tomado como qualquer outro, e
    "selecionado" é estado do navegador — não existe no banco até virar
    reserva. Fundir os quatro estados num campo só obrigaria o front a
    desfazer a fusão.
    """

    id = serializers.IntegerField()
    numero = serializers.IntegerField(source="number")
    tipo = serializers.SerializerMethodField()
    situacao = serializers.SerializerMethodField()

    def get_tipo(self, seat):
        return "acessibilidade" if seat.kind == Seat.Kind.ACCESSIBLE else "comum"

    def get_situacao(self, seat):
        return "tomado" if seat.is_taken else "livre"


class SeatMapSerializer(serializers.Serializer):
    """O mapa completo de uma sessão, agrupado por fileira.

    O agrupamento é do servidor. Entregar uma lista plana faria o cliente
    reagrupar, e a ordem de leitura da sala passaria a depender de código de
    apresentação.

    A capacidade da sala **não** entra: é dado de gestão, pela mesma regra
    que `ScreeningSerializer` do catálogo já aplica. O cliente recebe todos
    os lugares e não precisa do número.
    """

    id = serializers.IntegerField()
    filme = serializers.SerializerMethodField()
    sala = serializers.SerializerMethodField()
    inicio = serializers.DateTimeField(source="starts_at")
    preco = serializers.DecimalField(source="price", max_digits=8, decimal_places=2)
    esgotada = serializers.SerializerMethodField()
    limite_por_reserva = serializers.SerializerMethodField()
    fileiras = serializers.SerializerMethodField()

    def get_filme(self, screening):
        return {"titulo": screening.movie.title, "slug": screening.movie.slug}

    def get_sala(self, screening):
        return {"nome": screening.room.name}

    def get_limite_por_reserva(self, screening):
        return settings.MAX_SEATS_PER_RESERVATION

    def get_esgotada(self, screening):
        """Derivado, para o front escolher o estado explicativo sem varrer.

        Só os lugares comuns contam: os de acessibilidade estão fora da venda
        comum, então uma sala com eles livres e todo o resto tomado está
        esgotada para quem compra pelo fluxo normal.
        """
        comuns = [s for s in self.context["seats"] if s.kind != Seat.Kind.ACCESSIBLE]
        return bool(comuns) and all(s.is_taken for s in comuns)

    def get_fileiras(self, screening):
        fileiras = []
        for seat in self.context["seats"]:
            if not fileiras or fileiras[-1]["letra"] != seat.row:
                fileiras.append({"letra": seat.row, "assentos": []})
            fileiras[-1]["assentos"].append(SeatSerializer(seat).data)
        return fileiras


class ReservationInputSerializer(serializers.Serializer):
    """O que a requisição de reserva pode trazer.

    A chave de idempotência é obrigatória: sem ela, uma requisição repetida
    por instabilidade de rede vira reserva duplicada, e desabilitar o botão
    no navegador não cobre esse caso.
    """

    sessao = serializers.IntegerField()
    assentos = serializers.ListField(child=serializers.IntegerField(), allow_empty=True)
    chave_idempotencia = serializers.UUIDField()


class LugarSerializer(serializers.Serializer):
    fileira = serializers.CharField(source="row")
    numero = serializers.IntegerField(source="number")


class ReservationSerializer(serializers.Serializer):
    """A reserva como o cliente dono a vê.

    Não traz `idempotency_key` nem identificação do cliente: a primeira é
    segredo do envio e a segunda não acrescenta nada a quem já sabe quem é.
    """

    id = serializers.IntegerField()
    sessao = serializers.IntegerField(source="screening_id")
    assentos = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    # Instante absoluto, nunca "faltam N segundos": o relógio do navegador
    # pode estar errado, e a contagem regressiva precisa de um alvo fixo para
    # não derivar.
    expira_em = serializers.DateTimeField(source="expires_at")
    situacao = serializers.SerializerMethodField()

    def _assentos(self, reserva):
        return [o.seat for o in reserva.seats.all()]

    def get_assentos(self, reserva):
        return LugarSerializer(self._assentos(reserva), many=True).data

    def get_total(self, reserva):
        return f"{reserva.screening.price * len(self._assentos(reserva)):.2f}"

    def to_representation(self, reserva):
        """AMPLIA a resposta da 007, nunca a altera.

        Todo campo que a 007 entregava continua com o mesmo nome e o mesmo
        significado (FR-050); `pagamento` e `ingressos` só APARECEM quando a
        reserva está paga. É isto que faz a confirmação sobreviver a um
        recarregamento e que permite a `/pagamento/[id]` mostrar os ingressos
        em vez de um formulário inútil (R13).

        `expira_em` continua presente numa reserva paga, com o valor original
        e sem significado de prazo — reserva paga não vence. Quem decide não
        exibir contagem regressiva é o front, olhando `situacao`.
        """
        dados = super().to_representation(reserva)

        if reserva.status != Reservation.Status.PAID:
            return dados

        aprovado = reserva.payments.filter(status=Payment.Status.APPROVED).first()
        if aprovado is None:
            # Estado que o Princípio II proíbe e as constraints impedem. Se
            # aparecer, é sintoma de corrupção — e a resposta não inventa
            # ingresso para disfarçar.
            return dados

        dados["pagamento"] = PaymentSerializer(aprovado).data
        dados["ingressos"] = TicketSerializer(
            Ticket.objects.filter(payment=aprovado)
            .select_related(
                "reserved_seat__seat",
                "reserved_seat__screening__movie",
                "reserved_seat__screening__room",
            )
            .order_by("reserved_seat__seat__row", "reserved_seat__seat__number"),
            many=True,
        ).data
        return dados

    def get_situacao(self, reserva):
        """`paga` vem ANTES de `expirada`, e a ordem não é arbitrária.

        Uma reserva paga cujo prazo original já passou continua respondendo
        `True` em `is_expired` — a pergunta "o prazo venceu?" tem mesmo essa
        resposta. Perguntar primeiro se está paga é o que impede a compra
        concluída de aparecer como expirada dez minutos depois. É a mesma
        precedência que `Reservation.OCUPANDO` aplica no banco.
        """
        if reserva.status == Reservation.Status.PAID:
            return "paga"
        return "expirada" if reserva.is_expired else "reservada"


class PaymentInputSerializer(serializers.Serializer):
    """Os dados digitados do cartão.

    Nenhum destes campos é persistido: só os quatro últimos dígitos e a
    bandeira sobrevivem à requisição (FR-011). O serializer não é ecoado em
    resposta de erro — `tests/test_payment_api.py` fixa a ausência.

    A validação de forma (Luhn, mês válido) fica no serviço, junto da decisão,
    para que a fronteira entre "preenchimento inválido" e "cartão recusado"
    tenha um dono só.
    """

    # Todos aceitam vazio DE PROPÓSITO. O campo obrigatório de verdade é
    # conferido no serviço, que responde em português dizendo qual é — se a
    # obrigatoriedade morasse aqui, o DRF recusaria antes com a frase dele,
    # em inglês, e o Princípio V seria violado por um caminho que nenhuma
    # revisão de texto alcança.
    numero = serializers.CharField(max_length=32, allow_blank=True, default="")
    nome = serializers.CharField(max_length=80, allow_blank=True, default="")
    validade = serializers.CharField(max_length=10, allow_blank=True, default="")
    cvv = serializers.CharField(max_length=4, allow_blank=True, default="")


class PaymentSerializer(serializers.Serializer):
    """A cobrança aprovada, como o comprador a vê.

    Sem `id`: a identidade interna do pagamento não serve a nada no cliente e
    só amplia a superfície.
    """

    cartao_final = serializers.CharField(source="card_last4")
    bandeira = serializers.CharField(source="card_brand")
    total = serializers.SerializerMethodField()
    pago_em = serializers.DateTimeField(source="created_at")

    def get_total(self, pagamento):
        return f"{pagamento.amount:.2f}"


class TicketSerializer(serializers.Serializer):
    """Um ingresso — um por LUGAR, nunca um por reserva.

    `codigo` e `qr_svg` andam juntos de propósito: o código é a verdade
    assinada, o QR é uma representação dele. O texto aparece na tela junto da
    imagem porque a portaria exige digitação manual como alternativa sempre
    disponível, e um QR que não carrega não pode deixar a pessoa sem nada
    (FR-038).

    Sem `id` interno: a identidade pública já vai dentro do código assinado.
    """

    codigo = serializers.SerializerMethodField()
    qr_svg = serializers.SerializerMethodField()
    filme = serializers.SerializerMethodField()
    sessao = serializers.SerializerMethodField()
    sala = serializers.SerializerMethodField()
    assento = serializers.SerializerMethodField()

    def _codigo(self, ingresso):
        # Derivado, nunca armazenado: guardá-lo numa coluna criaria a chance
        # de a coluna e a chave discordarem depois de uma rotação.
        return ingressos_service.assinar_codigo(
            ingresso.public_id, ingresso.reserved_seat.screening_id
        )

    def get_codigo(self, ingresso):
        return self._codigo(ingresso)

    def get_qr_svg(self, ingresso):
        return ingressos_service.qr_data_uri(self._codigo(ingresso))

    def get_filme(self, ingresso):
        return ingresso.reserved_seat.screening.movie.title

    def get_sessao(self, ingresso):
        return ingresso.reserved_seat.screening.starts_at

    def get_sala(self, ingresso):
        return ingresso.reserved_seat.screening.room.name

    def get_assento(self, ingresso):
        return LugarSerializer(ingresso.reserved_seat.seat).data


class MeuIngressoSerializer(serializers.Serializer):
    """O ingresso como o DONO o vê. COMPÕE `TicketSerializer`, não o estende.

    A composição é a decisão de projeto mais importante deste arquivo na 009,
    e não é sobre o que `TicketSerializer` expõe hoje — hoje ele expõe
    exatamente o recorte que a página pública autoriza. É sobre a PRESSÃO DE
    CRESCIMENTO.

    A área do dono vai querer campos: estado do link, situação da sessão,
    identificador do ingresso. Se eles forem parar em `TicketSerializer`,
    aparecem na PÁGINA PÚBLICA no mesmo commit, em silêncio — e o teste de
    não vazamento vira a única coisa entre isso e um vazamento.

    Com dois serializers, quem precisa de um campo novo o acrescenta AQUI,
    porque é aqui que está trabalhando. A pressão aponta para o lado que não
    é público, por construção.

    `TicketSerializer` NÃO PODE GANHAR CAMPO NENHUM.

    `grupo` vem do contexto, e não é calculado aqui: quem separou futuros de
    passados foi a consulta, com o relógio do BANCO. Recalcular no Python
    introduziria um segundo relógio e uma janela de microssegundos em que um
    ingresso do grupo dos futuros se descreveria como passado.
    """

    def to_representation(self, ingresso):
        dados = TicketSerializer(ingresso).data
        sessao = ingresso.reserved_seat.screening

        # A identidade pública, que é o que endereça o ingresso nas rotas do
        # dono. Fora da resposta pública de propósito: lá seria identificador
        # reaproveitável e, pior, a metade não secreta do código assinado.
        dados["id"] = str(ingresso.public_id)
        dados["grupo"] = self.context.get("grupo", "futuro")
        # Fato ORTOGONAL ao horário: uma sessão cancelada que ainda não
        # começou continua no grupo dos futuros, com o aviso. Fundir os dois
        # num campo só obrigaria o front a desfazer a fusão.
        dados["sessao_cancelada"] = sessao.status == Screening.Status.CANCELLED
        return dados


class SessaoDaPortaSerializer(serializers.Serializer):
    """Uma sessão que a portaria pode receber.

    Filme, horário e sala — o que o operador precisa para reconhecer a porta
    em que está. Nada de preço, capacidade ou status: é o mesmo recorte que o
    mapa público da 007 já aplica, e a portaria não gerencia nada.
    """

    id = serializers.IntegerField()
    filme = serializers.SerializerMethodField()
    inicio = serializers.DateTimeField(source="starts_at")
    sala = serializers.SerializerMethodField()

    def get_filme(self, sessao):
        return sessao.movie.title

    def get_sala(self, sessao):
        return sessao.room.name


class ValidacaoInputSerializer(serializers.Serializer):
    """O que a portaria envia.

    `codigo` é EXATAMENTE o que a 008 emite e a 009 exibe. Nenhum segundo
    formato existe.

    `sessao` é a sessão da porta, escolhida pelo operador. Vem do cliente por
    decisão registrada (R9): a escolha é por posto, não por conta, e dois
    operadores podem usar a mesma conta do seed em portas diferentes. Não é
    escalada de privilégio — ele obteria o mesmo resultado escolhendo outra
    sessão no menu; a autorização que importa é o papel, conferida no servidor.
    """

    # `allow_blank` de propósito: o vazio é recusado pela VIEW, com frase
    # própria em português. Se a obrigatoriedade morasse aqui, o DRF recusaria
    # antes com a frase dele, em inglês — mesmo cuidado que o pagamento da 008
    # já tinha tomado.
    codigo = serializers.CharField(max_length=512, allow_blank=True, default="")
    sessao = serializers.IntegerField(required=False, allow_null=True, default=None)


class ValidacaoSerializer(serializers.Serializer):
    """O desfecho, como a portaria o vê.

    A saída é montada por `to_representation` porque cada situação carrega
    campos diferentes — e o INVÁLIDO carrega NENHUM, deliberadamente: qualquer
    detalhe a mais entregaria a quem tenta adivinhar a informação que o
    desfecho existe para negar.

    NÃO traz comprador, valor, `public_id`, id de reserva ou de pagamento. A
    portaria confere o ingresso, não a identidade de quem comprou.
    """

    def to_representation(self, resultado):
        from apps.screening.services import portaria as portaria_service

        dados = {"situacao": resultado.situacao}

        if resultado.situacao == portaria_service.INVALIDO:
            return dados

        if resultado.situacao == portaria_service.SESSAO_ERRADA:
            sessao = resultado.sessao_do_ingresso
            dados["sessao_do_ingresso"] = {
                "filme": sessao.movie.title,
                "inicio": sessao.starts_at,
                "sala": sessao.room.name,
                # Informação DENTRO do desfecho, nunca um quinto (FR-024).
                "cancelada": sessao.status == Screening.Status.CANCELLED,
            }
            return dados

        ingresso = resultado.ingresso
        sessao = resultado.sessao_do_ingresso
        dados["ingresso"] = {
            "filme": sessao.movie.title,
            "sessao": sessao.starts_at,
            "sala": sessao.room.name,
            "assento": LugarSerializer(ingresso.reserved_seat.seat).data,
        }

        if resultado.situacao == portaria_service.JA_UTILIZADO:
            # Obrigatório: é o que permite ao operador julgar se é a mesma
            # pessoa voltando ou outra com uma captura de tela (FR-021).
            dados["utilizado_em"] = resultado.utilizado_em

        return dados


def estado_do_link(link):
    """O estado do link de compartilhamento, com ou sem link.

    FUNÇÃO, e deliberadamente NÃO um `Serializer`. "Não existe link ativo" é
    um estado legítimo e frequente desta resposta, e `Serializer(None).data`
    devolve `{}` sem sequer chamar `to_representation` — o DRF curto-circuita
    instância nula. O resultado seria um corpo vazio no lugar de
    `{"ativo": false}`, e o front leria "sem link" como "resposta quebrada".

    Descoberto por teste, não por leitura. Registrado aqui para que ninguém
    "padronize" isto de volta para um serializer.

    O endereço vem COMPLETO, montado a partir de `settings.SITE_URL`. Montá-lo
    no navegador exigiria que o front soubesse a origem pública, o que erra
    atrás de proxy — e o endereço existe para ser colado num aplicativo de
    mensagens.

    Recebe o link (ou `None`), nunca o ingresso: quem chama já fez a consulta.
    """
    if link is None:
        return {"ativo": False, "endereco": None}

    base = settings.SITE_URL.rstrip("/")
    return {"ativo": True, "endereco": f"{base}/ingresso/{link.token}"}


# --- Programação do organizador (feature 013) -----------------------------
#
# ⚠️ A FRONTEIRA. Os serializers acima servem superfícies PÚBLICAS ou do dono, e
# o aviso no topo deste arquivo vale para eles sem exceção. Os de baixo servem o
# painel do organizador, e são os ÚNICOS do sistema autorizados a expor estado
# de sessão, capacidade de sala e ocupação numérica.
#
# A direção da pressão importa: quando um campo de gestão for pedido em alguma
# tela, ele nasce aqui. Nenhum campo desta seção pode migrar para cima, e
# `tests/test_seat_map_api.py`, `test_highlights_api.py` e
# `test_home_rows_api.py` continuam sendo a guarda do outro lado.


class FilmeDaGradeSerializer(serializers.Serializer):
    """O filme como o painel precisa dele: reconhecer e escolher.

    Sem sinopse, sem gêneros, sem trailers — a grade lista dezenas de linhas, e
    cada campo a mais é peso numa tela que serve para bater o olho.
    """

    id = serializers.IntegerField()
    titulo = serializers.CharField(source="title")
    poster_url = serializers.CharField(allow_null=True)


class SalaDaGradeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nome = serializers.CharField(source="name")
    lugares = serializers.SerializerMethodField()

    def get_lugares(self, room):
        """Vem da anotação da grade — nunca de `room.seats.count()`.

        A contagem por instância seria uma consulta por linha da grade, que é
        exatamente o N+1 que `grade_do_organizador` existe para evitar (R6).
        """
        return self.context.get("lugares", 0)


class SessaoDaGradeSerializer(serializers.Serializer):
    """Uma linha da grade. A ÚNICA superfície que expõe `estado` (FR-029).

    Todos os campos derivados vêm de anotações feitas em UMA consulta por
    `grade_do_organizador`. Se algum deles passar a ser calculado aqui com um
    acesso a relação, a grade volta a ser N+1 sem que nenhum teste de
    comportamento perceba.
    """

    id = serializers.IntegerField()
    estado = serializers.CharField(source="status")
    estado_rotulo = serializers.SerializerMethodField()
    filme = serializers.SerializerMethodField()
    sala = serializers.SerializerMethodField()
    inicio = serializers.DateTimeField(source="starts_at")
    preco = serializers.DecimalField(source="price", max_digits=8, decimal_places=2)
    ocupacao = serializers.IntegerField()
    a_venda = serializers.BooleanField()
    pode_editar = serializers.SerializerMethodField()
    pode_publicar = serializers.SerializerMethodField()
    pode_cancelar = serializers.SerializerMethodField()

    def get_estado_rotulo(self, screening):
        """A palavra em português vem do MODELO, não de um dicionário daqui.

        `Screening.Status` já carrega os três rótulos. Repeti-los aqui criaria
        a segunda redação de "Rascunho", e a interface distingue os estados por
        rótulo + forma — nunca só por cor (FR-029).
        """
        return screening.get_status_display()

    def get_filme(self, screening):
        return FilmeDaGradeSerializer(screening.movie).data

    def get_sala(self, screening):
        return SalaDaGradeSerializer(
            screening.room, context={"lugares": getattr(screening, "sala_lugares", 0)}
        ).data

    def get_pode_editar(self, screening):
        return screening.status == Screening.Status.DRAFT

    def get_pode_publicar(self, screening):
        """Rascunho ∧ futuro ∧ sala com lugar — as três de FR-026/FR-028.

        É CONVENIÊNCIA DE INTERFACE, para desabilitar com explicação em vez de
        esconder controle. Nunca autorização: `POST .../publicar/` revalida as
        três no servidor, e é lá que a recusa acontece (FR-037).
        """
        return (
            screening.status == Screening.Status.DRAFT
            and bool(getattr(screening, "no_futuro", False))
            and getattr(screening, "sala_lugares", 0) > 0
        )

    def get_pode_cancelar(self, screening):
        """Rascunho E publicada. Cancelar não exige ter publicado antes.

        Sem o cancelamento de rascunho, um rascunho errado ficaria na grade
        para sempre — apagar sessão está fora de escopo (FR-030).
        """
        return screening.status in (
            Screening.Status.DRAFT,
            Screening.Status.PUBLISHED,
        )


class SalaDoPainelSerializer(serializers.Serializer):
    """Uma sala na lista do painel, com o que decide se ela pode mudar.

    `lugares` é CONTADO, e pode divergir de `capacidade`: a geometria trunca no
    teto de 26 fileiras, e uma sala do seed acima disso tem menos lugares do
    que declara. Exibir `capacidade` como se fosse o mapa esconderia a
    diferença justamente na tela que existe para mostrá-la (R1).
    """

    id = serializers.IntegerField()
    nome = serializers.CharField(source="name")
    capacidade = serializers.IntegerField(source="capacity")
    lugares = serializers.IntegerField()
    acessiveis = serializers.IntegerField()
    ocupacao_viva = serializers.IntegerField()
    pode_trocar_capacidade = serializers.SerializerMethodField()

    def get_pode_trocar_capacidade(self, room):
        """`ocupacao_viva == 0` — dica de interface, nunca autorização.

        O `PATCH` revalida lendo a ocupação de novo, e o PROTECT de `Seat` é a
        rede embaixo dos dois (FR-020, R5).
        """
        return getattr(room, "ocupacao_viva", 0) == 0


class SessaoInputSerializer(serializers.Serializer):
    """O que o painel envia para criar uma sessão.

    As recusas de campo saem em português e nomeiam a próxima ação — nunca a
    frase do DRF em inglês, que no meio de uma tela de programação é texto de
    framework (Princípio V).

    AS PRÉ-CONDIÇÕES DE PUBLICAÇÃO NÃO SÃO ESCRITAS AQUI: vêm de
    `services/programacao.erros_para_publicar`, que é o mesmo lugar que a ação
    `POST .../publicar/` consulta. Duas cópias divergiriam na primeira revisão
    de redação, e a interface já tem uma terceira leitura da mesma pergunta
    (`pode_publicar`) — que é dica, e não garantia.

    O CONFLITO DE (SALA, HORÁRIO) NÃO É VALIDADO AQUI, e a ausência é
    deliberada: quem recusa é a constraint do banco, capturada no serviço. Uma
    checagem prévia melhoraria a mensagem no caminho feliz e daria a impressão
    de ser a garantia — que é exatamente o engano que a 007, a 008 e a 009 já
    documentaram (FR-025).
    """

    filme = serializers.PrimaryKeyRelatedField(
        queryset=Movie.objects.all(),
        error_messages={
            "does_not_exist": "Este filme não está no catálogo.",
            "required": "Escolha um filme.",
            "incorrect_type": "Escolha um filme.",
        },
    )
    sala = serializers.PrimaryKeyRelatedField(
        queryset=Room.objects.all(),
        error_messages={
            "does_not_exist": "Esta sala não existe.",
            "required": "Escolha uma sala.",
            "incorrect_type": "Escolha uma sala.",
        },
    )
    inicio = serializers.DateTimeField(
        error_messages={
            "required": "Informe a data e a hora.",
            "invalid": "Informe uma data e uma hora válidas.",
        }
    )
    preco = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        error_messages={
            "required": programacao_service.PRECO_INVALIDO,
            "invalid": programacao_service.PRECO_INVALIDO,
        },
    )
    publicar = serializers.BooleanField(default=False)

    def validate_preco(self, valor):
        """Zero e negativo saem com a MESMA frase que o campo ausente.

        Os três são o mesmo problema para quem está programando — não há preço
        —, e distinguir "informe" de "informe um valor maior" só acrescentaria
        redação sem acrescentar decisão.
        """
        if valor <= 0:
            raise serializers.ValidationError(programacao_service.PRECO_INVALIDO)
        return valor

    def validate(self, dados):
        if dados.get("publicar"):
            erros = programacao_service.erros_para_publicar(
                dados["sala"], dados["inicio"]
            )
            if erros:
                raise serializers.ValidationError(erros)
        return dados


class SessaoEditavelSerializer(SessaoInputSerializer):
    """A edição de um rascunho — os mesmos campos, sem `publicar`.

    Editar NÃO publica: a sessão continua em rascunho depois da alteração
    (FR-023). Publicar é uma ação com pré-condições próprias, e deixá-la
    entrar por aqui como um campo booleano esconderia essas pré-condições
    dentro de validação de formulário (R8).
    """

    publicar = None

    def get_fields(self):
        campos = super().get_fields()
        campos.pop("publicar", None)
        return campos
