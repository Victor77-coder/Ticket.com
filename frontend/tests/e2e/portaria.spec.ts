import { expect, test } from "@playwright/test";

/**
 * Percurso da portaria — comprar, escolher a porta, validar, e os quatro
 * desfechos.
 *
 * É o percurso que fecha o fluxo ponta a ponta do projeto: catálogo → sessão →
 * assento → pagamento → ingresso → **entrada**.
 *
 * A VALIDAÇÃO ACONTECE PELA DIGITAÇÃO, não pela câmera, e não é limitação do
 * teste: apontar uma câmera para um QR real exige hardware. A digitação produz
 * o mesmo desfecho pelo mesmo caminho de servidor, e é ela que a constitution
 * exige estar "sempre disponível" — inclusive porque a câmera não funciona
 * fora de contexto seguro, que é o cenário mais provável de demonstração.
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

const CARTAO_APROVADO = "4242424242424242";

// Em série: este percurso COMPRA e depois CONSOME ingressos, e uso é
// definitivo. Workers paralelos disputariam assento e ingresso.
test.describe.configure({ mode: "serial" });

async function entrar(page: import("@playwright/test").Page, usuario: string) {
  await page.goto("/");
  const entradaVisivel = await page
    .getByRole("link", { name: "Entrar na sua conta" })
    .count();

  if (entradaVisivel === 0) {
    // Já há sessão de outro papel: sair antes.
    await page.locator("header").getByRole("button").first().click();
    await page.getByRole("menuitem", { name: "Sair" }).click();
    await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toBeVisible();
  }

  await page.getByRole("link", { name: "Entrar na sua conta" }).click();
  await page.getByLabel("Usuário").fill(usuario);
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toHaveCount(0);
}

/**
 * Compra um ingresso numa sessão de HOJE e devolve o código e a sessão.
 *
 * Precisa ser hoje: a portaria só oferece as sessões do dia, porque é o que a
 * porta está recebendo. Uma sessão de amanhã não apareceria na lista.
 */
async function comprarIngressoDeHoje(
  page: import("@playwright/test").Page,
  request: import("@playwright/test").APIRequestContext,
) {
  const hoje = new Date().toISOString().slice(0, 10);

  const catalogo = await request.get("http://localhost:8000/api/v1/home/");
  const { rows } = (await catalogo.json()) as { rows: { movies: { slug: string }[] }[] };
  const slugs = new Set(rows.flatMap((linha) => linha.movies.map((m) => m.slug)));

  let escolhida: { id: number; livres: number } | null = null;
  for (const slug of slugs) {
    const detalhe = await request.get(`http://localhost:8000/api/v1/filmes/${slug}/`);
    if (!detalhe.ok()) continue;
    const filme = (await detalhe.json()) as {
      screenings?: { id: number; starts_at: string }[];
    };

    for (const sessao of filme.screenings ?? []) {
      if (!sessao.starts_at.startsWith(hoje)) continue;

      const mapa = await request.get(
        `http://localhost:8000/api/v1/sessoes/${sessao.id}/mapa/`,
      );
      if (!mapa.ok()) continue;
      const corpo = await mapa.json();
      const livres = corpo.fileiras.flatMap(
        (f: { assentos: { situacao: string; tipo: string }[] }) =>
          f.assentos.filter((a) => a.situacao === "livre" && a.tipo === "comum"),
      );
      if (livres.length >= 2) {
        escolhida = { id: sessao.id, livres: livres.length };
        break;
      }
    }
    if (escolhida) break;
  }

  if (!escolhida) {
    throw new Error(
      "nenhuma sessão de HOJE com lugares livres — rode `seed_demo` antes desta suíte",
    );
  }

  await page.goto(`/sessoes/${escolhida.id}`);
  await page.getByRole("button", { name: /^Fileira .*, livre$/ }).first().click();
  await page.getByRole("button", { name: "Confirmar lugares" }).click();
  await page.getByRole("link", { name: "Continuar para pagamento" }).click();

  await page.getByLabel("Número do cartão").fill(CARTAO_APROVADO);
  await page.getByLabel("Nome impresso no cartão").fill("MARIA DE SOUZA");
  await page.getByLabel("Validade").fill("122030");
  await page.getByLabel("Código de segurança").fill("123");
  await page.getByRole("button", { name: /Pagar e receber ingressos/ }).click();

  await expect(
    page.getByRole("status").filter({ hasText: /Pagamento aprovado/ }),
  ).toBeVisible();

  const codigo = await page.locator("code").first().innerText();
  return { codigo, sessaoId: escolhida.id };
}

async function validar(page: import("@playwright/test").Page, codigo: string) {
  await page.getByLabel(/digite o código/i).fill(codigo);
  await page.getByRole("button", { name: "Validar" }).click();
}

test("comprar → escolher a porta → válido → já utilizado → inválido", async ({
  page,
  request,
}) => {
  await entrar(page, "cliente1");
  const { codigo } = await comprarIngressoDeHoje(page, request);

  // A ENTRADA JÁ POUSA NA TELA DE TRABALHO. A portaria tem uma tela só e não
  // navega pelo site — entrar e cair no catálogo de filmes seria cair no lugar
  // errado. Nenhum `goto` aqui: se o pouso quebrar, este teste quebra.
  await entrar(page, "portaria");
  await expect(page).toHaveURL(/\/portaria$/);

  // --- A sessão da porta vem ANTES de qualquer leitura ---
  await expect(
    page.getByRole("heading", { name: /Qual sessão esta porta está recebendo/ }),
  ).toBeVisible();
  await expect(page.getByLabel(/digite o código/i)).toHaveCount(0);

  await page.getByRole("button").filter({ hasText: /Sala/ }).first().click();
  await expect(page.getByText("Esta porta está recebendo")).toBeVisible();

  // A digitação está visível MESMO com a câmera como caminho principal.
  await expect(page.getByLabel(/digite o código/i)).toBeVisible();

  // --- Campo vazio: aviso de preenchimento, não "inválido" ---
  //
  // Filtrado pelo texto: o Next mantém um `role="alert"` vazio na página (o
  // anunciador de rota), e um localizador só por papel pega os dois. É a mesma
  // armadilha que o e2e de pagamento já tinha registrado.
  await page.getByRole("button", { name: "Validar" }).click();
  await expect(
    page.getByRole("alert").filter({ hasText: /Apresente ou digite um código/ }),
  ).toBeVisible();

  // --- Inválido ---
  await validar(page, `${codigo.slice(0, -1)}X`);
  await expect(
    page.getByRole("heading", { name: "Ingresso não reconhecido" }),
  ).toBeVisible();

  // --- Válido, ou sessão errada se a porta escolhida for outra ---
  await validar(page, codigo);
  const titulo = page.locator("h2").first();
  await expect(titulo).toBeVisible();

  if ((await titulo.innerText()) === "Ingresso de outra sessão") {
    // A porta escolhida não era a do ingresso. Troca e confirma que o
    // ingresso NÃO foi consumido pela recusa.
    await page.getByRole("button", { name: "Trocar de porta" }).click();
    const opcoes = page.getByRole("button").filter({ hasText: /Sala/ });
    const quantas = await opcoes.count();
    for (let i = 0; i < quantas; i += 1) {
      await opcoes.nth(i).click();
      await validar(page, codigo);
      if ((await page.locator("h2").first().innerText()) === "Pode entrar") break;
      await page.getByRole("button", { name: "Trocar de porta" }).click();
    }
  }

  await expect(page.getByRole("heading", { name: "Pode entrar" })).toBeVisible();

  // --- Já utilizado, na segunda apresentação ---
  await validar(page, codigo);
  await expect(page.getByRole("heading", { name: /já foi usado/i })).toBeVisible();
  // `exact`: a frase do desfecho também contém "usado às".
  await expect(page.getByText("Usado às", { exact: true })).toBeVisible();
});

test("a tela cabe em 320px e o desfecho continua legível", async ({ page }) => {
  // A portaria é usada EM PÉ, com uma mão no celular da pessoa. O desfecho
  // precisa ser lido a um braço de distância (FR-019), e a tela não pode
  // exigir rolagem lateral.
  await entrar(page, "portaria");
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/portaria");

  const semRolagemLateral = () =>
    page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );

  expect(await semRolagemLateral()).toBe(true);

  await page.getByRole("button").filter({ hasText: /Sala/ }).first().click();
  expect(await semRolagemLateral()).toBe(true);
  await expect(page.getByLabel(/digite o código/i)).toBeVisible();

  // Um desfecho qualquer serve para medir o título.
  await page.getByLabel(/digite o código/i).fill("codigo:que:nao:confere");
  await page.getByRole("button", { name: "Validar" }).click();

  const titulo = page.getByRole("heading", { name: "Ingresso não reconhecido" });
  await expect(titulo).toBeVisible();
  expect(await semRolagemLateral()).toBe(true);

  // Título grande o bastante para leitura à distância.
  const tamanho = await titulo.evaluate(
    (el) => parseFloat(getComputedStyle(el).fontSize),
  );
  expect(tamanho).toBeGreaterThanOrEqual(24);
});

test("o menu da conta também leva à validação", async ({ page }) => {
  // O pouso resolve a primeira vez. O item do menu é o que devolve o porteiro
  // à tela dele depois de ele ter navegado para qualquer outro lugar.
  await entrar(page, "portaria");
  await page.goto("/");

  await page.locator("header").getByRole("button").first().click();
  await page.getByRole("menuitem", { name: "Validar ingressos" }).click();

  await expect(page).toHaveURL(/\/portaria$/);
});

test("papel errado lê a explicação e não é mandado à entrada", async ({ page }) => {
  await entrar(page, "cliente1");
  await page.goto("/portaria");

  await expect(page.getByRole("heading", { name: "Esta área é da portaria" })).toBeVisible();
  await expect(page).toHaveURL(/\/portaria$/);
});

test("visitante sem sessão é conduzido à entrada", async ({ browser }) => {
  const anonimo = await browser.newContext();
  const visitante = await anonimo.newPage();

  await visitante.goto("/portaria");

  await expect(visitante).toHaveURL(/\/entrar\?next=%2Fportaria|\/entrar\?next=\/portaria/);
  await anonimo.close();
});
