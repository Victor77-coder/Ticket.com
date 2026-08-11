/**
 * Verificação de SC-007 — os quatro estados do lugar continuam distinguíveis
 * sem cor. Emula acromatopsia via CDP e captura o mapa ampliado.
 *
 * Uso: node tests/e2e/acromatopsia.mjs <id-da-sessao> <prefixo-do-arquivo>
 *
 * Gera dois arquivos: `<prefixo>-cor.png` e `<prefixo>-cinza.png`. A
 * comparação entre os dois é a verificação; a captura em cor sozinha não diz
 * nada sobre FR-008.
 */

import { chromium } from "@playwright/test";

const [, , idSessao = "1", prefixo = "/tmp/mapa"] = process.argv;

const navegador = await chromium.launch();
const pagina = await navegador.newPage({
  viewport: { width: 900, height: 1100 },
  deviceScaleFactor: 3,
});

await pagina.goto(`http://localhost:5003/sessoes/${idSessao}`, {
  waitUntil: "networkidle",
});

const lugares = pagina.getByRole("button", { name: /^Fileira/ });
await lugares.first().waitFor();

// Um lugar selecionado, para o estado 2 entrar na captura. Os estados
// "tomado" e "acessibilidade" precisam já existir na sessão escolhida.
await lugares.nth(2).click();

// A transição de cor do lugar leva alguns quadros. Sem esta espera a captura
// pega o estado no meio do caminho e a cor lida errada — o que já produziu um
// falso alarme nesta verificação.
await pagina.waitForTimeout(600);

const sala = pagina.locator("section, main").first();
const area = await pagina.getByRole("list").first().boundingBox();
const mapa = await sala.boundingBox();
const recorte = {
  x: mapa.x,
  y: mapa.y,
  width: mapa.width,
  height: area.y + area.height - mapa.y,
};

await pagina.screenshot({ path: `${prefixo}-cor.png`, clip: recorte });

const cdp = await pagina.context().newCDPSession(pagina);
await cdp.send("Emulation.setEmulatedVisionDeficiency", { type: "achromatopsia" });

await pagina.screenshot({ path: `${prefixo}-cinza.png`, clip: recorte });

console.log(`capturas: ${prefixo}-cor.png e ${prefixo}-cinza.png`);
await navegador.close();
