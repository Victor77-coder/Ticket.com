import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PainelDeLink from "@/components/tickets/PainelDeLink";

/**
 * O painel de compartilhamento.
 *
 * O que estes testes protegem:
 *
 *  - que as três ações sejam alcançáveis e acionáveis **só pelo teclado**
 *    (FR-055) e que o resultado de cada uma seja **anunciado** a tecnologias
 *    assistivas (FR-054). Uma ação que muda uma credencial em silêncio é
 *    inacessível de um jeito que ninguém percebe olhando a tela;
 *  - que o texto diga que o link **mostra o código de entrada**. Compartilhar
 *    aqui é entregar o direito de entrar, e uma interface que chama isso de
 *    "compartilhar" e para por aí mente sobre o que a ação faz;
 *  - que o endereço continue **selecionável em texto**: se a área de
 *    transferência for negada, é o que resta.
 */

const chamadas: { metodo: string; corpo: unknown }[] = [];

beforeEach(() => {
  chamadas.length = 0;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (_url: string, init: RequestInit) => {
      chamadas.push({ metodo: init.method ?? "GET", corpo: JSON.parse(String(init.body)) });
      const gerou = init.method === "POST";
      return {
        ok: true,
        status: gerou ? 201 : 200,
        json: async () =>
          gerou
            ? { ativo: true, endereco: "http://localhost:5003/ingresso/token-novo" }
            : { ativo: false, endereco: null },
      };
    }),
  );
});

const SEM_LINK = { ativo: false, endereco: null };
const COM_LINK = { ativo: true, endereco: "http://localhost:5003/ingresso/token-antigo" };

describe("painel de link", () => {
  it("diz que o link mostra o código de entrada, antes de gerar", () => {
    render(<PainelDeLink ingressoId="abc" inicial={SEM_LINK} />);

    expect(screen.getByText(/mostra o código de entrada/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Gerar link" })).toBeInTheDocument();
  });

  it("com link ativo, avisa que quem abrir pode entrar e oferece as duas ações", () => {
    render(<PainelDeLink ingressoId="abc" inicial={COM_LINK} />);

    expect(screen.getByText(/pode usá-lo para entrar/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar link" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Revogar link" })).toBeInTheDocument();
    // Selecionável em texto: é o que resta se copiar for negado.
    expect(screen.getByText(COM_LINK.endereco)).toBeInTheDocument();
  });

  it("gera o link apenas pelo teclado e anuncia o resultado", async () => {
    const usuario = userEvent.setup();
    render(<PainelDeLink ingressoId="abc" inicial={SEM_LINK} />);

    await usuario.tab();
    expect(screen.getByRole("button", { name: "Gerar link" })).toHaveFocus();

    await usuario.keyboard("{Enter}");

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(/Link gerado/),
    );
    expect(chamadas).toEqual([{ metodo: "POST", corpo: { ingresso: "abc" } }]);
    expect(screen.getByText(/token-novo/)).toBeInTheDocument();
  });

  it("revoga apenas pelo teclado e anuncia o resultado", async () => {
    const usuario = userEvent.setup();
    render(<PainelDeLink ingressoId="abc" inicial={COM_LINK} />);

    // Copiar, depois Revogar: as duas são alcançáveis por tabulação.
    await usuario.tab();
    await usuario.tab();
    expect(screen.getByRole("button", { name: "Revogar link" })).toHaveFocus();

    await usuario.keyboard("{Enter}");

    await waitFor(() =>
      expect(screen.getByRole("status")).toHaveTextContent(/Link revogado/),
    );
    expect(chamadas).toEqual([{ metodo: "DELETE", corpo: { ingresso: "abc" } }]);
    // E volta ao estado de "sem link", oferecendo gerar outro.
    expect(screen.getByRole("button", { name: "Gerar link" })).toBeInTheDocument();
  });

  it("o aviso é uma região viva, para o resultado não passar em silêncio", () => {
    render(<PainelDeLink ingressoId="abc" inicial={SEM_LINK} />);

    expect(screen.getByRole("status")).toHaveAttribute("aria-live", "polite");
  });

  it("mostra a frase do servidor quando a recusa vem de lá", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 403,
        json: async () => ({ detail: "Apenas clientes têm ingressos." }),
      })),
    );
    const usuario = userEvent.setup();
    render(<PainelDeLink ingressoId="abc" inicial={SEM_LINK} />);

    await usuario.click(screen.getByRole("button", { name: "Gerar link" }));

    // A frase vem do Django, já em pt-BR. Traduzir de novo aqui faria a mesma
    // regra existir em dois lugares.
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Apenas clientes têm ingressos."),
    );
  });
});
