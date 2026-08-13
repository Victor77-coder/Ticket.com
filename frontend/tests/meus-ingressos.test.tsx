import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ListaDeIngressos, MeuIngresso } from "@/lib/types";

/**
 * A área "Meus ingressos".
 *
 * O que estes testes protegem:
 *
 *  - que a tela **não reordene** o que o servidor mandou. A fronteira entre
 *    futuro e passado é decisão do servidor, com o relógio do banco (FR-010);
 *    recomparar datas aqui reintroduziria o relógio do navegador;
 *  - que o ingresso de sessão **cancelada** apareça com aviso, em vez de
 *    sumir ou de se passar por um ingresso comum (FR-011);
 *  - que o estado vazio seja para quem **não tem ingresso nenhum**, e não
 *    para quem só tem ingressos passados (FR-013). É o contra-teste que pega
 *    a condição olhando só o grupo dos futuros.
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
  fetchMeusIngressos: (...args: unknown[]) => buscar(...args),
}));

const { default: MeusIngressosPage } = await import("@/app/meus-ingressos/page");

function criarIngresso(sobrescreve: Partial<MeuIngresso> = {}): MeuIngresso {
  return {
    id: "3f9a1c22-8e4b-4d51-9a77-2c5f0b1e9d33",
    grupo: "futuro",
    sessao_cancelada: false,
    codigo: "codigo-assinado-abc",
    qr_svg: "data:image/svg+xml;base64,PHN2Zy8+",
    filme: "A Odisseia",
    sessao: new Date("2026-08-20T19:30:00Z").toISOString(),
    sala: "Sala 1",
    assento: { fileira: "A", numero: 3 },
    tipo: "inteira" as const,
    ...sobrescreve,
  };
}

async function renderizar(lista: ListaDeIngressos) {
  buscar.mockResolvedValue({ ok: true, data: lista, status: 200 });
  render(await MeusIngressosPage());
}

describe("meus ingressos", () => {
  it("mostra um item por ingresso, com filme, sala e lugar", async () => {
    await renderizar({
      futuros: [
        criarIngresso({ id: "a", assento: { fileira: "F", numero: 11 } }),
        criarIngresso({ id: "b", assento: { fileira: "F", numero: 12 } }),
      ],
      passados: [],
    });

    expect(screen.getAllByText("A Odisseia")).toHaveLength(2);
    expect(screen.getByText("F11")).toBeInTheDocument();
    expect(screen.getByText("F12")).toBeInTheDocument();
  });

  it("preserva a ordem que o servidor mandou, sem recomparar datas", async () => {
    await renderizar({
      futuros: [
        criarIngresso({ id: "a", filme: "Primeira sessão" }),
        criarIngresso({ id: "b", filme: "Segunda sessão" }),
      ],
      passados: [criarIngresso({ id: "c", filme: "Já aconteceu", grupo: "passado" })],
    });

    const titulos = screen.getAllByRole("heading", { level: 3 }).map((h) => h.textContent);
    expect(titulos).toEqual(["Primeira sessão", "Segunda sessão", "Já aconteceu"]);
  });

  it("separa os grupos com título próprio, não só com cor", async () => {
    await renderizar({
      futuros: [criarIngresso({ id: "a" })],
      passados: [criarIngresso({ id: "b", grupo: "passado" })],
    });

    expect(screen.getByRole("heading", { name: "Próximas sessões" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Já aconteceram" })).toBeInTheDocument();
  });

  it("cada ingresso mostra seu próprio QR e seu próprio código", async () => {
    await renderizar({
      futuros: [
        criarIngresso({ id: "a", codigo: "codigo-um" }),
        criarIngresso({ id: "b", codigo: "codigo-dois" }),
      ],
      passados: [],
    });

    expect(screen.getAllByRole("img")).toHaveLength(2);
    expect(screen.getByText("codigo-um")).toBeInTheDocument();
    expect(screen.getByText("codigo-dois")).toBeInTheDocument();
  });

  it("avisa quando a sessão do ingresso foi cancelada, sem escondê-lo", async () => {
    await renderizar({
      futuros: [criarIngresso({ id: "a", filme: "Cancelado", sessao_cancelada: true })],
      passados: [],
    });

    expect(screen.getByText("Cancelado")).toBeInTheDocument();
    expect(screen.getByText(/sessão foi cancelada/i)).toBeInTheDocument();
  });

  it("cada ingresso leva ao seu próprio endereço", async () => {
    await renderizar({ futuros: [criarIngresso({ id: "abc-123" })], passados: [] });

    const link = screen.getByRole("link", { name: /Abrir e compartilhar/ });
    expect(link).toHaveAttribute("href", "/meus-ingressos/abc-123");
  });

  it("quem não tem ingresso nenhum lê uma frase e alcança o catálogo", async () => {
    await renderizar({ futuros: [], passados: [] });

    expect(screen.getByText(/ainda não tem ingressos/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /filmes em cartaz/i })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("quem só tem ingressos passados NÃO vê o estado vazio", async () => {
    // O contra-teste que pega a condição olhando só o grupo dos futuros.
    await renderizar({
      futuros: [],
      passados: [criarIngresso({ id: "a", grupo: "passado", filme: "Cidade de Deus" })],
    });

    expect(screen.queryByText(/ainda não tem ingressos/i)).not.toBeInTheDocument();
    expect(screen.getByText("Cidade de Deus")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Já aconteceram" })).toBeInTheDocument();
  });

  it("papel sem ingressos recebe explicação, e não é mandado para a entrada", async () => {
    // Entrar de novo não muda o papel: conduzir à entrada seria caminho sem
    // saída (FR-051).
    buscar.mockResolvedValue({ ok: false, status: 403, error: "Apenas clientes têm ingressos." });

    render(await MeusIngressosPage());

    expect(screen.getByText(/área é de quem compra/i)).toBeInTheDocument();
    expect(redirecionou).not.toHaveBeenCalled();
  });
});
