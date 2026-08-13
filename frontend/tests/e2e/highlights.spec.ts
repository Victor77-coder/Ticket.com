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
  // Hover pausa a rotação (onMouseEnter). Sem isso o intervalo de 7s pode
  // trocar o painel no meio do trailer e o clique cai num grupo inert.
  await carrossel.hover();

  const painelAtivo = carrossel.locator('[role="group"]:not([inert])');
  await expect(painelAtivo.getByRole("heading")).toBeVisible();

  // O trailer abre dentro do painel, sem janela sobreposta e sem sair do site.
  const botaoTrailer = painelAtivo.getByRole("button", { name: "Trailer" });
  if (await botaoTrailer.isVisible()) {
    await botaoTrailer.click();

    const video = page.locator("iframe[title^='Trailer de']");
    await expect(video).toBeVisible();
    expect(page.url()).toContain("localhost:5003");

    await painelAtivo.getByRole("button", { name: "Fechar trailer" }).click();
    await expect(video).toHaveCount(0);
  }

  // "Ver ingressos" leva a uma página com sessões listadas.
  await painelAtivo.getByRole("link", { name: "Ver ingressos" }).click();

  await expect(page).toHaveURL(/\/filmes\//);
  await expect(page.getByRole("tab", { name: "Sessões" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
});

test("navega pelo carrossel e fecha o ciclo", async ({ page }) => {
  await page.goto("/");

  const carrossel = page.getByRole("region", { name: "Filmes em cartaz" });
  await carrossel.hover();

  const indicadores = page.getByRole("button", { name: /^Ir para / });
  const total = await indicadores.count();
  const proximo = page.getByRole("button", { name: "Próximo filme" });

  for (let i = 0; i < total; i += 1) {
    await proximo.click();
  }

  await expect(indicadores.first()).toHaveAttribute("aria-current", "true");
});

test("percorre o carrossel apenas pelo teclado", async ({ page }) => {
  await page.goto("/");

  await page.getByRole("button", { name: "Próximo filme" }).focus();
  await page.keyboard.press("ArrowRight");

  await expect(page.getByRole("button", { name: /^Ir para / }).nth(1)).toHaveAttribute(
    "aria-current",
    "true",
  );
});
