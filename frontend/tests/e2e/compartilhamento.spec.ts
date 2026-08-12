import { expect, test } from "@playwright/test";

/**
 * Percurso do compartilhamento — comprar → achar de novo → gerar → abrir sem
 * conta → revogar → conferir que o ingresso continua válido.
 *
 * O QUE ESTE ARQUIVO PROVA E NENHUM TESTE DE UNIDADE PROVA: que a revogação
 * chega à TELA. O back-end pode estar perfeito e o link continuar abrindo, se
 * a página compartilhada for servida do cache — é a falha mais discreta desta
 * feature, e só um percurso de verdade a pega.
 *
 * A abertura do link acontece num CONTEXTO SEM SESSÃO, e não numa aba nova do
 * mesmo contexto: com o cookie do comprador junto, a página abriria de
 * qualquer jeito e o teste provaria nada sobre acesso público.
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

const CARTAO_APROVADO = "4242424242424242";

// Em série pelo mesmo motivo do e2e de pagamento: este percurso PAGA, e lugar
// pago é definitivo. Workers paralelos disputariam o mesmo assento.
test.describe.configure({ mode: "serial" });

const FOLGA_SUFICIENTE = 20;
let sessaoEscolhida: number | null = null;

/**
 * O aviso do painel de link, escopado à região.
 *
 * O cabeçalho do site mantém um `role="status"` vivo e vazio para anunciar
 * navegação (feature 002), então um localizador só por papel pega os dois. É
 * a mesma armadilha que o e2e de pagamento já tinha registrado.
 */
function avisoDoPainel(page: import("@playwright/test").Page) {
  return page
    .getByRole("region", { name: "Compartilhar este ingresso" })
    .getByRole("status");
}

/**
 * Gera um link, partindo de qualquer estado do painel.
 *
 * ESPERA O PAINEL RENDERIZAR ANTES DE DECIDIR. `isVisible()` não tem
 * auto-espera: chamado antes de a ilha cliente hidratar, devolve `false` e o
 * teste toma o galho errado — foi exatamente o que aconteceu na primeira
 * versão deste arquivo, e a falha aparecia dez linhas adiante, no clique de um
 * botão que nunca ia existir.
 *
 * Revogar antes de gerar torna o percurso REPETÍVEL: o teste abre o primeiro
 * ingresso da lista, que rodadas anteriores da suíte podem ter deixado com
 * link ativo. E exercita a revogação de graça.
 */
async function gerarLinkDoZero(page: import("@playwright/test").Page) {
  const gerar = page.getByRole("button", { name: "Gerar link" });
  const revogar = page.getByRole("button", { name: "Revogar link" });

  await expect(gerar.or(revogar)).toBeVisible();

  if (await revogar.isVisible()) {
    await revogar.click();
    await expect(avisoDoPainel(page)).toContainText(/Link revogado/);
  }

  await gerar.click();
  await expect(avisoDoPainel(page)).toContainText(/Link gerado/);
}

async function entrar(page: import("@playwright/test").Page, usuario = "cliente1") {
  await page.goto("/");
  await page.getByRole("link", { name: "Entrar na sua conta" }).click();

  await page.getByLabel("Usuário").fill(usuario);
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toHaveCount(0);
}

/**
 * Uma sessão folgada, escolhida do fim da grade para a frente.
 *
 * Mesma técnica do e2e de pagamento, e pelo mesmo motivo: os arquivos rodam em
 * paralelo, e "a primeira sessão" faria dois testes disputarem o mesmo lugar.
 * Este começa do MEIO da lista invertida para se separar também do e2e de
 * pagamento, que já começa do fim.
 */
async function sessaoComLugares(request: import("@playwright/test").APIRequestContext) {
  if (sessaoEscolhida !== null) return sessaoEscolhida;

  const catalogo = await request.get("http://localhost:8000/api/v1/home/");
  const { rows } = (await catalogo.json()) as { rows: { movies: { slug: string }[] }[] };
  const slugs = new Set(rows.flatMap((linha) => linha.movies.map((m) => m.slug)));

  const ids = new Set<number>();
  for (const slug of slugs) {
    const detalhe = await request.get(`http://localhost:8000/api/v1/filmes/${slug}/`);
    if (!detalhe.ok()) continue;
    const filme = (await detalhe.json()) as { screenings?: { id: number }[] };
    for (const sessao of filme.screenings ?? []) ids.add(sessao.id);
  }

  const ordenadas = [...ids].reverse();
  const doMeio = ordenadas.slice(Math.floor(ordenadas.length / 2));

  const candidatas: { id: number; livres: number }[] = [];
  for (const id of [...doMeio, ...ordenadas]) {
    const resposta = await request.get(`http://localhost:8000/api/v1/sessoes/${id}/mapa/`);
    if (!resposta.ok()) continue;
    const mapa = await resposta.json();
    const livres = mapa.fileiras.flatMap(
      (f: { assentos: { situacao: string; tipo: string }[] }) =>
        f.assentos.filter((a) => a.situacao === "livre" && a.tipo === "comum"),
    );
    candidatas.push({ id, livres: livres.length });
    if (livres.length >= FOLGA_SUFICIENTE) break;
  }

  candidatas.sort((a, b) => b.livres - a.livres);

  if (!candidatas.length || candidatas[0].livres < 4) {
    throw new Error(
      "nenhuma sessão com lugares livres de sobra — rode `seed_demo` antes desta suíte",
    );
  }

  sessaoEscolhida = candidatas[0].id;
  return sessaoEscolhida;
}

async function comprarUmIngresso(
  page: import("@playwright/test").Page,
  sessaoId: number,
) {
  await page.goto(`/sessoes/${sessaoId}`);
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
}

test("comprar → reencontrar → compartilhar → revogar", async ({ page, request, browser }) => {
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await comprarUmIngresso(page, sessao);

  // --- O problema que a feature resolve: sair da confirmação e voltar ---
  await page.getByRole("link", { name: "Ver em Meus ingressos" }).click();
  await expect(page).toHaveURL(/\/meus-ingressos$/);
  await expect(page.getByRole("heading", { name: "Meus ingressos" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Próximas sessões" })).toBeVisible();

  // O caminho pela navegação global também existe, e é o que o cliente usa
  // quando volta noutro dia.
  //
  // O botão da conta é localizado por posição no cabeçalho, e não por nome: o
  // nome acessível dele é o NOME DO USUÁRIO vindo do seed (feature 002/003),
  // e amarrar o teste a esse texto o quebraria na primeira vez que o seed
  // mudasse um dado de exibição.
  await page.goto("/");
  await page.locator("header").getByRole("button").first().click();
  await page.getByRole("menuitem", { name: "Meus ingressos" }).click();
  await expect(page).toHaveURL(/\/meus-ingressos$/);

  // --- Abrir o ingresso e gerar o link ---
  await page.getByRole("link", { name: /Abrir e compartilhar/ }).first().click();
  await expect(page).toHaveURL(/\/meus-ingressos\/[0-9a-f-]{36}$/);

  const codigoAntes = await page.locator("code").first().innerText();

  await gerarLinkDoZero(page);

  const endereco = await page.locator("code").last().innerText();
  expect(endereco).toContain("/ingresso/");

  // Pedir de novo devolve O MESMO endereço — nunca uma segunda credencial.
  await page.reload();
  const enderecoDeNovo = await page.locator("code").last().innerText();
  expect(enderecoDeNovo).toBe(endereco);

  // --- Abrir SEM SESSÃO NENHUMA ---
  const anonimo = await browser.newContext();
  const visitante = await anonimo.newPage();
  await visitante.goto(endereco);

  await expect(visitante.getByRole("heading", { name: "Ingresso" })).toBeVisible();
  // Escopado a `main`: o overlay de dev tools do Next também expõe um `img`,
  // e um localizador de página inteira pegaria os dois.
  await expect(visitante.locator("main").getByRole("img")).toBeVisible();
  // O QR é o mesmo ingresso, não uma imagem decorativa.
  await expect(visitante.locator("code")).toHaveText(codigoAntes);

  // E nada além do ingresso: nem o comprador, nem convite para entrar.
  const textoPublico = (await visitante.locator("main").innerText()).toLowerCase();
  for (const proibido of ["cliente1", "cartão", "r$", "reserva", "entrar"]) {
    expect(textoPublico).not.toContain(proibido);
  }

  // --- Revogar, e conferir que chega à tela ---
  await page.getByRole("button", { name: "Revogar link" }).click();
  await expect(avisoDoPainel(page)).toContainText(/Link revogado/);

  await visitante.reload();

  // A asserção que só um percurso real pega: sem `force-dynamic` na rota, o
  // banco estaria certo e ISTO continuaria mostrando o ingresso.
  await expect(visitante.getByRole("heading", { name: /não vale mais/i })).toBeVisible();
  await expect(visitante.locator("main").getByRole("img")).toHaveCount(0);

  // --- O ingresso continua valendo: os dois segredos são independentes ---
  await page.reload();
  const codigoDepois = await page.locator("code").first().innerText();
  expect(codigoDepois).toBe(codigoAntes);

  // --- Gerar outro produz endereço diferente, e o antigo continua morto ---
  await page.getByRole("button", { name: "Gerar link" }).click();
  await expect(avisoDoPainel(page)).toContainText(/Link gerado/);
  const novoEndereco = await page.locator("code").last().innerText();
  expect(novoEndereco).not.toBe(endereco);

  await visitante.goto(endereco);
  await expect(visitante.getByRole("heading", { name: /não vale mais/i })).toBeVisible();

  await visitante.goto(novoEndereco);
  await expect(visitante.getByRole("heading", { name: "Ingresso" })).toBeVisible();

  await anonimo.close();
});

test("cliente sem ingressos lê uma frase e alcança o catálogo", async ({ page }) => {
  await entrar(page, "cliente2");
  await page.goto("/meus-ingressos");

  // `cliente2` do seed não comprou nada. Se esta asserção falhar porque ele
  // acumulou compras de outras rodadas da suíte, `seed_demo` devolve o
  // cenário ao início.
  const vazio = page.getByText(/ainda não tem ingressos/i);
  const temIngressos = await page
    .getByRole("heading", { name: /Próximas sessões|Já aconteceram/ })
    .count();

  if (temIngressos === 0) {
    await expect(vazio).toBeVisible();
    await expect(page.getByRole("link", { name: /filmes em cartaz/i })).toBeVisible();
  }
});

test("as três superfícies cabem em 320px, com o QR legível", async ({ page, request }) => {
  // 320px é a largura em que SC-005 é verificado. O QR precisa continuar
  // grande o bastante para um leitor de terceiro decodificar da tela — a
  // leitura em si é conferida à mão, pelo quickstart; o que dá para
  // automatizar é o TAMANHO RENDERIZADO e a ausência de rolagem lateral.
  const sessao = await sessaoComLugares(request);
  await entrar(page);
  await page.setViewportSize({ width: 320, height: 720 });

  await page.goto("/meus-ingressos");
  const primeiro = page.getByRole("link", { name: /Abrir e compartilhar/ }).first();

  if ((await primeiro.count()) === 0) {
    await comprarUmIngresso(page, sessao);
    await page.goto("/meus-ingressos");
  }

  const semRolagemLateral = () =>
    page.evaluate(
      () => document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    );

  expect(await semRolagemLateral()).toBe(true);

  // `scrollIntoViewIfNeeded` antes de medir: `boundingBox()` devolve `null`
  // para elemento fora da viewport, e a 320px o QR fica abaixo da dobra.
  const qrDaLista = page.locator("main img").first();
  await qrDaLista.scrollIntoViewIfNeeded();
  const caixa = await qrDaLista.boundingBox();
  expect(caixa!.width).toBeGreaterThanOrEqual(128);

  // O código em texto continua INTEIRO, não truncado: é o que a portaria
  // digita quando a câmera falha, e um código cortado não serve para digitar.
  const codigo = await page.locator("main code").first().innerText();
  expect(codigo.length).toBeGreaterThan(40);
  expect(codigo).not.toContain("…");

  await page.getByRole("link", { name: /Abrir e compartilhar/ }).first().click();
  expect(await semRolagemLateral()).toBe(true);

  await gerarLinkDoZero(page);

  await page.goto(await page.locator("code").last().innerText());
  expect(await semRolagemLateral()).toBe(true);

  const qrPublico = page.locator("main img").first();
  await qrPublico.scrollIntoViewIfNeeded();
  expect((await qrPublico.boundingBox())!.width).toBeGreaterThanOrEqual(128);
});

test("link inventado responde igual a link revogado", async ({ page }) => {
  // Distinguir entregaria a quem adivinha a informação de que um palpite
  // chegou perto.
  await page.goto("/ingresso/eu-inventei-isso-aqui-agora-mesmo-zxq");

  await expect(page.getByRole("heading", { name: /não vale mais/i })).toBeVisible();
  await expect(page.getByText(/peça um novo/i)).toBeVisible();
});
