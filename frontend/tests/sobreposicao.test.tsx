import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { describe, expect, it } from "vitest";

import Sobreposicao from "@/components/sessao/Sobreposicao";

/**
 * As regras M1–M6 de contracts/paineis-do-cartao.md.
 *
 * M3 e M4 são a razão de este componente existir. `<dialog>` nativo já entrega
 * `Esc` e foco preso; a DEVOLUÇÃO DE FOCO é o que quase sempre falta, e é a
 * falha invisível para quem usa mouse — a pessoa fecha o painel e o foco
 * reaparece no topo da página, com a navegação por teclado perdida.
 */

function Anfitriao() {
  const [aberta, setAberta] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setAberta(true)}>
        Assentos
      </button>
      <button type="button">Outro botão da página</button>
      <Sobreposicao
        aberta={aberta}
        titulo="Assentos — Sala 2"
        subtitulo="qua., 13/08, 19:00"
        aoFechar={() => setAberta(false)}
      >
        <button type="button">Escolher lugares</button>
      </Sobreposicao>
    </>
  );
}

describe("Sobreposicao", () => {
  it("M5 — é anunciada como diálogo rotulado pelo título", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    await usuario.click(screen.getByRole("button", { name: "Assentos" }));

    expect(screen.getByRole("dialog", { name: /Assentos — Sala 2/ })).toBeInTheDocument();
  });

  it("M1 — fecha com Esc", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    await usuario.click(screen.getByRole("button", { name: "Assentos" }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await usuario.keyboard("{Escape}");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("M2 — fecha por controle visível com nome acessível", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    await usuario.click(screen.getByRole("button", { name: "Assentos" }));
    await usuario.click(screen.getByRole("button", { name: /fechar/i }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("M3 — o foco entra no painel ao abrir", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    await usuario.click(screen.getByRole("button", { name: "Assentos" }));

    const painel = screen.getByRole("dialog");
    expect(painel.contains(document.activeElement)).toBe(true);
  });

  it("M4 — devolve o foco à ação que a abriu", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    const acao = screen.getByRole("button", { name: "Assentos" });
    await usuario.click(acao);
    await usuario.keyboard("{Escape}");

    expect(document.activeElement).toBe(acao);
  });

  it("o conteúdo passado aparece dentro do painel", async () => {
    const usuario = userEvent.setup();
    render(<Anfitriao />);

    await usuario.click(screen.getByRole("button", { name: "Assentos" }));

    const painel = screen.getByRole("dialog");
    expect(painel).toContainElement(screen.getByRole("button", { name: "Escolher lugares" }));
  });

  it("fechada, não renderiza nada", () => {
    render(<Anfitriao />);

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.queryByText(/Assentos — Sala 2/)).not.toBeInTheDocument();
  });
});
