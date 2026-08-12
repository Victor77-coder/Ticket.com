import { expect, test } from "@playwright/test";

/**
 * Percurso do organizador — entrar, programar, publicar, e o cliente comprar.
 *
 * É a prova de SC-001 e SC-002 juntas: o organizador coloca um filme à venda
 * sem executar comando nenhum, e a sessão aparece no caminho de compra do
 * cliente sem passo intermediário.
 *
 * O PONTO DO TESTE É A COSTURA, não a tela. Cada metade já tem prova própria —
 * a API tem `test_programacao_sessoes.py`, a interface tem
 * `programacao.test.tsx`. O que só este arquivo pega é a sessão publicada no
 * painel não chegando ao catálogo: as duas metades passariam verdes e o
 * produto estaria quebrado no meio.
 *
 * Em série, e o motivo é o mesmo do percurso da portaria: este teste ESCREVE
 * na grade, e workers paralelos disputariam a mesma (sala, horário).
 *
 * Requer a aplicação no ar com o catálogo sincronizado e semeado:
 *   docker compose up -d
 *   docker compose exec backend python manage.py sync_tmdb --limit 20
 *   docker compose exec backend python manage.py seed_demo
 */

test.describe.configure({ mode: "serial" });

type Pagina = import("@playwright/test").Page;

async function sair(page: Pagina) {
  await page.goto("/");
  const jaEstaFora = await page
    .getByRole("link", { name: "Entrar na sua conta" })
    .count();
  if (jaEstaFora > 0) return;

  await page.locator("header").getByRole("button").first().click();
  await page.getByRole("menuitem", { name: "Sair" }).click();
  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toBeVisible();
}

async function entrar(page: Pagina, usuario: string) {
  await sair(page);
  await page.getByRole("link", { name: "Entrar na sua conta" }).click();
  await page.getByLabel("Usuário").fill(usuario);
  await page.getByLabel("Senha").fill("desafio2026");
  await page.getByRole("button", { name: "Entrar", exact: true }).click();
  await expect(page.getByRole("link", { name: "Entrar na sua conta" })).toHaveCount(0);
}

/** Um horário futuro improvável de colidir com a grade do seed. */
function horarioDaSessao(): { valor: string; hora: string } {
  const quando = new Date();
  quando.setDate(quando.getDate() + 6);
  quando.setHours(22, 47, 0, 0);

  const dois = (n: number) => String(n).padStart(2, "0");
  const data = `${quando.getFullYear()}-${dois(quando.getMonth() + 1)}-${dois(quando.getDate())}`;
  const hora = `${dois(quando.getHours())}:${dois(quando.getMinutes())}`;

  return { valor: `${data}T${hora}`, hora };
}

test("o organizador pousa no painel ao entrar", async ({ page }) => {
  await entrar(page, "organizador");

  // O pouso é o que faz a tela existir na prática: sem ele, o painel só
  // alcança quem decorou o endereço.
  await expect(page).toHaveURL(/\/programacao$/);
  await expect(page.getByRole("heading", { name: "Programação" })).toBeVisible();
});

test("o organizador continua alcançando o catálogo público", async ({ page }) => {
  await entrar(page, "organizador");

  await page.goto("/");

  // FR-004: diferente da portaria, ele NÃO é devolvido para a casa dele — é
  // no catálogo que ele confere que a sessão publicada apareceu à venda.
  await expect(page).toHaveURL(/\/$/);
});

test("programa, publica, e o cliente encontra a sessão", async ({ page }) => {
  const horario = horarioDaSessao();

  await entrar(page, "organizador");
  await page.getByRole("link", { name: "Programar sessão" }).click();

  const filme = page.getByLabel("Filme");
  await filme.selectOption({ index: 1 });
  const tituloEscolhido = (await filme.locator("option:checked").textContent())!
    .replace(/\s*\(\d{4}\)\s*$/, "")
    .trim();

  await page.getByLabel("Data e hora").fill(horario.valor);
  await page.getByLabel("Preço").fill("31.50");
  await page.getByRole("button", { name: "Publicar" }).click();

  await expect(page).toHaveURL(/\/programacao$/);
  await expect(page.getByText("Publicada").first()).toBeVisible();

  // A outra ponta: o cliente vê o horário na página do filme.
  await entrar(page, "cliente1");
  await page.goto("/");
  await page.getByRole("link", { name: new RegExp(tituloEscolhido, "i") }).first().click();

  await expect(
    page.getByRole("link", { name: new RegExp(`Escolher lugares — .*${horario.hora}`) }).first(),
  ).toBeVisible();
});

test("o cliente que abre a programação lê uma recusa, e não a entrada", async ({ page }) => {
  await entrar(page, "cliente1");

  await page.goto("/programacao");

  // R11: papel errado NÃO é conduzido à entrada — entrar de novo não muda o
  // papel, e o caminho não teria saída.
  await expect(page).toHaveURL(/\/programacao$/);
  await expect(page.getByRole("alert")).toContainText("Esta área é da programação");
});
