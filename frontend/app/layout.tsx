import type { Metadata } from "next";
import { Archivo } from "next/font/google";
import "@/styles/tokens.css";

import { SiteHeader } from "@/components/header/SiteHeader";
import { getSessao } from "@/lib/session";

/**
 * Archivo — família única em fonte variável.
 *
 * O eixo de largura (`wdth`) é o que dá o contraste entre display e texto: o
 * título do filme sai expandido e o corpo sai normal, do **mesmo arquivo**.
 * Sem isso seriam duas famílias a casar, e a coerência dependeria de bom
 * gosto em vez de construção (R1).
 *
 * `next/font/google` baixa em tempo de build e serve do próprio domínio —
 * nenhuma requisição a terceiro em tempo de visita. É o Princípio VII
 * aplicado a fontes, o mesmo raciocínio que mantém o TMDb fora do caminho de
 * leitura (R2).
 *
 * E gera um fallback ajustado por métrica, que é o que impede o texto de
 * saltar de posição quando a fonte chega (FR-011).
 */
const archivo = Archivo({
  subsets: ["latin"],
  // Sem declarar o eixo, chega só a largura padrão e o display não expande.
  axes: ["wdth"],
  display: "swap",
  variable: "--fonte-archivo",
});

export const metadata: Metadata = {
  // O título do navegador carrega o mesmo nome do cabeçalho (FR-004).
  title: "ticket.com — ingressos de cinema",
  description: "Compre ingressos para os filmes em cartaz.",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Resolvida no servidor a cada requisição: sem piscar entre "Entrar" e o
  // nome, e o papel nunca vem de valor guardado no navegador (R6, FR-022).
  const sessao = await getSessao();

  return (
    <html lang="pt-BR" className={archivo.variable}>
      <body>
        {/* O cabeçalho mora no layout raiz, não em cada página: é isso que
         * garante a mesma composição em todas elas (FR-001). */}
        <SiteHeader sessao={sessao} />
        {children}
      </body>
    </html>
  );
}
