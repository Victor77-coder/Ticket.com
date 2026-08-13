import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import FilmeCliente from "@/app/filmes/[slug]/FilmeCliente";
import type { MovieDetail, Screening } from "@/lib/types";

/**
 * As promessas C1–C7 de contracts/paineis-do-cartao.md.
 *
 * O teste renderiza `FilmeCliente` inteiro, e não `CartaoDeSessao` isolado, de
 * propósito: C1 é sobre AGRUPAMENTO — um cartão por sala dentro do dia ativo —,
 * e agrupamento só existe quando há mais de uma sala para agrupar.
 */

function sessao(
  sobrescreve: Partial<Screening> & Pick<Screening, "id" | "starts_at" | "room_name">,
): Screening {
  return { price: "32.00", has_available_seats: true, ...sobrescreve };
}

function filme(sobrescreve: Partial<MovieDetail> = {}): MovieDetail {
  return {
    id: 1,
    slug: "a-odisseia",
    title: "A Odisseia",
    synopsis: "",
    release_date: "2026-12-01",
    backdrop_url: null,
    poster_url: null,
    certification_br: "14",
    runtime_minutes: 148,
    genres: [],
    screenings: [
      sessao({ id: 10, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
      sessao({ id: 11, starts_at: "2026-08-12T21:00:00-03:00", room_name: "Sala 1" }),
      sessao({
        id: 12,
        starts_at: "2026-08-12T20:00:00-03:00",
        room_name: "Sala 2",
        price: "45.00",
      }),
    ],
    trailers: [],
    ...sobrescreve,
  };
}

describe("cartão de sessão", () => {
  it("C1 — um cartão por sala, com os horários daquela sala dentro", () => {
    render(<FilmeCliente filme={filme()} />);

    const salaUm = screen.getByRole("region", { name: "Sala 1" });
    const salaDois = screen.getByRole("region", { name: "Sala 2" });

    expect(within(salaUm).getByText("19:00")).toBeInTheDocument();
    expect(within(salaUm).getByText("21:00")).toBeInTheDocument();
    expect(within(salaUm).queryByText("20:00")).not.toBeInTheDocument();
    expect(within(salaDois).getByText("20:00")).toBeInTheDocument();
  });

  it("C2 — o nome da sala é cabeçalho e rotula a região", () => {
    render(<FilmeCliente filme={filme()} />);

    expect(screen.getByRole("heading", { name: "Sala 1" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Sala 1" })).toBeInTheDocument();
  });

  it("C3 — as ações trazem rótulo em texto, não só ícone", () => {
    render(<FilmeCliente filme={filme()} />);

    const salaUm = screen.getByRole("region", { name: "Sala 1" });

    // O nome acessível diz de qual sala é a ação: numa página com dois cartões,
    // "Assentos" sozinho não distingue.
    expect(within(salaUm).getByRole("button", { name: /^Assentos/ })).toBeInTheDocument();
    expect(within(salaUm).getByRole("button", { name: /^Preços/ })).toBeInTheDocument();
    // E o texto está visível, não só no rótulo acessível.
    expect(within(salaUm).getByText("Assentos")).toBeInTheDocument();
    expect(within(salaUm).getByText("Preços")).toBeInTheDocument();
  });

  it("C6 — horário esgotado se distingue por palavra, não por cor", () => {
    const comEsgotada = filme({
      screenings: [
        sessao({
          id: 10,
          starts_at: "2026-08-12T19:00:00-03:00",
          room_name: "Sala 1",
          has_available_seats: false,
        }),
      ],
    });
    render(<FilmeCliente filme={comEsgotada} />);

    expect(screen.getByText("Esgotada")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Escolher lugares —/ })).not.toBeInTheDocument();
  });

  it("C7 — o preço NÃO aparece no horário: ele mora no painel de Preços", () => {
    // Decisão do autor durante a 014, depois de ver a grade montada: repetir
    // em doze chips o que a ação "Preços" mostra transforma a grade num mural
    // de números. O alvo do horário é sobre HORÁRIO.
    render(<FilmeCliente filme={filme()} />);

    expect(screen.queryByText("R$ 32,00")).not.toBeInTheDocument();
    expect(screen.queryByText("R$ 45,00")).not.toBeInTheDocument();
  });

  it("C4 — as ações do topo operam sobre o primeiro horário disponível do cartão", () => {
    const primeiroEsgotado = filme({
      screenings: [
        sessao({
          id: 10,
          starts_at: "2026-08-12T19:00:00-03:00",
          room_name: "Sala 1",
          has_available_seats: false,
        }),
        sessao({ id: 11, starts_at: "2026-08-12T21:00:00-03:00", room_name: "Sala 1" }),
      ],
    });
    render(<FilmeCliente filme={primeiroEsgotado} />);

    // 21:00 é o primeiro DISPONÍVEL, embora 19:00 venha antes na grade.
    expect(screen.getByRole("button", { name: /^Assentos.*21:00/ })).toBeInTheDocument();
  });

  it("rótulos acessíveis usam o fuso de São Paulo, não o do processo", () => {
    // 18:30Z é 15:30 em São Paulo. Sem timeZone fixo, o SSR (UTC) e o
    // cliente (UTC-3) hidratam aria-label diferentes — o erro de hidratação
    // que apareceu no cartão.
    render(
      <FilmeCliente
        filme={filme({
          screenings: [
            sessao({ id: 10, starts_at: "2026-08-13T18:30:00.000Z", room_name: "Sala 2" }),
          ],
        })}
      />,
    );

    expect(screen.getByRole("button", { name: /Assentos — Sala 2,.*15:30/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Preços — Sala 2,.*15:30/ })).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Escolher lugares — .*15:30, Sala 2/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("15:30")).toBeInTheDocument();
  });
});
