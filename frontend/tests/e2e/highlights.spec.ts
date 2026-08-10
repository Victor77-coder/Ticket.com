import { expect, test } from "@playwright/test";

/**
 * Percurso ponta a ponta do carrossel (Princípio I: o fluxo inteiro).
 *
 * Requer a aplicação no ar com o seed aplicado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

test("descobre um filme, assiste ao trailer e chega às sessões", async ({ page }) => {
  await page.goto("/");

  const carrossel = page.getByRole("region", { name: "Filmes em cartaz" });
  await expect(carrossel).toBeVisible();

  const painelAtivo = carrossel.getByRole("group").filter({ visible: true }).first();
  await expect(painelAtivo.getByRole("heading")).toBeVisible();

  // O trailer abre dentro do painel, sem janela sobreposta e sem sair do site.
  const botaoTrailer = page.getByRole("button", { name: "Trailer" }).first();
  if (await botaoTrailer.isVisible()) {
    await botaoTrailer.click();

    const video = page.locator("iframe[title^='Trailer de']");
    await expect(video).toBeVisible();
    expect(page.url()).toContain("localhost:5000");

    await page.getByRole("button", { name: "Fechar trailer" }).click();
    await expect(video).toHaveCount(0);
  }

  // "Ver ingressos" leva a uma página com sessões listadas.
  await page.getByRole("link", { name: "Ver ingressos" }).first().click();

  await expect(page).toHaveURL(/\/filmes\//);
  await expect(page.getByRole("heading", { name: "Sessões" })).toBeVisible();
});

test("navega pelo carrossel e fecha o ciclo", async ({ page }) => {
  await page.goto("/");

  const contador = page.locator("text=/^\\d+ \\/ \\d+$/");
  await expect(contador).toBeVisible();

  const total = Number((await contador.textContent())!.split("/")[1].trim());
  const proximo = page.getByRole("button", { name: "Próximo filme" });

  for (let i = 0; i < total; i += 1) {
    await proximo.click();
  }

  await expect(contador).toHaveText(`1 / ${total}`);
});

test("percorre o carrossel apenas pelo teclado", async ({ page }) => {
  await page.goto("/");

  const contador = page.locator("text=/^\\d+ \\/ \\d+$/");
  await page.getByRole("button", { name: "Próximo filme" }).focus();
  await page.keyboard.press("ArrowRight");

  await expect(contador).toHaveText(/^2 \//);
});
