import { expect, test } from "@playwright/test";

/**
 * Percurso de reserva — filme → sessão → mapa → seleção → reserva confirmada.
 *
 * É o teste do Princípio I nesta feature: o caminho inteiro tem de fechar,
 * não cada tela em separado.
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

async function entrar(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.getByRole("link", { name: "Entrar na sua conta" }).click();

  await page.getByLabel("Usuário").fill("cliente1");
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();

  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toHaveCount(0);
}

async function abrirMapaDeUmaSessao(page: import("@playwright/test").Page) {
  await page.getByRole("link", { name: "Ver ingressos" }).first().click();
  await expect(page).toHaveURL(/\/filmes\//);

  // Uma interação da lista de sessões até o mapa (SC-001): a sessão inteira
  // é o alvo, não um botão ao lado dela.
  await page.getByRole("link", { name: /^Escolher lugares —/ }).first().click();

  await expect(page).toHaveURL(/\/sessoes\/\d+/);
  await expect(page.getByRole("heading", { name: "Escolha seus lugares" })).toBeVisible();
}

test("o visitante vê o mapa sem entrar", async ({ page }) => {
  await page.goto("/");
  await abrirMapaDeUmaSessao(page);

  // FR-010: exigir conta para olhar afastaria quem ainda não tem motivo de
  // criar uma.
  await expect(page.getByRole("button", { name: /^Fileira/ }).first()).toBeVisible();
});

test("filme → sessão → mapa → seleção → reserva confirmada", async ({ page }) => {
  await entrar(page);
  await abrirMapaDeUmaSessao(page);

  const livre = page.getByRole("button", { name: /^Fileira .*, livre$/ }).first();
  // O rótulo é lido ANTES do clique: ele muda de "livre" para "selecionado", e
  // um localizador por situação passaria a apontar para outro lugar da sala.
  const rotulo = (await livre.getAttribute("aria-label"))!;
  await livre.click();

  const escolhido = page.getByRole("button", {
    name: rotulo.replace(", livre", ", selecionado"),
  });
  await expect(escolhido).toHaveAttribute("aria-pressed", "true");

  await expect(page.getByText(/^1 lugar ·/)).toBeVisible();

  await page.getByRole("button", { name: "Confirmar lugares" }).click();

  await expect(page.getByRole("heading", { name: "Lugares reservados" })).toBeVisible();
  // O prazo aparece como contagem, a partir do instante absoluto (FR-020).
  await expect(page.getByRole("timer")).toContainText(/para concluir o pagamento/);
  // Nenhum ingresso é emitido aqui (FR-029) — o caminho leva à feature
  // seguinte em vez de terminar em beco.
  await expect(page.getByRole("link", { name: "Continuar para pagamento" })).toBeVisible();
});
