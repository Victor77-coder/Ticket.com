import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import PagamentoCliente from "@/app/pagamento/[id]/PagamentoCliente";
import type { Ingresso, Reserva } from "@/lib/types";

/**
 * A tela de pagamento e seus estados.
 *
 * O que estes testes protegem, além do óbvio: que a tela **não decide** o
 * desfecho da cobrança. Toda asserção de aprovação ou recusa parte de uma
 * resposta do servidor — se algum dia a regra do cartão for reproduzida no
 * navegador, estes testes continuam passando e é justamente aí que a
 * autorização deixa de valer. Por isso há um teste explícito de que o número
 * digitado não muda o desfecho.
 */

const QR = "data:image/svg+xml;base64,PHN2Zy8+";

function criarReserva(sobrescreve: Partial<Reserva> = {}): Reserva {
  return {
    id: 77,
    sessao: 12,
    assentos: [
      { fileira: "A", numero: 1 },
      { fileira: "A", numero: 2 },
    ],
    total: "64.00",
    expira_em: new Date(Date.now() + 9 * 60 * 1000).toISOString(),
    situacao: "reservada",
    ...sobrescreve,
  };
}

function criarIngresso(lugar: string, numero: number): Ingresso {
  return {
    codigo: `codigo-assinado-${lugar}`,
    qr_svg: QR,
    filme: "A Odisseia",
    sessao: new Date("2026-08-20T19:30:00Z").toISOString(),
    sala: "Sala 1",
    assento: { fileira: lugar, numero },
    tipo: "inteira" as const,
  };
}

function renderizar(reserva = criarReserva()) {
  return render(
    <PagamentoCliente
      reserva={reserva}
      filme="A Odisseia"
      sala="Sala 1"
      inicio={new Date("2026-08-20T19:30:00Z").toISOString()}
    />,
  );
}

async function preencherEPagar() {
  const usuario = userEvent.setup();
  await usuario.type(screen.getByLabelText(/número do cartão/i), "4242424242424242");
  await usuario.type(screen.getByLabelText(/nome impresso/i), "MARIA DE SOUZA");
  await usuario.type(screen.getByLabelText(/validade/i), "122030");
  await usuario.type(screen.getByLabelText(/código de segurança/i), "123");
  await usuario.click(screen.getByRole("button", { name: /pagar/i }));
  return usuario;
}

function responder(status: number, corpo: unknown) {
  return vi.fn().mockResolvedValue({
    status,
    json: async () => corpo,
  } as Response);
}

beforeEach(() => {
  vi.stubGlobal("fetch", responder(201, {}));
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("revisão antes de pagar", () => {
  it("mostra filme, sala, lugares e total vindos do servidor", () => {
    renderizar();

    expect(screen.getByText("A Odisseia")).toBeInTheDocument();
    expect(screen.getByText("Sala 1")).toBeInTheDocument();
    expect(screen.getByText("A1, A2")).toBeInTheDocument();
    expect(screen.getAllByText(/R\$\s*64,00/).length).toBeGreaterThan(0);
  });

  it("exibe o prazo restante da reserva", () => {
    renderizar();

    expect(screen.getByRole("timer")).toHaveTextContent(/para concluir o pagamento/i);
  });

  it("avisa que a cobrança é simulada", () => {
    renderizar();

    expect(screen.getByText(/cobrança simulada/i)).toBeInTheDocument();
  });
});

describe("aprovação", () => {
  it("exibe um ingresso por lugar, cada um com QR e código em texto", async () => {
    vi.stubGlobal(
      "fetch",
      responder(201, {
        situacao: "paga",
        pagamento: { cartao_final: "4242", bandeira: "visa", total: "64.00", pago_em: "" },
        ingressos: [criarIngresso("A", 1), criarIngresso("B", 2)],
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByText(/seus 2 ingressos/i)).toBeInTheDocument();
    });

    const imagens = screen.getAllByRole("img");
    expect(imagens).toHaveLength(2);
    // FR-038: o código em texto acompanha o QR — é o que a portaria digita.
    expect(screen.getByText("codigo-assinado-A")).toBeInTheDocument();
    expect(screen.getByText("codigo-assinado-B")).toBeInTheDocument();

    const itens = screen.getAllByRole("listitem");
    expect(itens).toHaveLength(2);
    for (const item of itens) {
      expect(item).toHaveAttribute("data-variante", "objeto");
    }
  });

  it("anuncia o resultado a quem não está olhando para a tela", async () => {
    vi.stubGlobal(
      "fetch",
      responder(201, {
        situacao: "paga",
        pagamento: { cartao_final: "4242", bandeira: "visa", total: "32.00", pago_em: "" },
        ingressos: [criarIngresso("A", 1)],
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/aprovado/i);
    });
  });

  it("some com a contagem regressiva depois de pagar", async () => {
    vi.stubGlobal(
      "fetch",
      responder(201, {
        situacao: "paga",
        pagamento: { cartao_final: "4242", bandeira: "visa", total: "32.00", pago_em: "" },
        ingressos: [criarIngresso("A", 1)],
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.queryByRole("timer")).not.toBeInTheDocument();
    });
  });

  it("já abre nos ingressos quando a reserva chega paga", () => {
    renderizar(
      criarReserva({
        situacao: "paga",
        pagamento: { cartao_final: "4242", bandeira: "visa", total: "64.00", pago_em: "" },
        ingressos: [criarIngresso("A", 1)],
      }),
    );

    // R13: voltar ao endereço de uma reserva paga leva aos ingressos, nunca a
    // um formulário inútil.
    expect(screen.getByText(/seu ingresso/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/número do cartão/i)).not.toBeInTheDocument();
  });
});

describe("recusa", () => {
  it("mostra a frase do servidor, em português, e mantém o formulário", async () => {
    vi.stubGlobal(
      "fetch",
      responder(402, {
        situacao: "recusada",
        motivo: "saldo_insuficiente",
        detail: "Não havia saldo suficiente neste cartão. Tente outro cartão.",
        expira_em: new Date(Date.now() + 9 * 60 * 1000).toISOString(),
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/saldo suficiente/i);
    });
    // A pessoa precisa poder tentar outro cartão sem sair da tela (FR-028).
    expect(screen.getByLabelText(/número do cartão/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /pagar/i })).toBeEnabled();
  });

  it("mantém a contagem correndo — a recusa não mexe no prazo", async () => {
    vi.stubGlobal(
      "fetch",
      responder(402, {
        situacao: "recusada",
        motivo: "cartao_expirado",
        detail: "Este cartão está expirado. Use um cartão com validade em dia.",
        expira_em: new Date(Date.now() + 9 * 60 * 1000).toISOString(),
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.getByRole("timer")).toBeInTheDocument();
  });

  it("distingue erro de preenchimento de recusa de cobrança", async () => {
    vi.stubGlobal("fetch", responder(400, { detail: "Confira o número do cartão." }));
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/confira o número/i);
    });
    // FR-010: a caixa de preenchimento não usa a palavra "recusado", porque
    // a ação da pessoa é outra — corrigir, não trocar de cartão.
    expect(screen.getByRole("alert")).not.toHaveTextContent(/recusado/i);
  });

  it("não decide o desfecho pelo número digitado", async () => {
    // O mesmo cartão que o servidor aprova em outro teste, aqui recusado. Se
    // a tela tivesse a tabela de cartões, este teste falharia — e é esse o
    // ponto: a autorização é do servidor, sempre (FR-042).
    vi.stubGlobal(
      "fetch",
      responder(402, {
        situacao: "recusada",
        motivo: "recusado_pelo_emissor",
        detail: "O banco emissor recusou a cobrança. Tente outro cartão ou fale com o banco.",
        expira_em: new Date(Date.now() + 9 * 60 * 1000).toISOString(),
      }),
    );
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/banco emissor/i);
    });
  });

  it("nenhum estado exibe texto genérico de erro", async () => {
    vi.stubGlobal("fetch", responder(400, { detail: "Confira os dados do cartão." }));
    renderizar();

    await preencherEPagar();

    await waitFor(() => {
      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
    expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^erro$/i)).not.toBeInTheDocument();
  });
});

describe("prazo vencido na tela", () => {
  it("troca o formulário por explicação e caminho de volta", () => {
    renderizar(criarReserva({ expira_em: new Date(Date.now() - 1000).toISOString() }));

    expect(screen.getByRole("alert")).toHaveTextContent(/prazo desta reserva terminou/i);
    expect(screen.queryByLabelText(/número do cartão/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /escolher lugares de novo/i })).toHaveAttribute(
      "href",
      "/sessoes/12",
    );
  });
});

describe("acessibilidade", () => {
  it("o formulário inteiro é alcançável e submissível só com o teclado", async () => {
    const usuario = userEvent.setup();
    vi.stubGlobal(
      "fetch",
      responder(201, {
        situacao: "paga",
        pagamento: { cartao_final: "4242", bandeira: "visa", total: "64.00", pago_em: "" },
        ingressos: [criarIngresso("A", 1)],
      }),
    );
    renderizar();

    await usuario.tab();
    expect(screen.getByLabelText(/número do cartão/i)).toHaveFocus();
    await usuario.keyboard("4242424242424242");

    await usuario.tab();
    expect(screen.getByLabelText(/nome impresso/i)).toHaveFocus();
    await usuario.keyboard("MARIA");

    await usuario.tab();
    expect(screen.getByLabelText(/validade/i)).toHaveFocus();
    await usuario.keyboard("122030");

    await usuario.tab();
    expect(screen.getByLabelText(/código de segurança/i)).toHaveFocus();
    await usuario.keyboard("123");

    await usuario.tab();
    expect(screen.getByRole("button", { name: /pagar/i })).toHaveFocus();
    await usuario.keyboard("{Enter}");

    await waitFor(() => {
      expect(screen.getByRole("status")).toBeInTheDocument();
    });
  });

  it("todo campo tem rótulo ligado por id, não placeholder no lugar de label", () => {
    renderizar();

    for (const rotulo of [
      /número do cartão/i,
      /nome impresso/i,
      /validade/i,
      /código de segurança/i,
    ]) {
      expect(screen.getByLabelText(rotulo)).toBeInTheDocument();
    }
  });
});
