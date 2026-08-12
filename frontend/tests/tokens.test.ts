import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/**
 * A PROVA DESTA FEATURE.
 *
 * Trocar um valor de cor **não quebra nenhum teste de comportamento**. Os 197
 * testes de front-end continuam verdes com o contorno de foco invisível, o
 * texto do botão ilegível e o assento selecionado indistinguível do tomado.
 * Nenhum deles mede contraste, e nenhum vai começar a medir por acidente.
 *
 * Pior: o dano é invisível para quem ESCOLHEU a cor. Quem passou uma hora
 * olhando a paleta enxerga distinções que um usuário de passagem não enxerga,
 * e um contorno de foco fraco só incomoda quem navega por teclado.
 *
 * Este arquivo é a única coisa entre o projeto e esse defeito. Os limites
 * estão em specs/011-marca-sem-laranja/contracts/contraste.md.
 *
 * ELE LÊ O ARQUIVO DE TOKENS, e isso não é detalhe: um teste que guarda a
 * própria cópia da paleta passa a testar a cópia. Se alguém trocar um valor
 * em `tokens.css` e esquecer de atualizar o teste, é o teste que tem de
 * falhar — não o contrário.
 *
 * As fórmulas são escritas à mão de propósito. Luminância relativa, razão de
 * contraste WCAG 2.1 e ΔE76 em CIELAB são fórmulas publicadas de vinte
 * linhas; uma biblioteca de cor aqui seria dependência para não escrever
 * aritmética.
 */

const RAIZ = join(__dirname, "..");
const TOKENS = join(RAIZ, "styles", "tokens.css");

// --- Medidas ---------------------------------------------------------------

type RGB = [number, number, number];

function paraRgb(valor: string): RGB {
  const hex = valor.trim().match(/^#([0-9a-f]{6})$/i);
  if (hex) {
    const n = hex[1];
    return [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255) as RGB;
  }
  const rgba = valor.trim().match(/^rgba?\(([^)]+)\)$/i);
  if (rgba) {
    const p = rgba[1].split(",").map((x) => parseFloat(x.trim()));
    return [p[0] / 255, p[1] / 255, p[2] / 255];
  }
  throw new Error(`valor de cor não reconhecido: ${valor}`);
}

const linear = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);

function luminancia(valor: string): number {
  const [r, g, b] = paraRgb(valor).map(linear);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

/** Razão de contraste WCAG 2.1. */
function contraste(frente: string, fundo: string): number {
  const a = luminancia(frente);
  const b = luminancia(fundo);
  return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
}

function paraLab(valor: string): [number, number, number] {
  const [r, g, b] = paraRgb(valor).map(linear);
  const X = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047;
  const Y = 0.2126 * r + 0.7152 * g + 0.0722 * b;
  const Z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883;
  const f = (t: number) => (t > 0.008856 ? Math.cbrt(t) : 7.787 * t + 16 / 116);
  const [fx, fy, fz] = [f(X), f(Y), f(Z)];
  return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
}

/**
 * Distância perceptual ΔE76.
 *
 * Abaixo de 25, duas cores são confundíveis num elemento pequeno — que é o
 * tamanho de um selo de estado ou de um texto de erro.
 */
function deltaE(a: string, b: string): number {
  const [l1, a1, b1] = paraLab(a);
  const [l2, a2, b2] = paraLab(b);
  return Math.sqrt((l1 - l2) ** 2 + (a1 - a2) ** 2 + (b1 - b2) ** 2);
}

// --- Leitura dos tokens ----------------------------------------------------

function lerTokens(): Record<string, string> {
  const css = readFileSync(TOKENS, "utf8");
  const tokens: Record<string, string> = {};
  for (const [, nome, valor] of css.matchAll(/(--[\w-]+):\s*([^;]+);/g)) {
    tokens[nome] = valor.trim();
  }
  return tokens;
}

function arquivosDoFront(): string[] {
  const ignorar = new Set(["node_modules", ".next", "test-results", "playwright-report"]);
  const achados: string[] = [];
  const andar = (dir: string) => {
    for (const entrada of readdirSync(dir)) {
      if (ignorar.has(entrada)) continue;
      const caminho = join(dir, entrada);
      if (statSync(caminho).isDirectory()) andar(caminho);
      else if (/\.(css|tsx?|svg)$/.test(entrada)) achados.push(caminho);
    }
  };
  andar(RAIZ);
  return achados;
}

const tokens = lerTokens();
const t = (nome: string) => {
  const valor = tokens[nome];
  if (!valor) throw new Error(`token ausente em tokens.css: ${nome}`);
  return valor;
};

// --- Os limites, de contracts/contraste.md ---------------------------------

describe("contraste (C1–C7)", () => {
  const casos: Array<[string, string, string, number]> = [
    ["C1 destaque como texto no fundo", "--cor-destaque", "--cor-fundo", 4.5],
    ["C2 destaque como texto na superfície", "--cor-destaque", "--cor-superficie", 4.5],
    ["C3 destaque-forte como contorno de foco", "--cor-destaque-forte", "--cor-fundo", 3.0],
    ["C4 texto sobre o destaque (repouso)", "--cor-sobre-destaque", "--cor-destaque", 4.5],
    // C5 é PAR com C4, não um caso à parte: o texto do botão vive sobre a base
    // em repouso e sobre a `-forte` no hover. Medir só o primeiro deixa de
    // fora o estado em que a pessoa está quando vai clicar.
    ["C5 texto sobre o destaque (hover)", "--cor-sobre-destaque", "--cor-destaque-forte", 4.5],
    ["C6 texto no fundo", "--cor-texto", "--cor-fundo", 4.5],
    ["C7 texto suave na superfície", "--cor-texto-suave", "--cor-superficie", 4.5],
  ];

  it.each(casos)("%s", (rotulo, frente, fundo, minimo) => {
    const medido = contraste(t(frente), t(fundo));
    // A mensagem nomeia o par e quanto faltou: uma falha que diz só "o
    // contraste está ruim" obriga a refazer a medição para descobrir onde.
    expect(
      medido,
      `${rotulo}: ${t(frente)} sobre ${t(fundo)} deu ${medido.toFixed(2)}:1, mínimo ${minimo}:1`,
    ).toBeGreaterThanOrEqual(minimo);
  });
});

describe("distância de estado (D1–D3)", () => {
  // A marca não pode ser confundível com uma cor que já significa outra
  // coisa. Foi esta medida que eliminou o âmbar da disputa: ele fica a ΔE 8
  // do alerta. Ver research.md, R1.
  const estados: Array<[string, string]> = [
    ["D1 erro", "--cor-erro"],
    ["D2 alerta", "--cor-alerta"],
    ["D3 sucesso", "--cor-sucesso"],
  ];

  it.each(estados)("%s está longe o bastante do destaque", (rotulo, estado) => {
    const medido = deltaE(t("--cor-destaque"), t(estado));
    expect(
      medido,
      `${rotulo}: destaque ${t("--cor-destaque")} × ${t(estado)} deu ΔE ${medido.toFixed(1)}, mínimo 25`,
    ).toBeGreaterThanOrEqual(25);
  });
});

describe("ausência (A1–A2)", () => {
  it("A1 nenhum vestígio da cor antiga em lugar nenhum", () => {
    const antigos = [/ff5c39/i, /ff7a5c/i, /255,\s*92,\s*57/];
    const vestigios: string[] = [];

    for (const arquivo of arquivosDoFront()) {
      // Este arquivo se exclui: ele CONTÉM os padrões, porque é quem procura
      // por eles. Sem a exclusão, A1 nunca poderia passar.
      if (arquivo === __filename) continue;

      const conteudo = readFileSync(arquivo, "utf8");
      if (antigos.some((padrao) => padrao.test(conteudo))) {
        vestigios.push(arquivo.replace(`${RAIZ}/`, ""));
      }
    }

    expect(vestigios, `a cor antiga sobreviveu em: ${vestigios.join(", ")}`).toEqual([]);
  });

  it("A2 nenhuma cor de marca fora de tokens.css", () => {
    // A disciplina da 006, verificada em vez de confiada. É ela que garante
    // que os 12 arquivos consumidores não precisaram ser tocados — e se um
    // precisar, é sinal de que um valor vazou.
    const fora: string[] = [];

    for (const arquivo of arquivosDoFront()) {
      if (arquivo === TOKENS) continue;
      if (!arquivo.endsWith(".css")) continue;

      const conteudo = readFileSync(arquivo, "utf8");
      for (const linha of conteudo.split("\n")) {
        const semComentario = linha.replace(/\/\*.*?\*\//g, "");
        if (/#[0-9a-f]{3,8}\b/i.test(semComentario) || /rgba?\(\s*\d/.test(semComentario)) {
          fora.push(`${arquivo.replace(`${RAIZ}/`, "")}: ${linha.trim()}`);
        }
      }
    }

    expect(fora, `valor de cor fora dos tokens:\n${fora.join("\n")}`).toEqual([]);
  });
});

describe("o ícone de aba", () => {
  // `app/icon.svg` é a variante compacta da marca, e é a ÚNICA superfície que
  // não pode consumir tokens: um favicon é renderizado fora do documento, sem
  // acesso ao CSS. As cores ficam literais lá por necessidade.
  //
  // Isso cria um SEGUNDO LUGAR PARA A VERDADE MORAR — e a próxima pessoa que
  // trocar a cor da marca vai esquecer dele, porque ele não aparece em
  // nenhuma tela durante o desenvolvimento. A duplicação fica segura porque é
  // verificada, não porque alguém vai lembrar.
  const icone = readFileSync(join(RAIZ, "app", "icon.svg"), "utf8").toLowerCase();

  it.each([
    ["o destaque", "--cor-destaque"],
    ["o fundo", "--cor-fundo"],
    ["o texto", "--cor-texto"],
  ])("%s do ícone acompanha o token", (_rotulo, nome) => {
    expect(icone).toContain(t(nome).toLowerCase());
  });
});

describe("os nomes dos tokens de destaque", () => {
  // Renomear um deles quebraria os 12 consumidores EM SILÊNCIO: CSS não
  // reclama de variável inexistente, ele simplesmente não pinta nada.
  it.each([
    "--cor-destaque",
    "--cor-destaque-forte",
    "--cor-destaque-fraca",
    "--cor-destaque-vestigio",
    "--cor-sobre-destaque",
  ])("%s continua existindo", (nome) => {
    expect(tokens[nome]).toBeDefined();
  });
});

describe("o que não pode mudar", () => {
  it("o fundo do QR continua branco", () => {
    // Exceção deliberada da 008: leitor de QR depende do contraste entre
    // módulo escuro e fundo claro. Harmonizá-lo com a marca faz a catraca
    // parar de ler. É a superfície que mais parece fora do lugar numa feature
    // de paleta, e a única que não pode mudar.
    expect(t("--cor-fundo-qr").toLowerCase()).toBe("#ffffff");
  });

  it.each([
    ["--cor-sucesso", "#3ecf8e"],
    ["--cor-alerta", "#f5b544"],
    ["--cor-erro", "#ff6b6b"],
  ])("%s não foi tocado", (nome, esperado) => {
    // Mudar uma cor de estado muda o significado de um estado — fora do
    // escopo desta feature por decisão registrada na spec.
    expect(t(nome).toLowerCase()).toBe(esperado);
  });
});
