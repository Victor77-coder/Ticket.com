import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { SearchBox } from "@/components/header/SearchBox";
import type { SearchResponse, SearchSuggestion } from "@/lib/types";
import { rotasVisitadas } from "./setup";

const DEBOUNCE_MS = 250;

function criarSugestao(sobrescreve: Partial<SearchSuggestion> = {}): SearchSuggestion {
  return {
    slug: "matrix",
    title: "Matrix",
    poster_url: "https://image.tmdb.org/t/p/w500/poster.jpg",
    year: 1999,
    movie_path: "/filmes/matrix",
    ...sobrescreve,
  };
}

function criarResposta(
  results: SearchSuggestion[],
  sobrescreve: Partial<SearchResponse> = {},
): SearchResponse {
  return {
    termo: "matrix",
    count: results.length,
    truncated: false,
    results,
    ...sobrescreve,
  };
}

/** Controla quando cada requisição resolve — é o que permite provar SC-005. */
function criarFetchControlavel() {
  const pendentes: Array<{ url: string; resolver: (r: SearchResponse) => void }> = [];

  const stub = vi.fn((entrada: string | URL) => {
    return new Promise((resolve) => {
      pendentes.push({
        url: String(entrada),
        resolver: (corpo) =>
          resolve({
            ok: true,
            status: 200,
            json: async () => corpo,
          } as Response),
      });
    });
  });

  return { stub, pendentes };
}

function digitar(valor: string) {
  fireEvent.change(screen.getByRole("combobox"), { target: { value: valor } });
}

function avancarDebounce() {
  vi.advanceTimersByTime(DEBOUNCE_MS + 10);
}

beforeEach(() => {
  vi.useFakeTimers({ shouldAdvanceTime: true });
  rotasVisitadas.length = 0;
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  cleanup();
});

describe("busca do cabeçalho", () => {
  it("agrupa a digitação rápida em uma única requisição", async () => {
    const { stub } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);

    for (const parcial of ["m", "ma", "mat", "matr", "matri"]) {
      digitar(parcial);
    }
    avancarDebounce();

    await waitFor(() => expect(stub).toHaveBeenCalledTimes(1));
    expect(String(stub.mock.calls[0][0])).toContain("matri");
  });

  it("descarta a resposta antiga que chega depois da nova (SC-005)", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);

    digitar("mat");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(1));

    digitar("matrix");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(2));

    // A nova responde primeiro; a antiga chega depois — a janela de corrida
    // que o AbortController sozinho não fecha.
    pendentes[1].resolver(criarResposta([criarSugestao({ title: "Matrix" })]));
    pendentes[0].resolver(
      criarResposta([criarSugestao({ title: "Chamado da Mata", slug: "mata" })], {
        termo: "mat",
      }),
    );

    await waitFor(() => expect(screen.getByRole("listbox")).toBeInTheDocument());

    const opcoes = within(screen.getByRole("listbox")).getAllByRole("option");
    expect(opcoes).toHaveLength(1);
    expect(opcoes[0]).toHaveTextContent("Matrix");
    expect(screen.queryByText(/Chamado da Mata/)).not.toBeInTheDocument();
  });

  it("mostra o estado 'nenhum resultado' com o termo buscado", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    digitar("zzzz");
    avancarDebounce();

    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([], { termo: "zzzz", count: 0 }));

    // O termo aparece na sugestão e também na região `status`; a asserção
    // mira a mensagem visível, não o anúncio para leitor de tela.
    await waitFor(() =>
      expect(
        screen.getByText(/nenhum filme encontrado para/i, { ignore: '[role="status"]' }),
      ).toHaveTextContent("zzzz"),
    );
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("distingue 'buscando' de 'nenhum resultado'", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    digitar("matrix");
    avancarDebounce();

    // Requisição em voo: os dois estados produzem lista vazia e precisam de
    // mensagens diferentes.
    await waitFor(() => expect(screen.getByText(/buscando/i)).toBeInTheDocument());
    expect(screen.queryByText(/nenhum filme/i)).not.toBeInTheDocument();

    pendentes[0].resolver(criarResposta([criarSugestao()]));
    await waitFor(() => expect(screen.queryByText(/buscando/i)).not.toBeInTheDocument());
  });

  it("mostra erro em português e preserva o termo digitado", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 502, json: async () => ({}) }) as Response),
    );

    render(<SearchBox />);
    digitar("matrix");
    avancarDebounce();

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("alert").textContent).toMatch(/n[ãa]o foi poss[ií]vel/i);
    expect(screen.getByRole("combobox")).toHaveValue("matrix");
  });

  it("avisa quando há mais resultados do que os exibidos", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    digitar("aventura");
    avancarDebounce();

    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([criarSugestao()], { truncated: true }));

    await waitFor(() => expect(screen.getByText(/mais resultados/i)).toBeInTheDocument());
  });

  it("move o descendente ativo com as setas em vez de mover o foco", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    const campo = screen.getByRole("combobox");
    campo.focus();

    digitar("a");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(
      criarResposta([
        criarSugestao({ title: "Alfa", slug: "alfa", movie_path: "/filmes/alfa" }),
        criarSugestao({ title: "Beta", slug: "beta", movie_path: "/filmes/beta" }),
      ]),
    );

    await waitFor(() => expect(screen.getByRole("listbox")).toBeInTheDocument());
    const opcoes = within(screen.getByRole("listbox")).getAllByRole("option");

    fireEvent.keyDown(campo, { key: "ArrowDown" });
    expect(campo).toHaveAttribute("aria-activedescendant", opcoes[0].id);
    // Foco virtual: o cursor não sai do campo (R4).
    expect(document.activeElement).toBe(campo);

    fireEvent.keyDown(campo, { key: "ArrowDown" });
    expect(campo).toHaveAttribute("aria-activedescendant", opcoes[1].id);

    fireEvent.keyDown(campo, { key: "ArrowUp" });
    expect(campo).toHaveAttribute("aria-activedescendant", opcoes[0].id);
  });

  it("abre o filme destacado ao apertar Enter", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    const campo = screen.getByRole("combobox");
    campo.focus();

    digitar("matrix");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([criarSugestao({ movie_path: "/filmes/matrix" })]));

    await waitFor(() => expect(screen.getByRole("listbox")).toBeInTheDocument());

    fireEvent.keyDown(campo, { key: "ArrowDown" });
    fireEvent.keyDown(campo, { key: "Enter" });

    expect(rotasVisitadas).toEqual(["/filmes/matrix"]);
  });

  it("não navega ao apertar Enter sem opção destacada", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    const campo = screen.getByRole("combobox");

    digitar("matrix");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([criarSugestao()]));
    await waitFor(() => expect(screen.getByRole("listbox")).toBeInTheDocument());

    fireEvent.keyDown(campo, { key: "Enter" });

    expect(rotasVisitadas).toEqual([]);
  });

  it("fecha a lista com Esc sem tirar o foco do campo", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    const campo = screen.getByRole("combobox");
    campo.focus();

    digitar("matrix");
    avancarDebounce();
    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([criarSugestao()]));

    await waitFor(() => expect(screen.getByRole("listbox")).toBeInTheDocument());

    fireEvent.keyDown(campo, { key: "Escape" });

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(document.activeElement).toBe(campo);
    expect(campo).toHaveAttribute("aria-expanded", "false");
  });

  it("não dispara busca com o campo vazio ou só com espaços", async () => {
    const { stub } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);

    digitar("   ");
    avancarDebounce();
    digitar("");
    avancarDebounce();

    expect(stub).not.toHaveBeenCalled();
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("limita o tamanho do termo aceito pelo campo", () => {
    render(<SearchBox />);

    expect(screen.getByRole("combobox")).toHaveAttribute("maxLength", "80");
  });

  it("anuncia a quantidade de resultados a tecnologias assistivas", async () => {
    const { stub, pendentes } = criarFetchControlavel();
    vi.stubGlobal("fetch", stub);

    render(<SearchBox />);
    digitar("matrix");
    avancarDebounce();

    await waitFor(() => expect(pendentes).toHaveLength(1));
    pendentes[0].resolver(criarResposta([criarSugestao(), criarSugestao({ slug: "outro" })]));

    await waitFor(() => {
      expect(screen.getByRole("status").textContent).toMatch(/2/);
    });
  });
});
