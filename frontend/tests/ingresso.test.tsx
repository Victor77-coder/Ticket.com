import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Ingresso from "@/components/tickets/Ingresso";
import type { Ingresso as IngressoTipo } from "@/lib/types";

/**
 * O ingresso emitido.
 *
 * O que estes testes protegem: que o CÓDIGO EM TEXTO nunca desapareça em favor
 * do QR. A constitution exige que a digitação manual seja alternativa "sempre
 * disponível" na portaria, e é fácil alguém decidir que o texto polui a tela —
 * o teste é o que impede essa remoção de passar como melhoria visual.
 */

const CODIGO =
  "eyJ0IjoiM2Y5YTFlMmMtN2IwNC00YzhkLTlmMjEtNWE2YjhjMGQxZTJmIiwicyI6MTJ9:1uJd3P:AbCdEf";

function criarIngresso(sobrescreve: Partial<IngressoTipo> = {}): IngressoTipo {
  return {
    codigo: CODIGO,
    qr_svg: "data:image/svg+xml;base64,PHN2Zy8+",
    filme: "A Odisseia",
    sessao: new Date("2026-08-20T19:30:00Z").toISOString(),
    sala: "Sala 1",
    assento: { fileira: "A", numero: 3 },
    ...sobrescreve,
  };
}

describe("um ingresso", () => {
  it("mostra filme, sala e o lugar daquele ingresso", () => {
    render(<Ingresso ingresso={criarIngresso()} indice={1} total={1} />);

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText(/Sala 1/)).toBeInTheDocument();
    expect(screen.getByText("A3")).toBeInTheDocument();
  });

  it("mostra o QR como imagem com texto alternativo", () => {
    render(<Ingresso ingresso={criarIngresso()} indice={1} total={1} />);

    const imagem = screen.getByRole("img");
    expect(imagem).toHaveAttribute("src", expect.stringContaining("data:image/svg+xml"));
    // O `alt` nomeia o lugar: quem usa leitor de tela precisa saber qual dos
    // ingressos está lendo.
    expect(imagem).toHaveAccessibleName(/lugar A3/i);
  });

  it("mostra o código em texto, INTEIRO, junto do QR", () => {
    render(<Ingresso ingresso={criarIngresso()} indice={1} total={1} />);

    // FR-038: é o que a portaria digita quando a câmera falha ou é negada.
    // Truncar com reticências tornaria o texto inútil para digitar.
    expect(screen.getByText(CODIGO)).toBeInTheDocument();
    expect(screen.queryByText(/…|\.\.\./)).not.toBeInTheDocument();
  });

  it("anuncia a posição na lista", () => {
    render(<Ingresso ingresso={criarIngresso()} indice={2} total={3} />);

    expect(screen.getByText(/ingresso 2 de 3/i)).toBeInTheDocument();
  });
});

describe("uma reserva de três lugares", () => {
  it("rende três ingressos, cada um com seu lugar e seu código", () => {
    const lugares: [string, number][] = [
      ["A", 1],
      ["A", 2],
      ["A", 3],
    ];

    render(
      <ul>
        {lugares.map(([fileira, numero], i) => (
          <Ingresso
            key={numero}
            ingresso={criarIngresso({
              codigo: `${CODIGO}-${numero}`,
              assento: { fileira, numero },
            })}
            indice={i + 1}
            total={3}
          />
        ))}
      </ul>,
    );

    // FR-014: um ingresso por LUGAR, não um por reserva.
    const itens = screen.getAllByRole("listitem");
    expect(itens).toHaveLength(3);

    for (const [indice, [fileira, numero]] of lugares.entries()) {
      const item = itens[indice];
      expect(within(item).getByText(`${fileira}${numero}`)).toBeInTheDocument();
      expect(within(item).getByText(`${CODIGO}-${numero}`)).toBeInTheDocument();
    }

    // Três QR distintos, um por ingresso.
    expect(screen.getAllByRole("img")).toHaveLength(3);
  });

  it("os códigos exibidos são diferentes entre si", () => {
    const codigos = [`${CODIGO}-1`, `${CODIGO}-2`];

    render(
      <ul>
        {codigos.map((codigo, i) => (
          <Ingresso
            key={codigo}
            ingresso={criarIngresso({ codigo, assento: { fileira: "A", numero: i + 1 } })}
            indice={i + 1}
            total={2}
          />
        ))}
      </ul>,
    );

    for (const codigo of codigos) {
      expect(screen.getByText(codigo)).toBeInTheDocument();
    }
  });

  // --- A alteração da 009: `indice` e `total` viraram opcionais ------------

  it("sem indice e total, continua completo e não anuncia posição", () => {
    // O mesmo cartão serve à página compartilhada, onde há UM ingresso e não
    // existe "1 de 1" para anunciar. A alteração é aditiva: tudo o que o
    // cartão mostrava continua aqui.
    render(
      <ul>
        <Ingresso ingresso={criarIngresso()} />
      </ul>,
    );

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText(/Sala 1/)).toBeInTheDocument();
    expect(screen.getByText("A3")).toBeInTheDocument();
    expect(screen.getByRole("img")).toBeInTheDocument();
    expect(screen.getByText(CODIGO)).toBeInTheDocument();

    expect(screen.queryByText(/Ingresso \d+ de \d+/)).not.toBeInTheDocument();
  });

  it("sem prop, a variante é o cartão da 009", () => {
    render(
      <ul>
        <Ingresso ingresso={criarIngresso()} />
      </ul>,
    );

    expect(screen.getByRole("listitem")).toHaveAttribute("data-variante", "cartao");
    expect(screen.getByText(CODIGO)).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAttribute("src", expect.stringContaining("data:image"));
  });

  it("variante objeto destaca o lugar e mantém QR e código", () => {
    render(
      <ul>
        <Ingresso ingresso={criarIngresso()} variante="objeto" />
      </ul>,
    );

    const item = screen.getByRole("listitem");
    expect(item).toHaveAttribute("data-variante", "objeto");
    expect(within(item).getAllByText("A3").length).toBeGreaterThanOrEqual(1);
    expect(within(item).getByText(CODIGO)).toBeInTheDocument();
    expect(within(item).getByRole("img")).toBeInTheDocument();
  });
});
