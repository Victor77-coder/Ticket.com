import { expect, test } from "@playwright/test";

/**
 * Trilhas da home.
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

test.describe("trilhas da home", () => {
  test("exibe as trilhas e conduz à página do filme", async ({ page }) => {
    await page.goto("/");

    const emCartaz = page.getByRole("region", { name: /Em cartaz/ });
    await expect(emCartaz).toBeVisible();

    const primeiro = emCartaz.getByRole("link").first();
    const titulo = await primeiro.getAttribute("aria-label");
    await primeiro.click();

    await expect(page).toHaveURL(/\/filmes\//);
    await expect(page.getByRole("heading", { level: 1, name: titulo! })).toBeVisible();
    await expect(page.getByRole("heading", { name: "Sessões" })).toBeVisible();
  });

  test("a trilha Em alta não passa de 9 filmes", async ({ page }) => {
    await page.goto("/");

    const emAlta = page.getByRole("region", { name: /Em alta/ });
    if (await emAlta.isVisible()) {
      expect(await emAlta.getByRole("link").count()).toBeLessThanOrEqual(9);
    }
  });

  test("um filme de Em breve leva a uma página que explica a ausência de sessões", async ({
    page,
  }) => {
    await page.goto("/");

    const emBreve = page.getByRole("region", { name: /Em breve/ });
    test.skip(!(await emBreve.isVisible()), "sem filmes de estreia futura no catálogo");

    await emBreve.getByRole("link").first().click();

    await expect(page).toHaveURL(/\/filmes\//);
    await expect(page.getByText("No momento, este filme não possui sessões programadas.")).toBeVisible();
  });
});

test.describe("sem rolagem horizontal da página (SC-005)", () => {
  // A armadilha de R1: overflow-x na trilha só é contido se o contêiner pai
  // tiver min-width: 0. Sem isso o conteúdo empurra a largura da página.
  for (const largura of [360, 768, 1280, 1920]) {
    test(`largura ${largura}px`, async ({ page }) => {
      await page.setViewportSize({ width: largura, height: 900 });
      await page.goto("/");
      await page.getByRole("region", { name: /Em cartaz/ }).waitFor();

      const transbordou = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );

      expect(transbordou).toBe(false);
    });
  }
});

test("as trilhas rolam de forma independente", async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await page.goto("/");

  const trilhas = page.locator("section[aria-labelledby^='trilha-'] > div").last();
  await trilhas.evaluate((el) => el.scrollBy({ left: 300, behavior: "instant" as ScrollBehavior }));

  const posicoes = await page.evaluate(() =>
    Array.from(document.querySelectorAll("section[aria-labelledby^='trilha-'] > div")).map(
      (el) => el.scrollLeft,
    ),
  );

  // Ao menos uma trilha continua no início: rolar uma não move as outras.
  expect(posicoes.filter((p) => p === 0).length).toBeGreaterThan(0);
});
