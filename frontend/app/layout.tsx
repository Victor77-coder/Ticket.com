import type { Metadata } from "next";
import "@/styles/tokens.css";

import { SiteHeader } from "@/components/header/SiteHeader";
import { getSessao } from "@/lib/session";

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
    <html lang="pt-BR">
      <body>
        {/* O cabeçalho mora no layout raiz, não em cada página: é isso que
         * garante a mesma composição em todas elas (FR-001). */}
        <SiteHeader sessao={sessao} />
        {children}
      </body>
    </html>
  );
}
