import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MovieCard } from "@/components/rows/MovieCard";
import { MovieRow } from "@/components/rows/MovieRow";
import type { MovieCard as MovieCardType, MovieRowData } from "@/lib/types";

let contador = 0;

function criarCartao(sobrescreve: Partial<MovieCardType> = {}): MovieCardType {
  contador += 1;
  return {
    id: contador,
    slug: `filme-${contador}`,
    title: `Filme ${contador}`,
    poster_url: "https://image.tmdb.org/t/p/w500/poster.jpg",
    certification_br: "14",
    runtime_minutes: 128,
    release_date: "2026-08-01",
    movie_path: `/filmes/filme-${contador}`,
    ...sobrescreve,
  };
}

function criarTrilha(quantidade: number, sobrescreve: Partial<MovieRowData> = {}): MovieRowData {
  const movies = Array.from({ length: quantidade }, (_, i) =>
    criarCartao({ title: `Filme ${String.fromCharCode(65 + i)}` }),
  );
  return { key: "em-cartaz", title: "Em cartaz", count: movies.length, movies, ...sobrescreve };
}

/**
 * jsdom reporta scrollWidth e clientWidth como 0, então nenhuma trilha
 * transborda por padrão e as setas nunca apareceriam.
 *
 * As dimensões vão no protótipo e não no elemento porque o `ResizeObserver`
 * lê durante o efeito de montagem — estubar depois do render chegaria tarde.
 */
let larguraDoConteudo = 300;
const LARGURA_VISIVEL = 300;

function simularTransbordo(transbordou: boolean) {
  larguraDoConteudo = transbordou ? 2000 : LARGURA_VISIVEL;
}

Object.defineProperty(HTMLElement.prototype, "scrollWidth", {
  configurable: true,
  get() {
    return larguraDoConteudo;
  },
});
Object.defineProperty(HTMLElement.prototype, "clientWidth", {
  configurable: true,
  get() {
    return LARGURA_VISIVEL;
  },
});

beforeEach(() => {
  simularTransbordo(false);

  // ResizeObserver não existe no jsdom. O callback é disparado na observação
  // para reproduzir a avaliação inicial de transbordo.
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(private cb: () => void) {}
      observe() {
        this.cb();
      }
      disconnect() {}
      unobserve() {}
    },
  );
});

// --- Cartão ---------------------------------------------------------------

describe("cartão de filme", () => {
  it("exibe o cartaz, o título em texto e leva à página do filme", () => {
    render(<MovieCard filme={criarCartao({ title: "Duna", movie_path: "/filmes/duna" })} />);

    const link = screen.getByRole("link", { name: "Duna" });
    expect(link).toHaveAttribute("href", "/filmes/duna");
    // Título como texto, não só dentro da imagem (FR-009).
    expect(within(link).getByText("Duna")).toBeInTheDocument();
    expect(link.querySelector("img")).toBeInTheDocument();
  });

  it("mostra substituto legível quando não há cartaz (FR-011)", () => {
    const { container } = render(
      <MovieCard filme={criarCartao({ title: "Sem Cartaz", poster_url: null })} />,
    );

    expect(container.querySelector("img")).not.toBeInTheDocument();
    // O título aparece duas vezes: dentro da moldura e abaixo dela.
    expect(screen.getAllByText("Sem Cartaz").length).toBeGreaterThanOrEqual(1);
  });

  it("mantém o nome acessível mesmo sem cartaz (FR-012)", () => {
    render(<MovieCard filme={criarCartao({ title: "Anônimo", poster_url: null })} />);

    expect(screen.getByRole("link", { name: "Anônimo" })).toBeInTheDocument();
  });

  it("omite classificação e duração ausentes em vez de exibir vazio", () => {
    render(
      <MovieCard
        filme={criarCartao({ title: "Sem Meta", certification_br: null, runtime_minutes: null })}
      />,
    );

    expect(screen.queryByText("N/A")).not.toBeInTheDocument();
    expect(screen.queryByText("·")).not.toBeInTheDocument();
  });

  it("formata a duração em horas e minutos", () => {
    render(<MovieCard filme={criarCartao({ runtime_minutes: 143, certification_br: null })} />);

    expect(screen.getByText("2h23")).toBeInTheDocument();
  });
});

// --- Trilha ---------------------------------------------------------------

describe("trilha", () => {
  it("exibe o título e todos os cartões", () => {
    render(<MovieRow trilha={criarTrilha(4)} />);

    expect(screen.getByRole("heading", { name: /Em cartaz/ })).toBeInTheDocument();
    expect(screen.getAllByRole("link")).toHaveLength(4);
  });

  it("anuncia a quantidade de filmes a tecnologias assistivas (FR-019)", () => {
    render(<MovieRow trilha={criarTrilha(3)} />);

    expect(screen.getByRole("heading", { name: "Em cartaz — 3 filmes" })).toBeInTheDocument();
  });

  it("usa singular quando há um só filme", () => {
    render(<MovieRow trilha={criarTrilha(1)} />);

    expect(screen.getByRole("heading", { name: "Em cartaz — 1 filme" })).toBeInTheDocument();
  });

  it("associa a região ao título", () => {
    render(<MovieRow trilha={criarTrilha(3)} />);

    expect(screen.getByRole("region", { name: /Em cartaz/ })).toBeInTheDocument();
  });
});

// --- Controles (FR-014) ---------------------------------------------------

describe("controles de navegação", () => {
  it("não renderiza setas quando tudo cabe na tela", () => {
    simularTransbordo(false);
    render(<MovieRow trilha={criarTrilha(2)} />);

    expect(screen.queryByRole("button", { name: /Ver mais filmes/ })).not.toBeInTheDocument();
  });

  it("renderiza setas quando há conteúdo além da borda", () => {
    simularTransbordo(true);
    render(<MovieRow trilha={criarTrilha(12)} />);

    expect(screen.getByRole("button", { name: /Ver mais filmes/ })).toBeInTheDocument();
  });

  it("desabilita 'anterior' no início da trilha", () => {
    simularTransbordo(true);
    render(<MovieRow trilha={criarTrilha(12)} />);

    expect(screen.getByRole("button", { name: /filmes anteriores/ })).toBeDisabled();
  });

  it("rotula as setas com o nome da trilha", () => {
    simularTransbordo(true);
    render(<MovieRow trilha={criarTrilha(12, { title: "Em alta", key: "em-alta" })} />);

    expect(screen.getByRole("button", { name: "Ver mais filmes em Em alta" })).toBeInTheDocument();
  });
});

// --- Teclado (FR-017, SC-006) --------------------------------------------

describe("acessibilidade por teclado", () => {
  it("todos os cartões são alcançáveis na ordem visual", async () => {
    const usuario = userEvent.setup();
    render(<MovieRow trilha={criarTrilha(3)} />);

    const links = screen.getAllByRole("link");

    await usuario.tab();
    expect(links[0]).toHaveFocus();
    await usuario.tab();
    expect(links[1]).toHaveFocus();
    await usuario.tab();
    expect(links[2]).toHaveFocus();
  });

  it("nenhum cartão fica fora da ordem de tabulação", () => {
    render(<MovieRow trilha={criarTrilha(5)} />);

    for (const link of screen.getAllByRole("link")) {
      expect(link).not.toHaveAttribute("tabindex", "-1");
    }
  });
});
