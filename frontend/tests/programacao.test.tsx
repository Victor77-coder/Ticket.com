import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SessaoDaGrade } from "@/lib/types";

/**
 * A área de programação.
 *
 * O que estes testes protegem:
 *
 *  - que as TRÊS superfícies de FR-007 existam: sucesso, erro e vazio. O vazio
 *    é o que costuma faltar, e uma tela em branco não é neutra — parece
 *    defeito;
 *  - que **papel errado** leia uma explicação e **não** seja mandado à entrada.
 *    Entrar de novo não muda o papel: seria caminho sem saída. É a mesma
 *    distinção que a 009 e a 010 já aplicam, agora do lado da programação;
 *  - que o estado da sessão seja legível **sem depender de cor** (FR-029) — a
 *    palavra vai no documento, não só na folha de estilo.
 */

vi.mock("next/headers", () => ({
  cookies: async () => ({ get: () => ({ value: "chave-de-sessao" }) }),
}));

const redirecionou = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (destino: string) => {
    redirecionou(destino);
    throw new Error(`REDIRECT:${destino}`);
  },
}));

const buscarGrade = vi.fn();
vi.mock("@/lib/api", () => ({
  COOKIE_SESSAO: "sessionid",
  fetchGrade: (...args: unknown[]) => buscarGrade(...args),
}));

const { default: ProgramacaoPage } = await import("@/app/programacao/page");

function sessao(over: Partial<SessaoDaGrade> = {}): SessaoDaGrade {
  return {
    id: 1,
    estado: "published",
    estado_rotulo: "Publicada",
    filme: { id: 7, titulo: "A Odisseia", poster_url: null },
    sala: { id: 1, nome: "Sala 1", lugares: 60 },
    inicio: "2026-08-14T20:30:00-03:00",
    preco: "32.00",
    ocupacao: 12,
    a_venda: true,
    pode_editar: false,
    pode_publicar: false,
    pode_cancelar: true,
    ...over,
  };
}

beforeEach(() => {
  redirecionou.mockClear();
  buscarGrade.mockReset();
});

describe("a área de programação", () => {
  it("mostra a grade quando há sessões", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: { count: 1, results: [sessao()] },
    });

    render(await ProgramacaoPage());

    expect(screen.getByRole("heading", { name: "Programação" })).toBeInTheDocument();
    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText("Sala 1")).toBeInTheDocument();
    // Ocupação sobre lugares: é a decisão que se toma olhando a linha.
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("de 60")).toBeInTheDocument();
  });

  it("convida a programar a primeira quando a grade está vazia (FR-007)", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: { count: 0, results: [] },
    });

    render(await ProgramacaoPage());

    expect(screen.getByText(/nenhuma sessão programada ainda/i)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Programar a primeira" }),
    ).toHaveAttribute("href", "/programacao/sessoes/nova");
  });

  it("explica a recusa por papel sem mandar à entrada (FR-037, R11)", async () => {
    buscarGrade.mockResolvedValue({
      ok: false,
      status: 403,
      error: "Apenas organizadores programam sessões.",
    });

    render(await ProgramacaoPage());

    expect(screen.getByRole("alert")).toHaveTextContent(/esta área é da programação/i);
    expect(screen.getByRole("link", { name: /voltar ao catálogo/i })).toBeInTheDocument();
    // A prova do R11: papel errado NUNCA é conduzido à entrada.
    expect(redirecionou).not.toHaveBeenCalled();
  });

  it("conduz à entrada quando a sessão venceu, e volta para cá", async () => {
    buscarGrade.mockResolvedValue({ ok: false, status: 401, error: "Entre para programar sessões." });

    await expect(ProgramacaoPage()).rejects.toThrow("REDIRECT:/entrar?next=/programacao");
    expect(redirecionou).toHaveBeenCalledWith("/entrar?next=/programacao");
  });

  it("diz que não carregou quando o servidor não responde", async () => {
    buscarGrade.mockResolvedValue({ ok: false, status: 0, error: "Não foi possível falar com o servidor." });

    render(await ProgramacaoPage());

    expect(screen.getByRole("alert")).toHaveTextContent(/não conseguimos carregar a grade/i);
  });
});

describe("os três estados na grade", () => {
  it("diz o estado por escrito, e não só por cor (FR-029)", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        count: 3,
        results: [
          sessao({ id: 1, estado: "draft", estado_rotulo: "Rascunho" }),
          sessao({ id: 2, estado: "published", estado_rotulo: "Publicada" }),
          sessao({ id: 3, estado: "cancelled", estado_rotulo: "Cancelada" }),
        ],
      },
    });

    render(await ProgramacaoPage());

    // A palavra está no DOCUMENTO. Uma folha de estilo que sumisse deixaria a
    // tela feia e ainda assim legível — é o que "não depender só de cor"
    // significa na prática.
    for (const rotulo of ["Rascunho", "Publicada", "Cancelada"]) {
      expect(screen.getByText(rotulo)).toBeInTheDocument();
    }
  });

  it("agrupa por dia, porque quem programa pensa em dia", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: {
        count: 2,
        results: [
          sessao({ id: 1, inicio: "2026-08-14T20:30:00-03:00" }),
          sessao({ id: 2, inicio: "2026-08-15T20:30:00-03:00" }),
        ],
      },
    });

    render(await ProgramacaoPage());

    expect(screen.getByRole("heading", { name: /14\/08/ })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /15\/08/ })).toBeInTheDocument();
  });
});
