import { describe, expect, it } from "vitest";

import { centavosDoLugar, totalPrevisto, valorDoLugar } from "@/lib/meia";

/**
 * A TABELA DE CASOS É COMPARTILHADA com `backend/tests/test_precos.py`.
 *
 * Ela é o que faz o espelho do navegador e a conta do servidor concordarem por
 * VERIFICAÇÃO, e não por presunção. Mudar um valor aqui sem mudar lá é o defeito
 * que os dois arquivos existem para impedir — e é por isso que os dois trazem os
 * mesmos pares, escritos na mesma ordem.
 */

// preço da sessão → centavos da meia
const CASOS: ReadonlyArray<[string, number]> = [
  ["32.00", 1600], // exato
  ["45.00", 2250], // exato, ímpar em reais
  ["25.01", 1250], // centavo ímpar → PARA BAIXO (12,505 → 12,50)
  ["25.03", 1251], // o outro lado do mesmo ímpar (12,515 → 12,51)
  ["0.01", 0], // um centavo não tem metade em centavos
  ["0.00", 0], // sessão gratuita continua gratuita
  ["19.99", 999], // 9,995 → 9,99
];

describe("meia — a metade que o navegador prevê", () => {
  it.each(CASOS)("meia de R$ %s é %i centavos", (preco, centavos) => {
    expect(centavosDoLugar(preco, "meia")).toBe(centavos);
  });

  it.each(CASOS)("inteira de R$ %s não é arredondada", (preco) => {
    expect(centavosDoLugar(preco, "inteira")).toBe(Math.round(Number(preco) * 100));
  });

  it("arredonda para BAIXO, em favor de quem compra", () => {
    // 25,01 / 2 = 12,505. Para cima daria 12,51.
    expect(valorDoLugar("25.01", "meia")).toBe(12.5);
  });

  it("o número aceita string ou número — a API manda decimal como string", () => {
    expect(centavosDoLugar(32, "meia")).toBe(centavosDoLugar("32.00", "meia"));
  });

  describe("total previsto", () => {
    it("uma inteira e uma meia somam o esperado", () => {
      expect(totalPrevisto("32.00", ["inteira", "meia"])).toBe(48);
    });

    it("seleção vazia é zero", () => {
      expect(totalPrevisto("32.00", [])).toBe(0);
    });

    it("tudo inteira é preço vezes quantidade", () => {
      expect(totalPrevisto("32.00", ["inteira", "inteira", "inteira"])).toBe(96);
    });

    it("soma em centavos, sem cauda binária", () => {
      // 0,1 + 0,2 em ponto flutuante dá 0,30000000000000004. Somar centavos
      // inteiros e dividir uma vez só é o que mantém o total exato.
      expect(totalPrevisto("10.10", ["inteira", "meia"])).toBe(15.15);
    });
  });
});
