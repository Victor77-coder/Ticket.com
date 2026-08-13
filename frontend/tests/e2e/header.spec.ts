import { expect, test } from "@playwright/test";

/**
 * Cabeçalho global — presença e navegação (US1).
 *
 * Requer a aplicação no ar com o seed aplicado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

async function abrirPaginaDeFilme(page: import("@playwright/test").Page) {
  await page.goto("/");
  const carrossel = page.getByRole("region", { name: "Filmes em cartaz" });
  await carrossel.hover();
  await carrossel
    .locator('[role="group"]:not([inert])')
    .getByRole("link", { name: "Ver ingressos" })
    .click();
  await expect(page).toHaveURL(/\/filmes\//);
}

test("o cabeçalho está presente na home e na página do filme", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.getByRole("banner").getByRole("link", { name: /ticket\.com/i })).toBeVisible();

  await abrirPaginaDeFilme(page);

  // Mesma composição, não apenas "um cabeçalho qualquer".
  await expect(page.getByRole("banner")).toBeVisible();
  await expect(page.getByRole("banner").getByRole("link", { name: /ticket\.com/i })).toBeVisible();
});

test("o nome do site leva de volta à home a partir da página do filme", async ({ page }) => {
  await abrirPaginaDeFilme(page);

  await page.getByRole("banner").getByRole("link", { name: /ticket\.com/i }).click();

  await expect(page).toHaveURL(/localhost:5003\/?$/);
});

test("o cabeçalho acompanha a rolagem sem cobrir o conteúdo", async ({ page }) => {
  await page.goto("/");

  await page.mouse.wheel(0, 1200);
  await expect(page.getByRole("banner")).toBeInViewport();
});

test("o título do documento carrega o nome do site", async ({ page }) => {
  await page.goto("/");

  await expect(page).toHaveTitle(/ticket\.com/);
});

test("busca um filme pelo nome e chega à página dele", async ({ page }) => {
  await page.goto("/");

  const campo = page.getByRole("combobox");
  await campo.fill("odis");

  const lista = page.getByRole("listbox");
  await expect(lista).toBeVisible();

  const primeira = lista.getByRole("option").first();
  const titulo = (await primeira.textContent())!.trim();
  await primeira.click();

  await expect(page).toHaveURL(/\/filmes\//);
  await expect(page.getByRole("heading", { level: 1 })).toContainText(titulo.replace(/\d{4}$/, ""));
});

test("informa quando nada corresponde ao termo", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("combobox").fill("zzzznaoexiste");

  await expect(page.getByText(/nenhum filme encontrado para/i).first()).toBeVisible();
  await expect(page.getByRole("listbox")).toHaveCount(0);
});

test("percorre as sugestões e abre pelo teclado", async ({ page }) => {
  await page.goto("/");

  const campo = page.getByRole("combobox");
  await campo.click();
  await campo.type("odis", { delay: 30 });

  await expect(page.getByRole("listbox")).toBeVisible();

  await page.keyboard.press("ArrowDown");
  // Foco virtual: o cursor continua no campo (R4).
  await expect(campo).toBeFocused();
  await expect(campo).toHaveAttribute("aria-activedescendant", /opcao-0$/);

  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/filmes\//);
});

test("Esc fecha as sugestões sem tirar o foco do campo", async ({ page }) => {
  await page.goto("/");

  const campo = page.getByRole("combobox");
  await campo.fill("odis");
  await expect(page.getByRole("listbox")).toBeVisible();

  await page.keyboard.press("Escape");

  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(campo).toBeFocused();
});

test("a busca funciona a partir da página do filme", async ({ page }) => {
  await abrirPaginaDeFilme(page);

  await page.getByRole("combobox").fill("odis");

  await expect(page.getByRole("listbox")).toBeVisible();
});

test("percorre o cabeçalho inteiro pelo teclado, com foco visível", async ({ page }) => {
  await page.goto("/");

  // Primeira parada: a identidade do site.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("banner").getByRole("link", { name: /ticket\.com/i })).toBeFocused();
  expect(await contornoDeFoco(page)).not.toBe("none");

  // Segunda parada: a busca.
  await page.keyboard.press("Tab");
  await expect(page.getByRole("combobox")).toBeFocused();
  expect(await contornoDeFoco(page)).not.toBe("none");

  // Com a lista aberta, as setas não tiram o foco do campo — nem prendem o
  // usuário dentro do cabeçalho.
  await page.getByRole("combobox").fill("odis");
  await expect(page.getByRole("listbox")).toBeVisible();
  await page.keyboard.press("ArrowDown");
  await expect(page.getByRole("combobox")).toBeFocused();

  await page.keyboard.press("Escape");
  await page.keyboard.press("Tab");
  await expect(page.getByRole("combobox")).not.toBeFocused();
});

async function contornoDeFoco(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    const alvo = document.activeElement;
    if (!alvo) return "none";
    return getComputedStyle(alvo).outlineStyle;
  });
}

test("não há rolagem horizontal em tela estreita", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto("/");

  const transbordou = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(transbordou).toBe(false);

  await expect(page.getByRole("banner").getByRole("link", { name: /ticket\.com/i })).toBeVisible();
});

// --- Acesso à conta (feature 003) ---
// Percurso que a T038 previa e que só se tornou executável quando a
// autenticação entregou a rota de entrada.

test("percorre visitante → entrada → autenticado → saída", async ({ page }) => {
  await page.goto("/");

  const cabecalho = page.getByRole("banner");

  // Visitante: o ponto de conta convida a entrar e leva ao destino.
  const entrar = cabecalho.getByRole("link", { name: /entrar na sua conta/i });
  await expect(entrar).toBeVisible();
  await entrar.click();
  await expect(page).toHaveURL(/\/entrar/);

  await page.getByLabel("Usuário").fill("cliente1");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  // Autenticado: o mesmo ponto passa a identificar, em todas as páginas.
  await expect(page).toHaveURL("/");
  await expect(cabecalho.getByRole("button", { name: /camila/i })).toBeVisible();

  await page.goto("/filmes");
  await page.goto("/");
  await expect(cabecalho.getByRole("button", { name: /camila/i })).toBeVisible();

  // Saída: volta ao estado de visitante.
  await cabecalho.getByRole("button", { name: /camila/i }).click();
  await page.getByRole("menuitem", { name: "Sair" }).click();

  await expect(cabecalho.getByRole("link", { name: /entrar na sua conta/i })).toBeVisible();
});

test("volta ao estado de visitante quando a sessão deixa de valer", async ({ page, context }) => {
  await page.goto("/entrar");
  await page.getByLabel("Usuário").fill("cliente1");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page.getByRole("banner").getByRole("button", { name: /camila/i })).toBeVisible();

  // Invalida a sessão por fora, como aconteceria ao expirar.
  await context.clearCookies();
  await page.reload();

  // A página continua utilizável; só o cabeçalho muda de estado (FR-017).
  await expect(
    page.getByRole("banner").getByRole("link", { name: /entrar na sua conta/i }),
  ).toBeVisible();
  await expect(page.getByRole("banner")).toBeVisible();
});

test("o retorno após a entrada respeita a página de origem", async ({ page }) => {
  await page.goto("/entrar?next=%2Ffilmes%2Fduna-parte-dois");

  await page.getByLabel("Usuário").fill("cliente2");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  await expect(page).toHaveURL(/\/filmes\/duna-parte-dois/);
});

test("descarta destino de retorno externo", async ({ page }) => {
  await page.goto("/entrar?next=%2F%2Fexemplo.com");

  await page.getByLabel("Usuário").fill("cliente1");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar" }).click();

  // Nunca sai do site: o destino externo é trocado pela home (FR-011).
  await expect(page).toHaveURL("/");
});
