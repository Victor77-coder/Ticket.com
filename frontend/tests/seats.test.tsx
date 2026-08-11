import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import SeatSelection from "@/components/seats/SeatSelection";
import { situacaoDoAssento } from "@/components/seats/Seat";
import type { Assento, Fileira, MapaSessao } from "@/lib/types";

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
    expect(screen.getByText(/1 lugar ·/)).toBeInTheDocument();

    await usuario.click(dois);
    expect(screen.getByText(/2 lugares ·/)).toBeInTheDocument();
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
    expect(screen.getByText(/2 lugares ·/)).toBeInTheDocument();
  });

  it("confirmar fica indisponível sem nenhum lugar escolhido", () => {
    render(<SeatSelection mapa={criarMapa()} />);

    expect(screen.getByRole("button", { name: /Confirmar lugares/ })).toBeDisabled();
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
    await usuario.tab();
    await usuario.tab();

    expect(screen.getByRole("button", { name: /Confirmar lugares/ })).toHaveFocus();
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
