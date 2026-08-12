import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import FilmeCliente from "@/app/filmes/[slug]/FilmeCliente";
import type { MovieDetail, Screening, TrailerDoFilme } from "@/lib/types";

function sessao(sobrescreve: Partial<Screening> & Pick<Screening, "id" | "starts_at" | "room_name">): Screening {
  return {
    price: "32.00",
    has_available_seats: true,
    ...sobrescreve,
  };
}

function filme(sobrescreve: Partial<MovieDetail> = {}): MovieDetail {
  return {
    id: 1,
    slug: "a-odisseia",
    title: "A Odisseia",
    synopsis: "Uma viagem longa demais para caber num cartão.",
    release_date: "2026-12-01",
    backdrop_url: null,
    poster_url: null,
    certification_br: "14",
    runtime_minutes: 148,
    genres: ["Ficção científica"],
    screenings: [
      sessao({ id: 10, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
      sessao({
        id: 11,
        starts_at: "2026-08-12T21:00:00-03:00",
        room_name: "Sala 2",
        has_available_seats: false,
      }),
      sessao({ id: 12, starts_at: "2026-08-13T19:00:00-03:00", room_name: "Sala 1" }),
    ],
    trailers: [
      {
        provider: "youtube",
        external_key: "abc123",
        kind: "trailer",
        name: "Trailer oficial",
      } satisfies TrailerDoFilme,
    ],
    ...sobrescreve,
  };
}

describe("grade de sessões", () => {
  it("mostra o seletor de dia e agrupa horários por sala", () => {
    render(<FilmeCliente filme={filme()} />);

    expect(screen.getByRole("tablist", { name: /dias com sessão/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sala 1" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Sala 2" })).toBeInTheDocument();
  });

  it("horário disponível é o link Escolher lugares — até o mapa", () => {
    render(<FilmeCliente filme={filme()} />);

    const alvo = screen.getByRole("link", { name: /^Escolher lugares —/ });
    expect(alvo).toHaveAttribute("href", "/sessoes/10");
  });

  it("sessão esgotada não é link e diz Esgotada", () => {
    render(<FilmeCliente filme={filme()} />);

    expect(screen.getByText("Esgotada")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Sala 2/ })).not.toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /^Escolher lugares —/ })).toHaveLength(1);
  });

  it("trocar o dia mostra só os horários daquele dia", async () => {
    const usuario = userEvent.setup();
    render(<FilmeCliente filme={filme()} />);

    const dias = screen.getByRole("tablist", { name: /dias com sessão/i });
    const botoes = within(dias).getAllByRole("tab");
    expect(botoes.length).toBeGreaterThan(1);

    await usuario.click(botoes[1]);

    expect(screen.queryByRole("heading", { name: "Sala 2" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Escolher lugares —/ })).toHaveAttribute(
      "href",
      "/sessoes/12",
    );
  });
});

describe("seções Sessões, Sobre e Trailers", () => {
  it("as três seções existem e só uma está visível", async () => {
    const usuario = userEvent.setup();
    render(<FilmeCliente filme={filme()} />);

    expect(screen.getByRole("tab", { name: "Sessões" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: "Sobre" })).toHaveAttribute("aria-selected", "false");
    expect(screen.getByRole("tab", { name: "Trailers" })).toHaveAttribute("aria-selected", "false");

    await usuario.click(screen.getByRole("tab", { name: "Sobre" }));

    expect(screen.getByRole("tab", { name: "Sobre" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText(/viagem longa demais/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Escolher lugares —/ })).not.toBeInTheDocument();
  });

  it("Sobre mostra sinopse e omite campo ausente — nunca N/A", async () => {
    const usuario = userEvent.setup();
    render(
      <FilmeCliente
        filme={filme({ certification_br: null, runtime_minutes: null, genres: [] })}
      />,
    );

    await usuario.click(screen.getByRole("tab", { name: "Sobre" }));

    expect(screen.getByText(/viagem longa demais/)).toBeInTheDocument();
    expect(screen.queryByText("N/A")).not.toBeInTheDocument();
    expect(screen.queryByText(/classificação/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/elenco/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/direção/i)).not.toBeInTheDocument();
  });

  it("Trailers reproduz a partir de um botão, sem alvo desabilitado", async () => {
    const usuario = userEvent.setup();
    render(<FilmeCliente filme={filme()} />);

    await usuario.click(screen.getByRole("tab", { name: "Trailers" }));

    const reproduzir = screen.getByRole("button", { name: /reproduzir trailer oficial/i });
    expect(reproduzir).not.toBeDisabled();

    await usuario.click(reproduzir);

    expect(screen.getByTitle("Trailer de A Odisseia")).toBeInTheDocument();
  });

  it("sem trailer, a seção explica e continua visível", async () => {
    const usuario = userEvent.setup();
    render(<FilmeCliente filme={filme({ trailers: [] })} />);

    await usuario.click(screen.getByRole("tab", { name: "Trailers" }));

    expect(screen.getByText(/ainda não tem trailer/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /reproduzir/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /disabled/i })).not.toBeInTheDocument();
  });

  it("filme sem sessão ainda oferece Sobre e Trailers", async () => {
    const usuario = userEvent.setup();
    render(<FilmeCliente filme={filme({ screenings: [], trailers: [] })} />);

    expect(screen.getByText(/não possui sessões programadas/i)).toBeInTheDocument();

    await usuario.click(screen.getByRole("tab", { name: "Sobre" }));
    expect(screen.getByText(/viagem longa demais/)).toBeInTheDocument();

    await usuario.click(screen.getByRole("tab", { name: "Trailers" }));
    expect(screen.getByText(/ainda não tem trailer/i)).toBeInTheDocument();
  });
});
