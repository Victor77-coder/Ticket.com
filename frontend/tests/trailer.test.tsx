import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { HighlightsCarousel } from "@/components/highlights/HighlightsCarousel";
import { criarHighlight, criarHighlights } from "./fixtures";
import { definirMediaQuery, limparMediaQueries } from "./setup";

function iframes(container: HTMLElement) {
  return container.querySelectorAll("iframe");
}

beforeEach(() => {
  limparMediaQueries();
  definirMediaQuery("(prefers-reduced-motion: reduce)", false);
});

describe("visibilidade do botão (FR-015)", () => {
  it("não renderiza 'Trailer' quando o filme não tem trailer", () => {
    render(<HighlightsCarousel highlights={[criarHighlight({ trailer: null })]} />);

    expect(screen.queryByRole("button", { name: "Trailer" })).not.toBeInTheDocument();
    // "Ver ingressos" continua acessível, sem lacuna no lugar do botão ausente.
    expect(screen.getByRole("link", { name: "Ver ingressos" })).toBeInTheDocument();
  });

  it("renderiza 'Trailer' quando o filme tem trailer", () => {
    render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    expect(screen.getByRole("button", { name: "Trailer" })).toBeInTheDocument();
  });
});

describe("reprodução dentro do painel (FR-012)", () => {
  it("não carrega nenhum iframe antes do clique (FR-017)", () => {
    const { container } = render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    expect(iframes(container)).toHaveLength(0);
  });

  it("monta o iframe dentro do painel ao acionar 'Trailer'", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    await usuario.click(screen.getByRole("button", { name: "Trailer" }));

    const video = iframes(container)[0];
    expect(video).toBeInTheDocument();
    // Dentro do próprio painel, não em uma janela sobreposta.
    expect(screen.getByRole("group").contains(video)).toBe(true);
    expect(video.getAttribute("src")).toContain("youtube-nocookie.com/embed/");
  });

  it("desmonta o iframe ao fechar (FR-013)", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    await usuario.click(screen.getByRole("button", { name: "Trailer" }));
    expect(iframes(container)).toHaveLength(1);

    await usuario.click(screen.getByRole("button", { name: "Fechar trailer" }));
    expect(iframes(container)).toHaveLength(0);
  });

  it("fecha com a tecla Escape", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    await usuario.click(screen.getByRole("button", { name: "Trailer" }));
    await usuario.keyboard("{Escape}");

    expect(iframes(container)).toHaveLength(0);
  });

  it("move o foco para o botão de fechar (SC-005)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    await usuario.click(screen.getByRole("button", { name: "Trailer" }));

    expect(screen.getByRole("button", { name: "Fechar trailer" })).toHaveFocus();
  });
});

describe("um trailer por vez (FR-014, FR-016)", () => {
  it("desmonta o trailer ao navegar para outro painel", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getAllByRole("button", { name: "Trailer" })[0]);
    expect(iframes(container)).toHaveLength(1);

    await usuario.click(screen.getByRole("button", { name: "Próximo filme" }));
    expect(iframes(container)).toHaveLength(0);
  });

  it("nunca deixa dois iframes montados ao mesmo tempo", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getAllByRole("button", { name: "Trailer" })[0]);
    await usuario.click(screen.getByRole("button", { name: "Ir para Filme C" }));
    await usuario.click(screen.getAllByRole("button", { name: "Trailer" })[2]);

    expect(iframes(container)).toHaveLength(1);
  });

  it("suspende a rotação automática enquanto o trailer toca (FR-010)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getAllByRole("button", { name: "Trailer" })[0]);

    // Com o trailer aberto o painel não pode trocar sozinho por baixo do vídeo.
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Fechar trailer" })).toBeInTheDocument();
  });
});

describe("estado esgotado (FR-020)", () => {
  it("troca o link por um aviso quando não há ingresso", () => {
    render(<HighlightsCarousel highlights={[criarHighlight({ has_available_seats: false })]} />);

    expect(screen.queryByRole("link", { name: "Ver ingressos" })).not.toBeInTheDocument();
    expect(screen.getByText("Ingressos esgotados")).toBeInTheDocument();
  });
});

describe("metadados ausentes", () => {
  it("omite a classificação em vez de mostrar 'N/A' (Princípio V)", () => {
    render(<HighlightsCarousel highlights={[criarHighlight({ certification_br: null })]} />);

    expect(screen.queryByText("N/A")).not.toBeInTheDocument();
    expect(screen.queryByText(/classificação/i)).not.toBeInTheDocument();
  });

  it("omite a duração quando o filme não a informa", () => {
    render(<HighlightsCarousel highlights={[criarHighlight({ runtime_minutes: null })]} />);

    expect(screen.queryByText(/\dh\d/)).not.toBeInTheDocument();
  });

  it("usa o fallback de arte quando não há imagem", () => {
    const { container } = render(
      <HighlightsCarousel highlights={[criarHighlight({ backdrop_url: null })]} />,
    );

    expect(container.querySelector("img")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2 })).toBeInTheDocument();
  });
});
