import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AccountMenu } from "@/components/header/AccountMenu";
import { caminhoDeRetornoSeguro } from "@/lib/session";
import { LoginForm } from "@/app/entrar/LoginForm";

const replace = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, refresh, push: vi.fn() }),
}));

beforeEach(() => {
  replace.mockClear();
  refresh.mockClear();
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function mockFetch(resposta: { ok: boolean; status?: number; body?: unknown }) {
  const fn = vi.fn().mockResolvedValue({
    ok: resposta.ok,
    status: resposta.status ?? (resposta.ok ? 200 : 401),
    json: async () => resposta.body ?? {},
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

// --- Destino de retorno (FR-011, R7) --------------------------------------

describe("validação do destino de retorno", () => {
  it.each([
    ["//exemplo.com", "protocolo relativo vira endereço absoluto"],
    ["/\\exemplo.com", "barra invertida é normalizada por alguns navegadores"],
    ["https://exemplo.com", "endereço absoluto explícito"],
    ["http://localhost:5003/x", "mesmo o próprio site, se vier absoluto"],
    ["exemplo.com", "sem barra inicial"],
    ["", "vazio"],
    [null, "ausente"],
  ])("descarta %s — %s", (valor) => {
    expect(caminhoDeRetornoSeguro(valor as string | null)).toBe("/");
  });

  it.each(["/", "/filmes/duna-parte-dois", "/busca?q=matrix", "/filmes/a?b=c#d"])(
    "aceita o caminho interno %s",
    (valor) => {
      expect(caminhoDeRetornoSeguro(valor)).toBe(valor);
    },
  );
});

// --- Tela de entrada ------------------------------------------------------

describe("formulário de entrada", () => {
  it("valida campos vazios antes de chamar o servidor (FR-006)", async () => {
    const usuario = userEvent.setup();
    const fetchMock = mockFetch({ ok: true });
    render(<LoginForm caminhoDeRetorno="/" />);

    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    expect(screen.getByText("Informe o usuário.")).toBeInTheDocument();
    expect(screen.getByText("Informe a senha.")).toBeInTheDocument();
    // Campo faltando não pode gastar uma tentativa do limite.
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("associa o erro ao campo para tecnologias assistivas (FR-028)", async () => {
    const usuario = userEvent.setup();
    mockFetch({ ok: true });
    render(<LoginForm caminhoDeRetorno="/" />);

    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    const campo = screen.getByLabelText("Usuário");
    expect(campo).toHaveAttribute("aria-invalid", "true");
    expect(campo).toHaveAccessibleDescription("Informe o usuário.");
  });

  it("envia as credenciais e volta ao caminho pedido", async () => {
    const usuario = userEvent.setup();
    const fetchMock = mockFetch({ ok: true, body: { user: { nome: "Ana", papel: "customer" } } });
    render(<LoginForm caminhoDeRetorno="/filmes/duna-parte-dois" />);

    await usuario.type(screen.getByLabelText("Usuário"), "cliente1");
    await usuario.type(screen.getByLabelText("Senha"), "desafio2026");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => expect(replace).toHaveBeenCalledWith("/filmes/duna-parte-dois"));
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/entrar",
      expect.objectContaining({ method: "POST" }),
    );
    // Sem o refresh o cabeçalho só mostraria o nome após recarregar.
    expect(refresh).toHaveBeenCalled();
  });

  it("mostra a mensagem do servidor quando a credencial é recusada", async () => {
    const usuario = userEvent.setup();
    mockFetch({ ok: false, status: 401, body: { detail: "Usuário ou senha incorretos." } });
    render(<LoginForm caminhoDeRetorno="/" />);

    await usuario.type(screen.getByLabelText("Usuário"), "cliente1");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Usuário ou senha incorretos.");
    expect(replace).not.toHaveBeenCalled();
  });

  it("preserva o usuário digitado e nunca a senha após a recusa (FR-005)", async () => {
    const usuario = userEvent.setup();
    mockFetch({ ok: false, status: 401, body: { detail: "Usuário ou senha incorretos." } });
    render(<LoginForm caminhoDeRetorno="/" />);

    await usuario.type(screen.getByLabelText("Usuário"), "cliente1");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    await screen.findByRole("alert");
    expect(screen.getByLabelText("Usuário")).toHaveValue("cliente1");
    expect(screen.getByLabelText("Senha")).toHaveValue("");
  });

  it("repassa a mensagem de limite de tentativas", async () => {
    const usuario = userEvent.setup();
    mockFetch({
      ok: false,
      status: 429,
      body: { detail: "Muitas tentativas. Tente novamente em 15 minutos." },
    });
    render(<LoginForm caminhoDeRetorno="/" />);

    await usuario.type(screen.getByLabelText("Usuário"), "cliente1");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Muitas tentativas");
  });

  it("é reconhecível por gerenciadores de senha (FR-030)", () => {
    render(<LoginForm caminhoDeRetorno="/" />);

    expect(screen.getByLabelText("Usuário")).toHaveAttribute("autoComplete", "username");
    expect(screen.getByLabelText("Senha")).toHaveAttribute("autoComplete", "current-password");
  });
});

// --- Menu de conta --------------------------------------------------------

describe("menu de conta", () => {
  it("mostra o convite para entrar quando não há sessão", () => {
    render(<AccountMenu sessao={null} caminhoEntrada="/entrar" />);

    expect(screen.getByRole("link", { name: /entrar na sua conta/i })).toHaveAttribute(
      "href",
      "/entrar",
    );
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("identifica o usuário quando há sessão", () => {
    render(<AccountMenu sessao={{ nome: "Camila Souza", papel: "customer" }} caminhoEntrada="/entrar" />);

    expect(screen.getByText("Camila Souza")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /entrar na sua conta/i })).not.toBeInTheDocument();
  });

  it("abre o menu com o papel e a opção de sair", async () => {
    const usuario = userEvent.setup();
    render(<AccountMenu sessao={{ nome: "Olívia", papel: "organizer" }} caminhoEntrada="/entrar" />);

    await usuario.click(screen.getByRole("button", { name: /olívia/i }));

    expect(screen.getByRole("menu")).toBeInTheDocument();
    expect(screen.getByText("Organizador")).toBeInTheDocument();
    expect(screen.getByRole("menuitem", { name: "Sair" })).toBeInTheDocument();
  });

  it.each([
    ["customer", "Meus ingressos", "/meus-ingressos"],
    ["gate", "Validar ingressos", "/portaria"],
  ] as const)(
    "leva %s ao destino de trabalho dele",
    async (papel, rotulo, href) => {
      // Sem este item, o usuário de portaria entra, cai no catálogo de filmes
      // — que não é a tela dele — e só alcança a validação digitando o
      // endereço. Um papel cuja tela depende de endereço decorado é uma tela
      // que, na prática, não existe.
      const usuario = userEvent.setup();
      render(<AccountMenu sessao={{ nome: "Olívia", papel }} caminhoEntrada="/entrar" />);

      await usuario.click(screen.getByRole("button", { name: /olívia/i }));

      expect(screen.getByRole("menuitem", { name: rotulo })).toHaveAttribute("href", href);
    },
  );

  it("não oferece destino de trabalho ao organizador, que ainda não tem painel", async () => {
    // Um item que leva a uma recusa por papel é pior do que item nenhum.
    const usuario = userEvent.setup();
    render(<AccountMenu sessao={{ nome: "Olívia", papel: "organizer" }} caminhoEntrada="/entrar" />);

    await usuario.click(screen.getByRole("button", { name: /olívia/i }));

    expect(screen.getAllByRole("menuitem")).toHaveLength(1);
    expect(screen.getByRole("menuitem", { name: "Sair" })).toBeInTheDocument();
  });

  it("fecha com Escape", async () => {
    const usuario = userEvent.setup();
    render(<AccountMenu sessao={{ nome: "Olívia", papel: "gate" }} caminhoEntrada="/entrar" />);

    await usuario.click(screen.getByRole("button", { name: /olívia/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await usuario.keyboard("{Escape}");
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("encerra a sessão por POST e revalida a rota (FR-015, R8)", async () => {
    const usuario = userEvent.setup();
    const fetchMock = mockFetch({ ok: true, status: 204 });
    render(<AccountMenu sessao={{ nome: "Camila", papel: "customer" }} caminhoEntrada="/entrar" />);

    await usuario.click(screen.getByRole("button", { name: /camila/i }));
    await usuario.click(screen.getByRole("menuitem", { name: "Sair" }));

    await waitFor(() => expect(refresh).toHaveBeenCalled());
    expect(fetchMock).toHaveBeenCalledWith("/api/sair", { method: "POST" });
  });

  it("distingue os dois estados por texto, não só por cor (FR-026)", () => {
    const { unmount } = render(<AccountMenu sessao={null} caminhoEntrada="/entrar" />);
    expect(screen.getByText("Entrar")).toBeInTheDocument();
    unmount();

    render(<AccountMenu sessao={{ nome: "Camila", papel: "customer" }} caminhoEntrada="/entrar" />);
    expect(screen.getByText("Camila")).toBeInTheDocument();
    expect(screen.queryByText("Entrar")).not.toBeInTheDocument();
  });
});
