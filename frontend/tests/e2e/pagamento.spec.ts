import { expect, test } from "@playwright/test";

/**
 * Percurso de pagamento — mapa → reserva → recusa → nova tentativa → ingresso.
 *
 * É o teste do Princípio I nesta feature, e cobre de propósito o caminho
 * TORTO: a recusa entra no meio do percurso, não num teste separado. A
 * constitution diz que o caminho de recusa não é opcional, e um percurso que
 * só passa pela aprovação não prova que dá para se recuperar de uma recusa.
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

const CARTAO_APROVADO = "4242424242424242";
const CARTAO_SEM_SALDO = "4000000000009995";

// Em série, e não por preferência: cada teste daqui RESERVA lugares de
// verdade na primeira sessão vendável, e quatro workers escolhendo "o
// primeiro lugar livre" disputam o mesmo assento. O 409 que apareceria seria
// o Princípio II funcionando — mas contra o próprio teste, e sem provar nada.
test.describe.configure({ mode: "serial" });

// Uma sessão com esta folga serve para os quatro testes deste arquivo, que
// consomem 2 lugares cada.
const FOLGA_SUFICIENTE = 20;

// Memo do arquivo inteiro: a descoberta custa requisições, e os quatro testes
// rodam em série na mesma sessão. Repeti-la seria pagar quatro vezes por uma
// resposta que não muda.
let sessaoEscolhida: number | null = null;

async function entrar(page: import("@playwright/test").Page, usuario = "cliente1") {
  await page.goto("/");
  await page.getByRole("link", { name: "Entrar na sua conta" }).click();

  await page.getByLabel("Usuário").fill(usuario);
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toHaveCount(0);
}

/**
 * Uma sessão que ainda tenha lugares livres de sobra.
 *
 * Escolhida pela API em vez de "a primeira do catálogo", e a razão é
 * específica desta feature: este percurso PAGA, e lugar pago é definitivo —
 * não volta ao estoque no vencimento como a reserva da 007. Rodar a suíte
 * algumas vezes esgota a primeira sessão, e a partir daí o teste falharia por
 * inventário, não por defeito. Perseguir "a primeira" seria um teste que
 * envelhece.
 *
 * O percurso pela lista de filmes já é coberto pelo e2e da 007; o que importa
 * aqui começa no mapa.
 */
async function sessaoComLugares(request: import("@playwright/test").APIRequestContext) {
  if (sessaoEscolhida !== null) return sessaoEscolhida;

  const catalogo = await request.get("http://localhost:8000/api/v1/home/");
  const { rows } = (await catalogo.json()) as {
    rows: { movies: { slug: string }[] }[];
  };

  const slugs = new Set(rows.flatMap((linha) => linha.movies.map((m) => m.slug)));

  const ids = new Set<number>();
  for (const slug of slugs) {
    const detalhe = await request.get(`http://localhost:8000/api/v1/filmes/${slug}/`);
    if (!detalhe.ok()) continue;
    const filme = (await detalhe.json()) as { screenings?: { id: number }[] };
    for (const sessao of filme.screenings ?? []) ids.add(sessao.id);
  }

  // DE TRÁS PARA A FRENTE, e é isso que separa este arquivo do e2e da 007.
  // Lá o percurso entra sempre pelo primeiro filme do catálogo e pela
  // primeira sessão dele; com o banco recém-semeado, "a sessão mais vazia"
  // seria exatamente essa, e os dois arquivos disputariam o mesmo assento em
  // paralelo. Começar pelo fim da grade é uma separação determinística, que
  // não depende de quanto cada suíte já consumiu.
  const candidatas: { id: number; livres: number }[] = [];
  for (const id of [...ids].reverse()) {
    const resposta = await request.get(`http://localhost:8000/api/v1/sessoes/${id}/mapa/`);
    if (!resposta.ok()) continue;
    const mapa = await resposta.json();
    const livres = mapa.fileiras.flatMap((f: { assentos: { situacao: string; tipo: string }[] }) =>
      f.assentos.filter((a) => a.situacao === "livre" && a.tipo === "comum"),
    );
    candidatas.push({ id, livres: livres.length });

    // Sai cedo quando acha uma sessão claramente folgada. Varrer a grade
    // inteira eram dezenas de requisições por teste contra o servidor de
    // desenvolvimento, e a fila que isso formava derrubava por timeout os
    // e2e das features anteriores rodando em paralelo — teste que quebra
    // teste alheio, sem nenhum defeito de produto envolvido.
    if (livres.length >= FOLGA_SUFICIENTE) break;
  }

  // A MAIS VAZIA, não a primeira que sirva. O e2e da 007 reserva sempre na
  // primeira sessão do catálogo, e a suíte inteira roda em paralelo — pegar
  // "a primeira que serve" faria os dois arquivos disputarem o mesmo assento.
  // O 409 daí seria o Princípio II funcionando contra o próprio teste.
  candidatas.sort((a, b) => b.livres - a.livres);

  if (!candidatas.length || candidatas[0].livres < 6) {
    throw new Error(
      "nenhuma sessão com lugares livres de sobra — rode `seed_demo` antes desta suíte",
    );
  }

  sessaoEscolhida = candidatas[0].id;
  return sessaoEscolhida;
}

async function reservarDoisLugares(
  page: import("@playwright/test").Page,
  sessaoId: number,
) {
  await page.goto(`/sessoes/${sessaoId}`);
  await expect(page).toHaveURL(/\/sessoes\/\d+/);

  // Dois lugares, não um: é o que torna visível "um ingresso POR ASSENTO".
  for (let i = 0; i < 2; i += 1) {
    await page.getByRole("button", { name: /^Fileira .*, livre$/ }).first().click();
  }

  await page.getByRole("button", { name: "Confirmar lugares" }).click();
  await expect(page.getByRole("heading", { name: "Lugares reservados" })).toBeVisible();

  await page.getByRole("link", { name: "Continuar para pagamento" }).click();
  await expect(page).toHaveURL(/\/pagamento\/\d+/);
}

/**
 * O selo de aprovação, filtrado pelo texto.
 *
 * O cabeçalho do site mantém um `role="status"` vivo e vazio para anunciar
 * navegação (feature 002), então um localizador só por papel pega os dois.
 */
function selo(page: import("@playwright/test").Page) {
  return page.getByRole("status").filter({ hasText: /Pagamento aprovado/ });
}

async function preencherCartao(
  page: import("@playwright/test").Page,
  numero: string,
) {
  await page.getByLabel("Número do cartão").fill(numero);
  await page.getByLabel("Nome impresso no cartão").fill("MARIA DE SOUZA");
  await page.getByLabel("Validade").fill("122030");
  await page.getByLabel("Código de segurança").fill("123");
  await page.getByRole("button", { name: /Pagar e receber ingressos/ }).click();
}

test("mapa → reserva → recusa → nova tentativa → ingressos com QR", async ({ page, request }) => {
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await reservarDoisLugares(page, sessao);

  // A revisão mostra o que está sendo comprado, antes de digitar qualquer coisa.
  await expect(page.getByRole("heading", { name: "Confira e pague" })).toBeVisible();
  await expect(page.getByRole("timer")).toContainText(/para concluir o pagamento/);

  // --- A recusa, de propósito e por escolha de quem testa ---
  await preencherCartao(page, CARTAO_SEM_SALDO);

  // Filtrado pelo texto: o Next mantém um `role="alert"` vazio na página (o
  // anunciador de rota), e um localizador só por papel pega os dois.
  const recusa = page.getByRole("alert").filter({ hasText: /Pagamento recusado/ });
  await expect(recusa).toContainText(/saldo suficiente/i);
  // Em português, dizendo a próxima ação — nunca código nem frase genérica.
  await expect(recusa).not.toContainText(/error|failed|went wrong/i);

  // O prazo continua correndo: a recusa não devolveu os lugares (FR-026).
  await expect(page.getByRole("timer")).toBeVisible();

  // --- A nova tentativa, dentro do prazo ---
  await preencherCartao(page, CARTAO_APROVADO);

  await expect(selo(page)).toContainText(/aprovado/i);
  await expect(page.getByRole("heading", { name: /Seus 2 ingressos/ })).toBeVisible();

  // Um ingresso POR ASSENTO (FR-014), cada um com QR e código legível.
  const ingressos = page.getByRole("listitem");
  await expect(ingressos).toHaveCount(2);
  await expect(page.getByRole("img", { name: /Código do ingresso do lugar/ })).toHaveCount(2);
  await expect(page.getByText("Código para digitação").first()).toBeVisible();
});

test("recarregar a confirmação mostra os mesmos ingressos", async ({ page, request }) => {
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await reservarDoisLugares(page, sessao);
  await preencherCartao(page, CARTAO_APROVADO);

  await expect(page.getByRole("heading", { name: /Seus 2 ingressos/ })).toBeVisible();
  const codigo = await page.locator("code").first().innerText();

  // FR-022: os ingressos vêm do servidor a cada visita, não de estado de
  // componente. Se sumissem ao recarregar, a compra teria virado algo que só
  // existe naquela aba.
  await page.reload();

  await expect(page.getByRole("heading", { name: /Seus 2 ingressos/ })).toBeVisible();
  await expect(page.locator("code").first()).toHaveText(codigo);
  // E não emitiu um segundo conjunto.
  await expect(page.getByRole("listitem")).toHaveCount(2);
});

test("voltar ao endereço de uma reserva paga leva aos ingressos, não ao formulário", async ({
  page,
  request,
}) => {
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await reservarDoisLugares(page, sessao);
  const endereco = page.url();

  await preencherCartao(page, CARTAO_APROVADO);
  await expect(selo(page)).toContainText(/aprovado/i);

  await page.goto("/");
  await page.goto(endereco);

  // R13: uma rota, quatro estados. Reserva paga nunca mostra formulário.
  await expect(page.getByRole("heading", { name: /Seus 2 ingressos/ })).toBeVisible();
  await expect(page.getByLabel("Número do cartão")).toHaveCount(0);
});

test("o visitante sem sessão é conduzido à entrada e volta ao pagamento", async ({
  page,
  request,
}) => {
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await reservarDoisLugares(page, sessao);
  const endereco = new URL(page.url()).pathname;

  // A sessão vai embora pelo cookie, e não pelo menu "Sair" do cabeçalho.
  // O que este teste precisa provar é o que acontece quando alguém SEM SESSÃO
  // abre o endereço do pagamento — sessão expirada, outro navegador, link
  // colado. Passar pelo menu amarraria este percurso ao markup da 003 e
  // testaria a saída, que já tem teste próprio lá.
  await page.context().clearCookies();

  await page.goto(endereco);

  await expect(page).toHaveURL(new RegExp(`/entrar\\?next=${endereco.replace("/", "\\/")}`));

  // A espera é necessária: o formulário de entrada envia por JavaScript, e um
  // clique antes de a página hidratar cai no envio nativo do navegador.
  await expect(page.getByRole("button", { name: "Entrar", exact: true })).toBeEnabled();
  await page.waitForFunction(() => document.readyState === "complete");

  await page.getByLabel("Usuário").fill("cliente1");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  // Volta para a MESMA reserva (FR-044).
  await expect(page).toHaveURL(new RegExp(endereco));
  await expect(page.getByRole("heading", { name: "Confira e pague" })).toBeVisible();
});
