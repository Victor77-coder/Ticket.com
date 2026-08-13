import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { Ingresso as IngressoTipo } from "@/lib/types";

/**
 * A página compartilhada — a única superfície pública que mostra um ingresso.
 *
 * O que estes testes protegem:
 *
 *  - que a página **não vaze** nada além do ingresso. A prova completa é do
 *    back-end (`test_share_link_leakage.py`, requisito da constitution); aqui
 *    a verificação é sobre o que é RENDERIZADO, incluindo o estado
 *    serializado que não aparece na tela — um vazamento cabe num `<script>`;
 *  - que a página **não convide a entrar**. Ela é pública, e um botão de
 *    entrada ali sugeriria que falta conta para ver o ingresso (FR-036);
 *  - que o link revogado tenha **frase própria**, e não a 404 genérica do
 *    site: quem recebeu o ingresso de um amigo concluiria que o site quebrou;
 *  - que `noindex` e `no-referrer` estejam declarados. O endereço É a
 *    credencial.
 */

const buscar = vi.fn();
vi.mock("@/lib/api", () => ({
  fetchIngressoCompartilhado: (...args: unknown[]) => buscar(...args),
}));

const modulo = await import("@/app/ingresso/[token]/page");
const { default: PaginaPublica, metadata } = modulo;

const INGRESSO: IngressoTipo = {
  codigo: "codigo-assinado-abc",
  qr_svg: "data:image/svg+xml;base64,PHN2Zy8+",
  filme: "A Odisseia",
  sessao: new Date("2026-08-20T19:30:00Z").toISOString(),
  sala: "Sala 3",
  assento: { fileira: "F", numero: 12 },
  tipo: "inteira" as const,
};

async function renderizar(resultado: unknown) {
  buscar.mockResolvedValue(resultado);
  const { container } = render(
    await PaginaPublica({ params: Promise.resolve({ token: "um-token-qualquer" }) }),
  );
  return container;
}

describe("página compartilhada", () => {
  it("mostra filme, sessão, sala, lugar e o QR", async () => {
    await renderizar({ ok: true, data: INGRESSO, status: 200 });

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText(/Sala 3/)).toBeInTheDocument();
    expect(screen.getByText("F12")).toBeInTheDocument();
    expect(screen.getByRole("img")).toBeInTheDocument();
    expect(screen.getByText("codigo-assinado-abc")).toBeInTheDocument();
  });

  it("não convida a entrar nem leva a nenhuma conta", async () => {
    await renderizar({ ok: true, data: INGRESSO, status: 200 });

    expect(screen.queryByText(/entrar/i)).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /conta|entrar|meus ingressos/i })).toBeNull();
  });

  it("não renderiza nenhum campo proibido, nem no estado serializado", async () => {
    // A prova completa é do back-end. Esta é a segunda linha: se um dia a
    // página passar a receber mais do que o ingresso, quebra aqui.
    //
    // A inspeção é sobre TEXTO VISÍVEL e ESTADO SERIALIZADO — os dois lugares
    // por onde um dado sai da página. Deliberadamente NÃO sobre o HTML cru:
    // nome de classe CSS não é dado, e incluí-lo transformaria `.cartao` num
    // falso positivo de "dado de cartão". (Aconteceu na primeira versão deste
    // teste. Um teste que falha por nome de classe é um teste que alguém
    // enfraquece na terceira vez.)
    const container = await renderizar({ ok: true, data: INGRESSO, status: 200 });

    const texto = container.textContent ?? "";
    const estado = Array.from(container.querySelectorAll("script"))
      .map((s) => s.textContent ?? "")
      .join(" ");
    const superficie = `${texto} ${estado}`.toLowerCase();

    const proibidos = [
      "comprador",
      "cliente1",
      "@", // qualquer e-mail
      "cartão",
      "bandeira",
      "r$",
      "valor",
      "expira",
      "reserva",
      "pagamento",
    ];

    for (const proibido of proibidos) {
      expect(superficie).not.toContain(proibido);
    }
  });

  it("link revogado tem frase própria, não a 404 genérica", async () => {
    await renderizar({ ok: false, status: 404, error: "Este link não vale mais." });

    expect(screen.getByText(/não vale mais/i)).toBeInTheDocument();
    expect(screen.getByText(/peça um novo/i)).toBeInTheDocument();
    // E nenhum vestígio do ingresso.
    expect(screen.queryByText("A Odisseia")).not.toBeInTheDocument();
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });

  it("distingue link morto de servidor fora do ar", async () => {
    // As duas telas dizem coisas diferentes porque a próxima ação é
    // diferente: pedir outro link, ou tentar de novo em instantes.
    await renderizar({ ok: false, status: 502, error: "Erro" });

    expect(screen.getByText(/não conseguimos abrir/i)).toBeInTheDocument();
    expect(screen.getByText(/atualizar a página/i)).toBeInTheDocument();
  });

  it("declara noindex e no-referrer", () => {
    // O endereço É a credencial: indexado, passa a ser encontrável por quem
    // nunca o recebeu, e o `Referer` o entregaria a qualquer destino.
    expect(metadata.robots).toEqual({ index: false, follow: false });
    expect(metadata.referrer).toBe("no-referrer");
  });
});
