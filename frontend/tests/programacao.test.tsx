import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
const refresh = vi.fn();
const push = vi.fn();
vi.mock("next/navigation", () => ({
  redirect: (destino: string) => {
    redirecionou(destino);
    throw new Error(`REDIRECT:${destino}`);
  },
  // A grade virou ilha cliente na US5: as ações de publicar e cancelar
  // atualizam a linha e pedem ao servidor para reler a grade.
  useRouter: () => ({ refresh, push, replace: vi.fn() }),
}));

const buscarGrade = vi.fn();
vi.mock("@/lib/api", () => ({
  COOKIE_SESSAO: "sessionid",
  fetchGrade: (...args: unknown[]) => buscarGrade(...args),
}));

// Importados depois dos `vi.mock` acima, como a suíte da portaria já faz: os
// dois módulos leem `@/lib/api` e `next/headers` no topo.
const { default: ProgramacaoPage } = await import("@/app/programacao/page");
const { BuscaDeFilme } = await import("@/components/programacao/BuscaDeFilme");

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

// --- Busca no TMDb (US3) --------------------------------------------------

describe("a busca no TMDb", () => {
  function responder(resposta: { ok: boolean; status?: number; body: unknown }) {
    const fn = vi.fn().mockResolvedValue({
      ok: resposta.ok,
      status: resposta.status ?? (resposta.ok ? 200 : 502),
      json: async () => resposta.body,
    });
    vi.stubGlobal("fetch", fn);
    return fn;
  }

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lista os resultados e marca o que já está no catálogo", async () => {
    const usuario = userEvent.setup();
    responder({
      ok: true,
      body: {
        termo: "duna",
        count: 1,
        results: [
          {
            tmdb_id: 693134,
            titulo: "Duna: Parte Dois",
            ano: 2024,
            poster_url: null,
            ja_no_catalogo: true,
          },
        ],
      },
    });

    render(<BuscaDeFilme onImportado={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Título"), "duna");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));

    expect(await screen.findByText(/Duna: Parte Dois/)).toBeInTheDocument();
    expect(screen.getByText("Já no catálogo")).toBeInTheDocument();
  });

  it("diz que nada foi encontrado, com o termo dentro (US3 cenário 7)", async () => {
    const usuario = userEvent.setup();
    responder({ ok: true, body: { termo: "asdfgh", count: 0, results: [] } });

    render(<BuscaDeFilme onImportado={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Título"), "asdfgh");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));

    // Não uma área em branco: o termo aparece na frase, para a pessoa saber a
    // que busca a resposta pertence.
    expect(await screen.findByText(/Nada encontrado para “asdfgh”/)).toBeInTheDocument();
  });

  it("mostra a frase do servidor quando o TMDb está fora (US3 cenário 6)", async () => {
    const usuario = userEvent.setup();
    responder({
      ok: false,
      status: 502,
      body: { detail: "O TMDb não respondeu em 10s. Verifique a conexão e tente novamente." },
    });

    render(<BuscaDeFilme onImportado={vi.fn()} />);
    await usuario.type(screen.getByLabelText("Título"), "duna");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("O TMDb não respondeu em 10s");
    // FR-014: a degradação é só da busca, e a tela diz isso em vez de parecer
    // que a área inteira quebrou.
    expect(alerta).toHaveTextContent("continua podendo programar com os filmes do catálogo");
  });

  it("entrega o filme importado a quem o pediu, mesmo quando já existia", async () => {
    const usuario = userEvent.setup();
    const aoImportar = vi.fn();
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({
          termo: "duna",
          count: 1,
          results: [
            { tmdb_id: 693134, titulo: "Duna", ano: 2024, poster_url: null, ja_no_catalogo: true },
          ],
        }),
      })
      // `200` — o filme já estava no catálogo. NÃO é erro: pediram um filme e
      // receberam um filme (FR-012).
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ id: 7, titulo: "Duna", tmdb_id: 693134, sessoes: 0 }),
      });
    vi.stubGlobal("fetch", fetchMock);

    render(<BuscaDeFilme onImportado={aoImportar} />);
    await usuario.type(screen.getByLabelText("Título"), "duna");
    await usuario.click(screen.getByRole("button", { name: "Buscar" }));
    await usuario.click(await screen.findByRole("button", { name: "Usar este" }));

    expect(aoImportar).toHaveBeenCalledWith(
      expect.objectContaining({ id: 7, titulo: "Duna" }),
    );
  });
});

// --- Conduzir a grade (US5) -----------------------------------------------

describe("as ações da grade", () => {
  function linha(over: Partial<SessaoDaGrade> = {}) {
    return { count: 1, results: [sessao(over)] };
  }

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("oferece editar e publicar só para rascunho", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: linha({ estado: "draft", estado_rotulo: "Rascunho", pode_editar: true, pode_publicar: true }),
    });

    render(await ProgramacaoPage());

    expect(screen.getByRole("link", { name: "Editar" })).toHaveAttribute(
      "href",
      "/programacao/sessoes/1",
    );
    expect(screen.getByRole("button", { name: "Publicar" })).toBeEnabled();
  });

  it("não oferece editar nem publicar para sessão publicada", async () => {
    buscarGrade.mockResolvedValue({ ok: true, status: 200, data: linha() });

    render(await ProgramacaoPage());

    expect(screen.queryByRole("link", { name: "Editar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Publicar" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancelar" })).toBeInTheDocument();
  });

  it("desabilita publicar COM EXPLICAÇÃO, em vez de esconder (FR-037)", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: linha({
        estado: "draft",
        estado_rotulo: "Rascunho",
        pode_editar: true,
        pode_publicar: false,
      }),
    });

    render(await ProgramacaoPage());

    // O controle continua visível: um botão que some não ensina nada e faz a
    // pessoa procurar o que sumiu.
    expect(screen.getByRole("button", { name: "Publicar" })).toBeDisabled();
    expect(screen.getByText("horário no passado")).toBeInTheDocument();
  });

  it("sessão cancelada não oferece ação nenhuma — é estado terminal", async () => {
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: linha({
        estado: "cancelled",
        estado_rotulo: "Cancelada",
        a_venda: false,
        pode_editar: false,
        pode_publicar: false,
        pode_cancelar: false,
      }),
    });

    render(await ProgramacaoPage());

    expect(screen.queryByRole("button", { name: "Cancelar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Editar" })).not.toBeInTheDocument();
  });

  it("pede confirmação antes de cancelar, e não cancela no primeiro clique", async () => {
    const usuario = userEvent.setup();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    buscarGrade.mockResolvedValue({ ok: true, status: 200, data: linha() });

    render(await ProgramacaoPage());
    await usuario.click(screen.getByRole("button", { name: "Cancelar" }));

    // Cancelada é terminal, e um clique acidental não tem desfazer.
    expect(fetchMock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Confirmar" })).toBeInTheDocument();
  });

  it("mostra a frase do servidor quando a ação é recusada", async () => {
    const usuario = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 409,
        json: async () => ({ detail: "Esta sessão já está publicada." }),
      }),
    );
    buscarGrade.mockResolvedValue({
      ok: true,
      status: 200,
      data: linha({ estado: "draft", estado_rotulo: "Rascunho", pode_publicar: true }),
    });

    render(await ProgramacaoPage());
    await usuario.click(screen.getByRole("button", { name: "Publicar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Esta sessão já está publicada.",
    );
  });
});
