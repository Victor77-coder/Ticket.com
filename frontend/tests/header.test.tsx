import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { cleanup } from "@testing-library/react";

import { AccountButton } from "@/components/header/AccountButton";
import { SiteHeader } from "@/components/header/SiteHeader";

afterEach(cleanup);

describe("cabeçalho global", () => {
  it("é exposto como a landmark de topo do site", () => {
    render(<SiteHeader />);

    // `banner` é a região que leitores de tela usam para pular ao topo do
    // site (FR-027).
    expect(screen.getByRole("banner")).toBeInTheDocument();
  });

  it("exibe o nome do site", () => {
    render(<SiteHeader />);

    expect(screen.getByRole("banner")).toHaveTextContent("ticket.com");
  });

  it("usa o nome do site como caminho de volta para a home", () => {
    render(<SiteHeader />);

    const marca = screen.getByRole("link", { name: /ticket\.com/i });
    expect(marca).toHaveAttribute("href", "/");
  });

  it("apresenta o nome como texto, não como imagem", () => {
    render(<SiteHeader />);

    // R8: wordmark textual. Uma imagem não escala com o zoom nem é
    // selecionável, e exigiria texto alternativo para dizer o mesmo.
    const marca = screen.getByRole("link", { name: /ticket\.com/i });
    expect(marca.querySelector("img")).toBeNull();
  });
});

/**
 * US3 — o componente existe e está testado, mas ainda NÃO está montado no
 * cabeçalho: a rota de entrada pertence à feature de autenticação (FR-023).
 */
describe("acesso à conta", () => {
  it("anuncia a ação de entrar quando não há sessão", () => {
    render(<AccountButton usuario={null} />);

    const acesso = screen.getByRole("link", { name: /entrar na sua conta/i });
    expect(acesso).toBeInTheDocument();
  });

  it("conduz ao caminho de entrada", () => {
    render(<AccountButton usuario={null} caminhoEntrada="/entrar" />);

    expect(screen.getByRole("link", { name: /entrar na sua conta/i })).toHaveAttribute(
      "href",
      "/entrar",
    );
  });

  it("identifica de quem é a sessão quando autenticado", () => {
    render(<AccountButton usuario={{ nome: "Ana" }} />);

    expect(screen.getByRole("button", { name: /ana/i })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /entrar na sua conta/i })).not.toBeInTheDocument();
  });

  it("diferencia os dois estados por texto, não apenas por cor", () => {
    const { unmount } = render(<AccountButton usuario={null} />);
    const visitante = screen.getByRole("link").textContent;
    unmount();

    render(<AccountButton usuario={{ nome: "Ana" }} />);
    const autenticado = screen.getByRole("button").textContent;

    expect(visitante).not.toEqual(autenticado);
    expect(autenticado).toContain("Ana");
  });

  it("é anunciado por função, não como imagem sem descrição", () => {
    render(<AccountButton usuario={null} />);

    const acesso = screen.getByRole("link", { name: /entrar na sua conta/i });
    // O SVG é decorativo: quem carrega o significado é o nome acessível.
    expect(acesso.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
  });
});

describe("cabeçalho de um papel de tela única", () => {
  it("não oferece a busca do catálogo à portaria", () => {
    // Oferecer e depois recusar é pior do que não oferecer: a busca leva ao
    // catálogo, e a portaria seria devolvida à tela dela.
    render(<SiteHeader sessao={{ nome: "Olívia", papel: "gate" }} />);

    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("a marca leva a portaria à tela dela, não à home", () => {
    render(<SiteHeader sessao={{ nome: "Olívia", papel: "gate" }} />);

    expect(screen.getByRole("link", { name: /ticket\.com/i })).toHaveAttribute(
      "href",
      "/portaria",
    );
  });

  it("o cliente continua com busca e marca apontando para a home", () => {
    render(<SiteHeader sessao={{ nome: "Ana", papel: "customer" }} />);

    expect(screen.getByRole("combobox")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ticket\.com/i })).toHaveAttribute("href", "/");
  });
});

describe("a marca no cabeçalho (feature 011)", () => {
  it("o nome sai na família da marca, não na da interface", () => {
    // `--fonte-marca` tem exatamente um consumidor. Se o nome voltar a usar a
    // família da interface, a marca perde o tratamento que a distingue do
    // texto comum — que é metade do que a 011 entrega.
    render(<SiteHeader />);

    const marca = screen.getByRole("link", { name: /ticket\.com/i });
    expect(marca).toHaveClass(/marca/);
  });

  it("o desenho acompanha o nome", () => {
    const { container } = render(<SiteHeader />);

    const marca = screen.getByRole("link", { name: /ticket\.com/i });
    expect(marca.querySelector("svg")).toBeInTheDocument();
    expect(container).toBeTruthy();
  });
});
