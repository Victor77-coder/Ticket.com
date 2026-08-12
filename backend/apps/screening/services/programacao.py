"""Criar, editar, publicar e cancelar sessão — as escritas do painel.

O CONFLITO DE (SALA, HORÁRIO) VEM DO BANCO. A garantia é a constraint
`uma_sessao_por_sala_e_horario`, capturada como `IntegrityError` e reconhecida
pelo NOME. Uma consulta `Screening.objects.filter(room=..., starts_at=...).
exists()` antes do INSERT é o padrão que a concorrência quebra — as duas
requisições verificam, nenhuma encontra, ambas gravam — e este projeto já o
rejeitou três vezes (007, 008, 009). O comentário de
`Reservation.idempotency_key` o descreve por escrito.

`test_programacao_concorrencia.py` prova o resultado; a revisão de código
prova o caminho (FR-025, R4).

O QUE CANCELAR NÃO FAZ (FR-031): não estorna pagamento, não apaga ingresso,
não apaga ocupação, não mexe em `used_at`, não devolve ao estoque lugar já
pago. Muda UMA coluna: `status`.
"""
