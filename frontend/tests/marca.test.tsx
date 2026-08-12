import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { BrandMark } from "@/components/header/BrandMark";

/**
 * A marca — desenho, nome e destino.
 *
 * O que estes testes protegem:
 *
 *  - que o **destino por papel** sobreviva. Ele veio da 010, não é óbvio
 *    olhando um componente de logotipo, e a 011 reescreveu esse componente —
 *    que é a maneira mais provável de perdê-lo. Perdê-lo significa a portaria
 *    voltando a cair no catálogo;
 *  - que o **rótulo acessível descreva a viagem certa**. Dizer "ir para a
 *    página inicial" a quem vai para a portaria descreve a viagem errada, e o
 *    defeito só aparece para quem usa leitor de tela;
 *  - que o desenho **não dependa de fonte**. Se ele fosse texto na família da
 *    marca, sumiria antes de a fonte chegar e não serviria como ícone de aba.
 */

describe("marca", () => {
  it("mostra o desenho e o nome", () => {
    const { container } = render(<BrandMark />);

    expect(container.querySelector("svg")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveTextContent("ticket.com");
  });

  it("o desenho é SVG, não texto dependente de fonte", () => {
    // Como caminho desenhado, ele aparece igual no primeiro quadro e serve
    // como ícone de aba, onde não existe fonte nenhuma.
    const { container } = render(<BrandMark />);
    const svg = container.querySelector("svg")!;

    expect(svg.querySelectorAll("path").length).toBeGreaterThan(0);
    expect(svg.querySelector("circle")).toBeInTheDocument();
    expect(svg.querySelector("text")).toBeNull();
  });

  it("o desenho não é anunciado duas vezes", () => {
    // Quem nomeia o site é o rótulo do link. Anunciar o desenho também faria
    // o leitor de tela dizer o nome duas vezes.
    const { container } = render(<BrandMark />);

    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  // --- O comportamento que veio da 010 e não pode se perder ---------------

  it("leva à home por padrão", () => {
    render(<BrandMark />);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/");
  });

  it("leva a portaria à tela dela", () => {
    // A portaria tem tela única e não alcança o catálogo. Uma marca que a
    // levasse à home só produziria um redirecionamento de volta.
    render(<BrandMark destino="/portaria" />);

    expect(screen.getByRole("link")).toHaveAttribute("href", "/portaria");
  });

  it.each([
    ["/", /página inicial/i],
    ["/portaria", /validação/i],
  ])("o rótulo acessível descreve a viagem certa a partir de %s", (destino, esperado) => {
    render(<BrandMark destino={destino} />);

    const link = screen.getByRole("link");
    expect(link).toHaveAccessibleName(/ticket\.com/i);
    expect(link.getAttribute("aria-label")).toMatch(esperado);
  });
});
