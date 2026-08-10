import { act, fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { HighlightsCarousel } from "@/components/highlights/HighlightsCarousel";
import { criarHighlight, criarHighlights } from "./fixtures";
import { definirMediaQuery, limparMediaQueries } from "./setup";

const MOVIMENTO_REDUZIDO = "(prefers-reduced-motion: reduce)";
const INTERVALO_ROTACAO_MS = 7000;

function painelAtivo() {
  // O painel ativo é o único que não está inerte.
  const paineis = screen.getAllByRole("group");
  return paineis.find((p) => !p.hasAttribute("inert"))!;
}

/** A rotação automática muda estado do React; sem act() nada é repintado. */
function avancarTempo(ms: number) {
  act(() => {
    vi.advanceTimersByTime(ms);
  });
}

beforeEach(() => {
  limparMediaQueries();
  definirMediaQuery(MOVIMENTO_REDUZIDO, false);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("navegação", () => {
  it("mostra o primeiro filme e o contador correto", () => {
    render(<HighlightsCarousel highlights={criarHighlights(5)} />);

    expect(within(painelAtivo()).getByRole("heading")).toHaveTextContent("Filme A");
    expect(screen.getByText("1 / 5")).toBeInTheDocument();
  });

  it("avança para o próximo filme", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(5)} />);

    await usuario.click(screen.getByRole("button", { name: "Próximo filme" }));

    expect(within(painelAtivo()).getByRole("heading")).toHaveTextContent("Filme B");
    expect(screen.getByText("2 / 5")).toBeInTheDocument();
  });

  it("do último volta ao primeiro — navegação circular (FR-008)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    const proximo = screen.getByRole("button", { name: "Próximo filme" });
    await usuario.click(proximo);
    await usuario.click(proximo);
    expect(screen.getByText("3 / 3")).toBeInTheDocument();

    await usuario.click(proximo);
    expect(within(painelAtivo()).getByRole("heading")).toHaveTextContent("Filme A");
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("do primeiro retrocede ao último — navegação circular (FR-008)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getByRole("button", { name: "Filme anterior" }));

    expect(within(painelAtivo()).getByRole("heading")).toHaveTextContent("Filme C");
    expect(screen.getByText("3 / 3")).toBeInTheDocument();
  });

  it("salta direto para um filme pelo indicador (FR-007)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(5)} />);

    await usuario.click(screen.getByRole("button", { name: "Ir para Filme D" }));

    expect(within(painelAtivo()).getByRole("heading")).toHaveTextContent("Filme D");
    expect(screen.getByText("4 / 5")).toBeInTheDocument();
  });

  it("marca o indicador ativo com aria-current", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    expect(screen.getByRole("button", { name: "Ir para Filme A" })).toHaveAttribute(
      "aria-current",
      "true",
    );

    await usuario.click(screen.getByRole("button", { name: "Ir para Filme B" }));

    expect(screen.getByRole("button", { name: "Ir para Filme A" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getByRole("button", { name: "Ir para Filme B" })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });

  it("navega pelas setas do teclado (FR-025)", async () => {
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getByRole("button", { name: "Próximo filme" }));
    await usuario.keyboard("{ArrowRight}");
    expect(screen.getByText("3 / 3")).toBeInTheDocument();

    await usuario.keyboard("{ArrowLeft}");
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("esconde os controles quando há um único filme", () => {
    render(<HighlightsCarousel highlights={[criarHighlight()]} />);

    expect(screen.queryByRole("button", { name: "Próximo filme" })).not.toBeInTheDocument();
  });

  it("mostra o estado vazio quando não há destaque (FR-022)", () => {
    render(<HighlightsCarousel highlights={[]} />);

    expect(screen.getByText("Nenhum filme em cartaz agora")).toBeInTheDocument();
    expect(screen.queryByRole("region")).not.toBeInTheDocument();
  });
});

describe("rotação automática", () => {
  it("avança sozinho após o intervalo (FR-009)", () => {
    vi.useFakeTimers();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    avancarTempo(INTERVALO_ROTACAO_MS);
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("pausa com o ponteiro sobre o carrossel e retoma ao sair (FR-010)", () => {
    // fireEvent em vez de userEvent.hover: o userEvent tem atrasos internos que
    // não se coordenam com fake timers e travam o teste.
    vi.useFakeTimers();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);
    const regiao = screen.getByRole("region");

    fireEvent.mouseEnter(regiao);
    avancarTempo(INTERVALO_ROTACAO_MS * 2);
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    fireEvent.mouseLeave(regiao);
    avancarTempo(INTERVALO_ROTACAO_MS);
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("pausa quando um controle interno recebe foco de teclado (FR-010)", () => {
    vi.useFakeTimers();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    act(() => {
      screen.getByRole("button", { name: "Próximo filme" }).focus();
    });
    avancarTempo(INTERVALO_ROTACAO_MS * 2);

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("não anuncia a troca automática ao leitor de tela (R9)", () => {
    vi.useFakeTimers();
    const { container } = render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    const trilha = container.querySelector("[aria-live]")!;
    expect(trilha).toHaveAttribute("aria-live", "off");

    avancarTempo(INTERVALO_ROTACAO_MS);
    expect(container.querySelector("[aria-live]")).toHaveAttribute("aria-live", "off");
  });

  it("anuncia a troca iniciada pelo usuário (R9)", async () => {
    const usuario = userEvent.setup();
    const { container } = render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getByRole("button", { name: "Próximo filme" }));

    expect(container.querySelector("[aria-live]")).toHaveAttribute("aria-live", "polite");
  });
});

describe("movimento reduzido (FR-011)", () => {
  it("não rotaciona sozinho", () => {
    definirMediaQuery(MOVIMENTO_REDUZIDO, true);
    vi.useFakeTimers();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    avancarTempo(INTERVALO_ROTACAO_MS * 3);

    expect(screen.getByText("1 / 3")).toBeInTheDocument();
  });

  it("mantém a navegação manual funcionando", async () => {
    definirMediaQuery(MOVIMENTO_REDUZIDO, true);
    const usuario = userEvent.setup();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    await usuario.click(screen.getByRole("button", { name: "Próximo filme" }));

    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });

  it("passa a rotacionar se a preferência mudar durante a sessão", () => {
    definirMediaQuery(MOVIMENTO_REDUZIDO, true);
    vi.useFakeTimers();
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    avancarTempo(INTERVALO_ROTACAO_MS);
    expect(screen.getByText("1 / 3")).toBeInTheDocument();

    act(() => {
      definirMediaQuery(MOVIMENTO_REDUZIDO, false);
    });
    avancarTempo(INTERVALO_ROTACAO_MS);
    expect(screen.getByText("2 / 3")).toBeInTheDocument();
  });
});

describe("acessibilidade", () => {
  it("expõe a região com semântica de carrossel (R9)", () => {
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    const regiao = screen.getByRole("region", { name: "Filmes em cartaz" });
    expect(regiao).toHaveAttribute("aria-roledescription", "carousel");
  });

  it("rotula cada painel com a posição e o título", () => {
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    expect(screen.getByRole("group", { name: "1 de 3: Filme A" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "3 de 3: Filme C" })).toBeInTheDocument();
  });

  it("torna inertes os painéis fora de vista (SC-005)", () => {
    render(<HighlightsCarousel highlights={criarHighlights(3)} />);

    const paineis = screen.getAllByRole("group");
    const inertes = paineis.filter((p) => p.hasAttribute("inert"));
    expect(inertes).toHaveLength(2);
  });
});
