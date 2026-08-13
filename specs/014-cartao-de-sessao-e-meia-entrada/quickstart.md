# Quickstart: Cartão de Sessão e Meia-Entrada

**Feature**: 014 | **Date**: 2026-08-13

Percursos de verificação manual. Os automatizados provam as garantias; estes provam que a coisa é
usável por gente.

## Preparo

```bash
docker compose up -d
docker compose exec backend python manage.py seed_demo --force
```

Cliente: `cliente1` / `desafio2026`. Interface em <http://localhost:5003>.

Para os percursos 3 a 5, tenha à mão um filme com sessões em **duas salas** e alguma com lugares já
vendidos — o `seed_demo` entrega isso.

---

## Percurso 1 — O cartão substituiu a lista (P1)

1. Abra um filme com sessões em duas salas no mesmo dia.
2. **Espere ver**: dois cartões, cada um com o nome da sala no cabeçalho, régua abaixo do cabeçalho,
   e os horários daquela sala dentro dele.
3. No topo de cada cartão, à direita: **Assentos** e **Preços**, com o texto visível.
4. Confira que um horário esgotado continua distinguível **sem olhar a cor** — tire uma captura e
   converta para escala de cinza se tiver dúvida.
5. Acione um horário disponível.
6. **Espere**: chegar ao mapa de assentos daquela sessão, como antes desta feature.

**Falha se**: as salas se misturarem num bloco só, as ações aparecerem só como ícone, ou o caminho
para o mapa mudar.

---

## Percurso 2 — Só pelo teclado (P1, P2, P3)

Sem tocar no mouse, do começo ao fim.

1. Na página do filme, tabule até a ação **Assentos** de um cartão.
2. Acione com `Enter`.
3. **Espere**: o painel abre e o foco entra nele.
4. Tabule algumas vezes. **Espere**: o foco circula **dentro** do painel e nunca escapa para a
   página atrás.
5. Pressione `Esc`.
6. **Espere**: o painel fecha e o foco volta **para a ação Assentos**, não para o topo da página.
7. Repita tudo com **Preços**.

**Falha se**: o foco escapar do painel, ou voltar para outro lugar depois de fechar. É a falha mais
comum em modal, e é invisível para quem usa mouse.

---

## Percurso 3 — Espiar a lotação (P2)

1. Escolha uma sessão que já tenha lugares vendidos.
2. Acione **Assentos**.
3. **Espere**: o desenho da sala com livres e ocupados distinguíveis sem depender de cor, e a
   quantidade de lugares livres.
4. Confira o número contra o mapa real: abra o mapa daquela sessão em outra aba e conte.
5. Volte ao painel e acione **Escolher lugares**.
6. **Espere**: chegar ao mapa daquela mesma sessão.
7. Tente acionar um assento **dentro do painel**.
8. **Espere**: nada acontece. O painel é prévia, não seleção.

**Também verifique**: numa sessão esgotada, o painel diz que não há lugares e **não** oferece o
caminho para escolher.

---

## Percurso 4 — A tabela de preços (P3)

1. Acione **Preços** num cartão.
2. **Espere**: "Inteira R$ 32,00" e "Meia R$ 16,00" (valores conforme a sessão), mais a frase de que
   a meia é conferida na entrada mediante documento.
3. Abra o painel de uma sessão com preço diferente.
4. **Espere**: valores diferentes — cada tabela mostra o preço da **sua** sessão.

---

## Percurso 5 — Comprar uma meia e uma inteira (P4)

Este é o percurso que prova a metade cara da feature.

1. Entre como `cliente1` e abra o mapa de uma sessão de R$ 32,00.
2. Selecione **dois** lugares.
3. **Espere**: o resumo mostra os dois como **inteira**, total R$ 64,00. O padrão nunca é meia.
4. Marque **um** deles como meia.
5. **Espere**: o total exibido passa a **R$ 48,00**.
6. Confirme a reserva.
7. **Espere**: a tela de pagamento mostra **R$ 48,00** — o mesmo valor, agora vindo do servidor.
8. Pague com um cartão aprovado (ver README).
9. **Espere**: dois ingressos, um declarando **inteira** e outro **meia**.
10. Abra **Meus ingressos**.
11. **Espere**: os dois ingressos com os tipos corretos.

**Falha se**: o total da tela de pagamento divergir do exibido na seleção. Isso significa que a
prévia do navegador e a conta do servidor discordam — ver R6.

---

## Percurso 6 — A meia na portaria (P4, FR-024)

**É o percurso que protege a fronteira que a constitution fixa.**

1. Com o ingresso de **meia** do percurso 5, entre como `portaria` / `desafio2026`.
2. Escolha a sessão correspondente.
3. Valide o código do ingresso de meia.
4. **Espere**: desfecho **pode entrar** — o mesmo de um ingresso de inteira —, com o tipo visível
   como informação para o operador pedir o documento.
5. Valide o mesmo código de novo.
6. **Espere**: **já utilizado**, com a hora do primeiro uso.

**Falha se**: aparecer qualquer desfecho que não seja um dos quatro, ou se a meia for barrada por
falta de documento. A plataforma **vende**; quem **confere** é a pessoa na porta.

---

## Percurso 7 — O centavo ímpar (FR-018)

Precisa de uma sessão de preço com centavo ímpar. Crie uma pelo painel do organizador:

1. Entre como `organizador`, vá a **Programação** e programe uma sessão de **R$ 25,01**. Publique.
2. Como cliente, abra **Preços** naquela sessão.
3. **Espere**: "Meia R$ 12,50" — arredondado **para baixo**, em favor de quem compra.
4. Compre uma meia nessa sessão.
5. **Espere**: o valor cobrado é exatamente **R$ 12,50**, o mesmo exibido.

**Falha se**: exibido e cobrado divergirem em um centavo. É o defeito que o R3 existe para impedir.

---

## O que não dá para verificar à mão

- **A corrida de duas compras simultâneas com tipos mistos.** Precisa de threads:
  `test_payment_concurrency.py`.
- **A ausência da fórmula antiga.** É busca no código, não percurso: `price *` não pode aparecer no
  `backend/` ao fim da feature (`T-DONO`).
- **A concordância entre o espelho do navegador e o servidor.** Tabela de casos compartilhada entre
  `test_precos.py` e `meia.test.ts`.
