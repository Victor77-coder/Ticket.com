import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import CartaoDeSessao from "@/components/sessao/CartaoDeSessao";
import type { MapaSessao, Screening } from "@/lib/types";

/**
 * A1–A7 e P1–P4 de contracts/paineis-do-cartao.md.
 *
 * Os dois painéis são testados a partir do CARTÃO, e não isolados, porque M6
 * — um painel por vez — só é observável com os dois montados, e porque a ação
 * que abre é parte do que se promete.
 */

function sessao(
  sobrescreve: Partial<Screening> & Pick<Screening, "id" | "starts_at" | "room_name">,
): Screening {
  return { price: "32.00", has_available_seats: true, ...sobrescreve };
}

const HORARIOS = [
  sessao({ id: 10, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
  sessao({ id: 11, starts_at: "2026-08-12T21:00:00-03:00", room_name: "Sala 1", price: "45.00" }),
];

function mapa(sobrescreve: Partial<MapaSessao> = {}): MapaSessao {
  return {
    id: 10,
    filme: { titulo: "A Odisseia", slug: "a-odisseia" },
    sala: { nome: "Sala 1" },
    inicio: "2026-08-12T19:00:00-03:00",
    preco: "32.00",
    esgotada: false,
    limite_por_reserva: 6,
    fileiras: [
      {
        letra: "A",
        assentos: [
          { id: 1, numero: 1, tipo: "comum", situacao: "livre" },
          { id: 2, numero: 2, tipo: "comum", situacao: "tomado" },
          { id: 3, numero: 3, tipo: "comum", situacao: "livre" },
        ],
      },
    ],
    ...sobrescreve,
  };
}

function responder(corpo: unknown, ok = true, status = 200) {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(corpo),
  } as Response);
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(() => responder(mapa())));
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("painel de assentos", () => {
  it("A1/A2 — desenha a lotação e diz quantos lugares restam", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    expect(await screen.findByText(/lugares livres/)).toBeInTheDocument();
    const painel = screen.getByRole("dialog");
    expect(within(painel).getByText("2")).toBeInTheDocument();
    // A legenda nomeia os dois estados: a distinção não depende de cor.
    expect(within(painel).getByText("Livre")).toBeInTheDocument();
    expect(within(painel).getByText("Ocupado")).toBeInTheDocument();
  });

  it("A3 — nenhum assento é acionável: é prévia, não seleção", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));
    await screen.findByText(/lugares livres/);

    const painel = screen.getByRole("dialog");
    // Os únicos controles são: fechar, os horários do seletor, e seguir ao mapa.
    const botoes = within(painel).getAllByRole("button");
    expect(botoes).toHaveLength(1 + HORARIOS.length);
    expect(within(painel).getAllByRole("link")).toHaveLength(1);
  });

  it("A4 — oferece o caminho para o mapa da sessão escolhida", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    const seguir = await screen.findByRole("link", { name: "Escolher lugares" });
    expect(seguir).toHaveAttribute("href", "/sessoes/10");
  });

  it("A4 — sessão esgotada não oferece o caminho, e diz por quê", async () => {
    vi.stubGlobal("fetch", vi.fn(() => responder(mapa({ esgotada: true }))));
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    expect(await screen.findByText(/esgotada/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Escolher lugares" })).not.toBeInTheDocument();
  });

  it("A5 — comunica espera enquanto carrega", async () => {
    let liberar: (valor: Response) => void = () => {};
    vi.stubGlobal(
      "fetch",
      vi.fn(() => new Promise<Response>((resolve) => (liberar = resolve))),
    );
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    expect(screen.getByText(/carregando a lotação/i)).toBeInTheDocument();

    liberar({ ok: true, status: 200, json: () => Promise.resolve(mapa()) } as Response);
    await screen.findByText(/lugares livres/);
  });

  it("A6 — falha vira mensagem em português, com a próxima ação", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        responder({ detail: "Não foi possível carregar a lotação desta sessão. Tente de novo." }, false, 502),
      ),
    );
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    const aviso = await screen.findByRole("alert");
    expect(aviso).toHaveTextContent(/não foi possível carregar a lotação/i);
    expect(aviso).toHaveTextContent(/tente de novo/i);
  });

  it("A7 — sala sem lugares é explicada, não desenhada vazia", async () => {
    vi.stubGlobal("fetch", vi.fn(() => responder(mapa({ fileiras: [] }))));
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));

    expect(await screen.findByText(/ainda não tem lugares cadastrados/i)).toBeInTheDocument();
  });
});

describe("painel de preços", () => {
  it("P1 — mostra inteira e meia", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Preços/ }));

    const painel = screen.getByRole("dialog");
    expect(within(painel).getByText("Inteira")).toBeInTheDocument();
    expect(within(painel).getByText("R$ 32,00")).toBeInTheDocument();
    expect(within(painel).getByText("Meia")).toBeInTheDocument();
    expect(within(painel).getByText("R$ 16,00")).toBeInTheDocument();
  });

  it("P2 — trocar o horário troca os valores, porque o preço é da sessão", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Preços/ }));
    const painel = screen.getByRole("dialog");
    await usuario.click(within(painel).getByRole("button", { name: "21:00" }));

    expect(within(painel).getByText("R$ 45,00")).toBeInTheDocument();
    expect(within(painel).getByText("R$ 22,50")).toBeInTheDocument();
  });

  it("P3 — declara que a meia é conferida na entrada", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Preços/ }));

    expect(screen.getByText(/conferida na entrada do cinema, mediante documento/i)).toBeInTheDocument();
  });
});

describe("os dois painéis juntos", () => {
  it("M6 — abrir um fecha o outro", async () => {
    const usuario = userEvent.setup();
    render(<CartaoDeSessao sala="Sala 1" horarios={HORARIOS} />);

    await usuario.click(screen.getByRole("button", { name: /^Assentos/ }));
    expect(screen.getByRole("dialog", { name: /^Assentos/ })).toBeInTheDocument();

    await usuario.click(screen.getByRole("button", { name: /^Preços/ }));

    await waitFor(() => {
      expect(screen.queryByRole("dialog", { name: /^Assentos/ })).not.toBeInTheDocument();
    });
    expect(screen.getByRole("dialog", { name: /^Preços/ })).toBeInTheDocument();
  });
});
