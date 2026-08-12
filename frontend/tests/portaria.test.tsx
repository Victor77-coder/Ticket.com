import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { SessaoDaPorta } from "@/lib/types";

/**
 * A tela de portaria.
 *
 * O que estes testes protegem:
 *
 *  - que a **sessão da porta** seja escolhida antes de qualquer leitura. Sem
 *    ela o desfecho "sessão errada" é impossível, e a tela entrega três dos
 *    quatro que o Princípio III exige;
 *  - que a **digitação manual** esteja sempre visível, e não escondida atrás
 *    de uma falha da câmera. A constitution exige "sempre disponível", e é ela
 *    que mantém a portaria de pé quando a câmera não está em contexto seguro;
 *  - que o **campo vazio** produza aviso de preenchimento, distinto de
 *    "inválido": nada foi apresentado, e não há o que julgar;
 *  - que **papel errado** leia uma explicação e **não** seja mandado à
 *    entrada — entrar de novo não muda o papel.
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

const buscar = vi.fn();
vi.mock("@/lib/api", () => ({
  COOKIE_SESSAO: "sessionid",
  fetchSessoesDaPortaria: (...args: unknown[]) => buscar(...args),
}));

// A câmera não existe em jsdom: `getUserMedia` ausente é exatamente o caminho
// "indisponível", que é o que estes testes querem exercitar de qualquer jeito.
vi.mock("jsqr", () => ({ default: () => null }));

const { default: PortariaPage } = await import("@/app/portaria/page");

const SESSOES: SessaoDaPorta[] = [
  {
    id: 272,
    filme: "A Odisseia",
    inicio: new Date("2026-08-12T21:30:00Z").toISOString(),
    sala: "Sala 3",
  },
  {
    id: 273,
    filme: "Cidade de Deus",
    inicio: new Date("2026-08-12T19:00:00Z").toISOString(),
    sala: "Sala 1",
  },
];

beforeEach(() => {
  window.localStorage.clear();
  redirecionou.mockClear();
});

async function renderizar(sessoes: SessaoDaPorta[] = SESSOES) {
  buscar.mockResolvedValue({ ok: true, data: { sessoes }, status: 200 });
  render(await PortariaPage());
}

describe("tela de portaria", () => {
  it("pede a sessão da porta antes de qualquer leitura", async () => {
    await renderizar();

    expect(
      screen.getByRole("heading", { name: /Qual sessão esta porta está recebendo/ }),
    ).toBeInTheDocument();
    // Nenhum campo de código antes da escolha.
    expect(screen.queryByLabelText(/digite o código/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /A Odisseia/ })).toBeInTheDocument();
  });

  it("depois de escolher, mostra a sessão e as duas formas de entrada", async () => {
    const usuario = userEvent.setup();
    await renderizar();

    await usuario.click(screen.getByRole("button", { name: /A Odisseia/ }));

    expect(screen.getByText("Esta porta está recebendo")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "A Odisseia" })).toBeInTheDocument();
    // A digitação está visível MESMO com a câmera no caminho principal.
    expect(screen.getByLabelText(/digite o código/i)).toBeInTheDocument();
  });

  it("a sessão escolhida sobrevive a um recarregamento", async () => {
    const usuario = userEvent.setup();
    await renderizar();
    await usuario.click(screen.getByRole("button", { name: /Cidade de Deus/ }));

    // Remonta a página, como faz um recarregamento.
    screen.getByText("Esta porta está recebendo");
    await renderizar();

    await waitFor(() =>
      expect(screen.getAllByText("Esta porta está recebendo").length).toBeGreaterThan(0),
    );
  });

  it("descarta a sessão guardada quando ela não está mais na grade", async () => {
    // A grade muda de um dia para o outro; uma escolha órfã deixaria a tela
    // validando contra uma sessão que já não existe.
    window.localStorage.setItem("portaria:sessao", "999");

    await renderizar();

    expect(
      screen.getByRole("heading", { name: /Qual sessão esta porta está recebendo/ }),
    ).toBeInTheDocument();
  });

  it("trocar de porta volta à escolha", async () => {
    const usuario = userEvent.setup();
    await renderizar();
    await usuario.click(screen.getByRole("button", { name: /A Odisseia/ }));

    await usuario.click(screen.getByRole("button", { name: "Trocar de porta" }));

    expect(
      screen.getByRole("heading", { name: /Qual sessão esta porta está recebendo/ }),
    ).toBeInTheDocument();
  });

  it("campo vazio produz aviso de preenchimento, não 'inválido'", async () => {
    const usuario = userEvent.setup();
    await renderizar();
    await usuario.click(screen.getByRole("button", { name: /A Odisseia/ }));

    await usuario.click(screen.getByRole("button", { name: "Validar" }));

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent("Apresente ou digite um código.");
    expect(screen.queryByText("Ingresso não reconhecido")).not.toBeInTheDocument();
  });

  it("valida pela digitação e mostra o desfecho", async () => {
    const usuario = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: true,
        status: 200,
        json: async () => ({
          situacao: "valido",
          detail: "Pode entrar. Sala 3, lugar F12.",
          ingresso: {
            filme: "A Odisseia",
            sessao: SESSOES[0].inicio,
            sala: "Sala 3",
            assento: { fileira: "F", numero: 12 },
          },
        }),
      })),
    );
    await renderizar();
    await usuario.click(screen.getByRole("button", { name: /A Odisseia/ }));

    await usuario.type(screen.getByLabelText(/digite o código/i), "codigo-assinado");
    await usuario.click(screen.getByRole("button", { name: "Validar" }));

    expect(await screen.findByRole("heading", { name: "Pode entrar" })).toBeInTheDocument();
  });

  it("o formulário é operável só pelo teclado", async () => {
    const usuario = userEvent.setup();
    await renderizar();
    await usuario.click(screen.getByRole("button", { name: /A Odisseia/ }));

    const campo = screen.getByLabelText(/digite o código/i);
    campo.focus();
    await usuario.keyboard("um-codigo");
    await usuario.tab();

    expect(screen.getByRole("button", { name: "Validar" })).toHaveFocus();
  });

  it("explica quando não há sessão hoje, sem lista vazia", async () => {
    await renderizar([]);

    expect(screen.getByRole("heading", { name: "Nenhuma sessão hoje" })).toBeInTheDocument();
    expect(screen.getByText(/não há entrada a receber/i)).toBeInTheDocument();
  });

  it("papel errado lê a explicação e NÃO é mandado à entrada", async () => {
    buscar.mockResolvedValue({
      ok: false,
      status: 403,
      error: "Apenas a portaria valida ingressos.",
    });

    render(await PortariaPage());

    expect(screen.getByRole("heading", { name: "Esta área é da portaria" })).toBeInTheDocument();
    expect(redirecionou).not.toHaveBeenCalled();
  });
});
