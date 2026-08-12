"""A geometria da sala — o ÚNICO lugar onde ela vive.

Até a 013 esta regra morava dentro de `seed_demo._seed_seats` e
`_posicoes_da_sala`. O painel do organizador precisa dela, e copiá-la seria
criar duas verdades sobre onde ficam os lugares de acessibilidade — que
divergem na primeira correção, porque a correção mais provável é justamente a
mais sutil: o que fazer quando a última fileira é menor que a cota.

A regra foi EXTRAÍDA, não duplicada (FR-017). `seed_demo` passou a chamar
daqui, e `test_sala_paridade_seed.py` compara lugar a lugar o que os dois
caminhos produzem.

A FRONTEIRA QUE A EXTRAÇÃO NÃO PODE APAGAR: `posicoes_da_sala` é geometria
pura e continua TRUNCANDO capacidade acima do teto, que é o comportamento que
o seed sempre teve. A RECUSA de capacidade fora dos limites (FR-018) é
validação de entrada e mora no serializer, antes de chegar aqui. Confundir as
duas faria o seed estourar por um valor que ele hoje aceita.
"""
