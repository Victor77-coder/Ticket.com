import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ReservationPanel from "@/components/seats/ReservationPanel";
import SeatSelection from "@/components/seats/SeatSelection";
import { situacaoDoAssento } from "@/components/seats/Seat";
import type { Assento, Fileira, MapaSessao, Reserva } from "@/lib/types";

// O mock global de `tests/setup.tsx` só registra as rotas visitadas. Aqui a
// navegação e a recarga são asserção — o 401 conduz à entrada e o 409 recarrega
// o mapa —, então este arquivo substitui o mock por espiões.
const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push,
    refresh,
    replace: () => {},
    prefetch: () => {},
    back: () => {},
    forward: () => {},
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

let contador = 0;

function criarAssento(sobrescreve: Partial<Assento> = {}): Assento {
  contador += 1;
  return {
    id: contador,
    numero: ((contador - 1) % 10) + 1,
    tipo: "comum",
    situacao: "livre",
    ...sobrescreve,
  };
}

function criarFileira(letra: string, quantidade = 10): Fileira {
  return {
    letra,
    assentos: Array.from({ length: quantidade }, (_, i) =>
      criarAssento({ numero: i + 1 }),
    ),
  };
}

function criarMapa(sobrescreve: Partial<MapaSessao> = {}): MapaSessao {
  return {
    id: 1,
    filme: { titulo: "A Odisseia", slug: "a-odisseia" },
    sala: { nome: "Sala 1" },
    inicio: "2026-08-12T19:30:00-03:00",
    preco: "32.00",
    esgotada: false,
    limite_por_reserva: 6,
    fileiras: [criarFileira("A"), criarFileira("B")],
    ...sobrescreve,
  };
}

function lugares() {
  return screen.getAllByRole("button", { name: /^Fileira/ });
}

// --- Os quatro estados (FR-007, FR-008) ------------------------------------

describe("os quatro estados do lugar", () => {
  it("distingue livre, selecionado, tomado e acessibilidade", async () => {
    const usuario = userEvent.setup();
    const fileira = criarFileira("A", 3);
    fileira.assentos[1] = criarAssento({ situacao: "tomado", numero: 2 });
    fileira.assentos[2] = criarAssento({ tipo: "acessibilidade", numero: 3 });

    render(<SeatSelection mapa={criarMapa({ fileiras: [fileira] })} />);

    const [livre, tomado, acessivel] = lugares();

    expect(livre).toHaveAttribute("data-situacao", "livre");
    expect(tomado).toHaveAttribute("data-situacao", "tomado");
    expect(acessivel).toHaveAttribute("data-situacao", "acessibilidade");

    await usuario.click(livre);
    expect(livre).toHaveAttribute("data-situacao", "selecionado");
  });

  it("cada estado tem rótulo próprio, não só cor", () => {
    const fileira = criarFileira("A", 3);
    fileira.assentos[1] = criarAssento({ situacao: "tomado", numero: 2 });
    fileira.assentos[2] = criarAssento({ tipo: "acessibilidade", numero: 3 });

    render(<SeatSelection mapa={criarMapa({ fileiras: [fileira] })} />);

    expect(screen.getByLabelText("Fileira A, lugar 1, livre")).toBeInTheDocument();
    expect(screen.getByLabelText("Fileira A, lugar 2, indisponível")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Fileira A, lugar 3, reservado para acessibilidade"),
    ).toBeInTheDocument();
  });

  it("a regra de situação não depende de renderização", () => {
    const livre = criarAssento();
    const tomado = criarAssento({ situacao: "tomado" });
    const acessivel = criarAssento({ tipo: "acessibilidade" });

    expect(situacaoDoAssento(livre, false)).toBe("livre");
    expect(situacaoDoAssento(livre, true)).toBe("selecionado");
    expect(situacaoDoAssento(tomado, false)).toBe("tomado");
    // Tomado vence acessibilidade: o lugar de acessibilidade que já foi
    // reservado precisa ler como indisponível, não como "reservado para
    // acessibilidade" — a segunda frase sugeriria que ainda dá para pedir.
    expect(situacaoDoAssento(tomado, true)).toBe("tomado");
    expect(situacaoDoAssento(acessivel, false)).toBe("acessibilidade");
  });

  it("a legenda nomeia os quatro estados", () => {
    render(<SeatSelection mapa={criarMapa()} />);

    const legenda = screen.getByRole("list");
    for (const nome of ["Livre", "Selecionado", "Indisponível", "Acessibilidade"]) {
      expect(within(legenda).getByText(nome)).toBeInTheDocument();
    }
  });
});

// --- Seleção (FR-012, FR-014) ----------------------------------------------

describe("seleção", () => {
  it("acionar de novo desmarca", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 3)] })} />);

    const primeiro = lugares()[0];

    await usuario.click(primeiro);
    expect(primeiro).toHaveAttribute("aria-pressed", "true");

    await usuario.click(primeiro);
    expect(primeiro).toHaveAttribute("aria-pressed", "false");
  });

  it("lugar tomado não entra na seleção", async () => {
    const usuario = userEvent.setup();
    const fileira = criarFileira("A", 2);
    fileira.assentos[0] = criarAssento({ situacao: "tomado", numero: 1 });

    render(<SeatSelection mapa={criarMapa({ fileiras: [fileira] })} />);

    await usuario.click(lugares()[0]);

    expect(screen.getByText(/Escolha até 6 lugares/)).toBeInTheDocument();
  });

  it("lugar de acessibilidade não entra no fluxo comum", async () => {
    const usuario = userEvent.setup();
    const fileira = criarFileira("A", 2);
    fileira.assentos[0] = criarAssento({ tipo: "acessibilidade", numero: 1 });

    render(<SeatSelection mapa={criarMapa({ fileiras: [fileira] })} />);

    await usuario.click(lugares()[0]);

    expect(screen.getByText(/Escolha até 6 lugares/)).toBeInTheDocument();
  });

  it("mostra quantidade e total da seleção", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 3)] })} />);

    const [um, dois] = lugares();

    await usuario.click(um);
    expect(screen.getByText("1 lugar")).toBeInTheDocument();

    await usuario.click(dois);
    expect(screen.getByText("2 lugares")).toBeInTheDocument();
    expect(screen.getByText("R$ 64,00")).toBeInTheDocument();
  });

  it("nomeia os lugares escolhidos por fileira e número", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 3)] })} />);

    await usuario.click(lugares()[2]);

    expect(screen.getByText(/A3/)).toBeInTheDocument();
  });

  it("informa o limite ao ser atingido, e não adiciona", async () => {
    const usuario = userEvent.setup();
    render(
      <SeatSelection
        mapa={criarMapa({ limite_por_reserva: 2, fileiras: [criarFileira("A", 4)] })}
      />,
    );

    const [um, dois, tres] = lugares();
    await usuario.click(um);
    await usuario.click(dois);
    await usuario.click(tres);

    expect(screen.getByRole("alert")).toHaveTextContent(/máximo 2 lugares/);
    expect(tres).toHaveAttribute("aria-pressed", "false");
    expect(screen.getByText("2 lugares")).toBeInTheDocument();
  });

  it("confirmar fica indisponível sem nenhum lugar escolhido", () => {
    render(<SeatSelection mapa={criarMapa()} />);

    expect(screen.getByRole("button", { name: /Confirmar lugares/ })).toBeDisabled();
  });

  it("mapa e resumo convivem no mesmo arranjo", () => {
    render(<SeatSelection mapa={criarMapa()} />);

    expect(document.querySelector("[data-layout='compra']")).toBeInTheDocument();
    expect(screen.getByText("Tela")).toBeInTheDocument();
    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText(/Sala 1/)).toBeInTheDocument();
  });
});

// --- Teclado (FR-011, SC-008) ----------------------------------------------

describe("operação por teclado", () => {
  it("todo lugar é alcançável por tabulação, inclusive os indisponíveis", async () => {
    const usuario = userEvent.setup();
    const fileira = criarFileira("A", 3);
    fileira.assentos[1] = criarAssento({ situacao: "tomado", numero: 2 });

    render(<SeatSelection mapa={criarMapa({ fileiras: [fileira] })} />);

    const [um, dois, tres] = lugares();

    await usuario.tab();
    expect(um).toHaveFocus();
    await usuario.tab();
    // `aria-disabled` em vez de `disabled` é o que mantém o lugar tomado na
    // ordem de tabulação. Com `disabled` ele sumiria, e quem navega por
    // teclado deixaria de saber que existe um lugar ali.
    expect(dois).toHaveFocus();
    await usuario.tab();
    expect(tres).toHaveFocus();
  });

  it("seleciona com a tecla Enter", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 2)] })} />);

    await usuario.tab();
    await usuario.keyboard("{Enter}");

    expect(lugares()[0]).toHaveAttribute("aria-pressed", "true");
  });

  it("não há armadilha de foco: o botão de confirmar é alcançável", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 2)] })} />);

    // Escolher antes de tabular até o fim é obrigatório: sem seleção o botão
    // está desabilitado, e elemento desabilitado sai da ordem de tabulação.
    await usuario.tab();
    await usuario.keyboard("{Enter}");

    // Desde a 014 o resumo tem um alvo a mais por lugar escolhido — o
    // alternador de meia-entrada. Tabular até o fim continua alcançando o
    // confirmar; o que este teste protege é a AUSÊNCIA de armadilha, não uma
    // contagem fixa de tabulações.
    const confirmar = screen.getByRole("button", { name: /Confirmar lugares/ });
    for (let i = 0; i < 10 && document.activeElement !== confirmar; i += 1) {
      await usuario.tab();
    }

    expect(confirmar).toHaveFocus();
  });
});

// --- Estados explicativos (FR-030, FR-031) ---------------------------------

describe("sessão esgotada", () => {
  it("explica em português em vez de mostrar sala vazia", () => {
    render(<SeatSelection mapa={criarMapa({ esgotada: true })} />);

    expect(screen.getByText("Esta sessão esgotou")).toBeInTheDocument();
    expect(screen.getByText(/Escolha outro horário/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Fileira/ })).not.toBeInTheDocument();
  });
});

// --- Autorização do visitante (FR-010, FR-026) -----------------------------

describe("visitante sem sessão", () => {
  beforeEach(() => {
    push.mockReset();
    refresh.mockReset();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({ detail: "Entre para reservar." }, { status: 401 }),
      ),
    );
  });

  it("vê o mapa e a confirmação conduz à entrada com retorno", async () => {
    const usuario = userEvent.setup();
    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 2)] })} />);

    expect(screen.getByLabelText("Fileira A, lugar 1, livre")).toBeInTheDocument();

    await usuario.click(lugares()[0]);
    await usuario.click(screen.getByRole("button", { name: /Confirmar lugares/ }));

    expect(push).toHaveBeenCalledWith("/entrar?next=%2Fsessoes%2F1");
  });
});

// --- Conflito e confirmação (FR-019, FR-020, FR-030) ------------------------

describe("confirmação da reserva", () => {
  beforeEach(() => {
    push.mockReset();
    refresh.mockReset();
  });

  it("nomeia o lugar perdido no 409 e recarrega o mapa", async () => {
    const usuario = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json(
          {
            detail: "O lugar A2 foi reservado(s) por outra pessoa agora há pouco. Escolha outro.",
            assentos_indisponiveis: [{ fileira: "A", numero: 2 }],
          },
          { status: 409 },
        ),
      ),
    );

    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 3)] })} />);

    await usuario.click(lugares()[0]);
    await usuario.click(screen.getByRole("button", { name: /Confirmar lugares/ }));

    expect(screen.getByRole("alert")).toHaveTextContent(/A2/);
    expect(refresh).toHaveBeenCalled();
  });

  it("mostra a reserva confirmada com prazo e caminho ao pagamento", async () => {
    const usuario = userEvent.setup();
    const reserva: Reserva = {
      id: 77,
      sessao: 1,
      assentos: [{ fileira: "A", numero: 1 }],
      total: "32.00",
      expira_em: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      situacao: "reservada",
    };

    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json(reserva, { status: 201 })),
    );

    render(<SeatSelection mapa={criarMapa({ fileiras: [criarFileira("A", 2)] })} />);

    await usuario.click(lugares()[0]);
    await usuario.click(screen.getByRole("button", { name: /Confirmar lugares/ }));

    expect(screen.getByText("Lugares reservados")).toBeInTheDocument();
    expect(screen.getByText(/A1/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Continuar para pagamento/ })).toHaveAttribute(
      "href",
      "/pagamento/77",
    );
  });
});

describe("prazo da reserva", () => {
  it("exibe o estado expirado com caminho para escolher de novo", () => {
    const reserva: Reserva = {
      id: 77,
      sessao: 12,
      assentos: [{ fileira: "B", numero: 4 }],
      total: "30.00",
      expira_em: new Date(Date.now() - 1000).toISOString(),
      situacao: "expirada",
    };

    render(<ReservationPanel reserva={reserva} />);

    expect(screen.getByText("Esta reserva expirou")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Escolher lugares de novo/ })).toHaveAttribute(
      "href",
      "/sessoes/12",
    );
  });
});
