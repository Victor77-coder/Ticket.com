import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Desfecho from "@/components/gate/Desfecho";
import type { Desfecho as DesfechoTipo } from "@/lib/types";

/**
 * Os quatro desfechos da portaria.
 *
 * O que estes testes protegem:
 *
 *  - que os quatro sejam distinguíveis **sem depender de cor** (FR-017). O
 *    Princípio V proíbe cor como sinal único, e aqui a consequência é séria:
 *    quem não distingue verde de vermelho decidiria quem entra pelo tom da
 *    tela;
 *  - que a apresentação venha do campo `situacao`, e **não** da frase — que é
 *    apresentação e muda numa revisão de redação;
 *  - que **já utilizado** informe QUANDO e **sessão errada** informe QUAL
 *    sessão: sem esses dois dados o operador nega sem saber o que dizer à
 *    pessoa;
 *  - que **inválido** não traga detalhe nenhum.
 */

const INGRESSO = {
  filme: "A Odisseia",
  sessao: new Date("2026-08-12T21:30:00Z").toISOString(),
  sala: "Sala 3",
  assento: { fileira: "F", numero: 12 },
  tipo: "inteira" as const,
};

function criar(sobrescreve: Partial<DesfechoTipo>): DesfechoTipo {
  return { situacao: "valido", detail: "…", ...sobrescreve } as DesfechoTipo;
}

describe("desfecho da portaria", () => {
  it("válido mostra o lugar a que a pessoa deve ir", () => {
    render(
      <Desfecho
        desfecho={criar({
          situacao: "valido",
          detail: "Pode entrar. Sala 3, lugar F12.",
          ingresso: INGRESSO,
        })}
      />,
    );

    expect(screen.getByRole("heading", { name: "Pode entrar" })).toBeInTheDocument();
    expect(screen.getByText("F12")).toBeInTheDocument();
    expect(screen.getByText("Sala 3")).toBeInTheDocument();
  });

  it("já utilizado informa quando o ingresso foi usado", () => {
    render(
      <Desfecho
        desfecho={criar({
          situacao: "ja_utilizado",
          detail: "Este ingresso já foi usado às 21:14. Não libere a entrada.",
          ingresso: INGRESSO,
          utilizado_em: new Date("2026-08-12T21:14:00Z").toISOString(),
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: /já foi usado/i }),
    ).toBeInTheDocument();
    expect(screen.getByText("Usado às")).toBeInTheDocument();
  });

  it("sessão errada informa a qual sessão o ingresso pertence", () => {
    render(
      <Desfecho
        desfecho={criar({
          situacao: "sessao_errada",
          detail: "Este ingresso é da sessão das 19:00, Sala 1. Não é esta porta.",
          sessao_do_ingresso: {
            filme: "Cidade de Deus",
            inicio: new Date("2026-08-12T19:00:00Z").toISOString(),
            sala: "Sala 1",
            cancelada: false,
          },
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Ingresso de outra sessão" }),
    ).toBeInTheDocument();
    expect(screen.getByText("Cidade de Deus")).toBeInTheDocument();
    expect(screen.getByText("Sala 1")).toBeInTheDocument();
  });

  it("inválido não traz detalhe nenhum do ingresso", () => {
    // Qualquer detalhe a mais entregaria a quem tenta adivinhar a informação
    // que o desfecho existe para negar.
    render(
      <Desfecho
        desfecho={criar({
          situacao: "invalido",
          detail: "Ingresso não reconhecido. Não libere a entrada.",
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Ingresso não reconhecido" }),
    ).toBeInTheDocument();
    expect(screen.queryByText("Lugar")).not.toBeInTheDocument();
    expect(screen.queryByText("Este ingresso é de")).not.toBeInTheDocument();
  });

  it("os quatro têm título próprio — a distinção não depende de cor", () => {
    const titulos = (
      ["valido", "invalido", "ja_utilizado", "sessao_errada"] as const
    ).map((situacao) => {
      const { unmount } = render(<Desfecho desfecho={criar({ situacao })} />);
      const titulo = screen.getByRole("heading").textContent;
      unmount();
      return titulo;
    });

    expect(new Set(titulos).size).toBe(4);
  });

  it("já utilizado e inválido são distinguíveis sem ler o texto inteiro", () => {
    // São situações diferentes e exigem reações diferentes do operador: uma é
    // "esta pessoa já entrou", a outra é "isto não é um ingresso nosso".
    const { unmount } = render(
      <Desfecho desfecho={criar({ situacao: "ja_utilizado" })} />,
    );
    const usado = screen.getByRole("heading").textContent;
    unmount();

    render(<Desfecho desfecho={criar({ situacao: "invalido" })} />);
    const invalido = screen.getByRole("heading").textContent;

    expect(usado).not.toBe(invalido);
  });

  it("anuncia o desfecho a tecnologias assistivas", () => {
    render(<Desfecho desfecho={criar({ situacao: "valido", ingresso: INGRESSO })} />);

    const regiao = screen.getByRole("status");
    expect(regiao).toHaveAttribute("aria-live", "assertive");
  });
});
