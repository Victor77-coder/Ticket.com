import type { Metadata } from "next";
import "@/styles/tokens.css";

import { SiteHeader } from "@/components/header/SiteHeader";

export const metadata: Metadata = {
  // O título do navegador carrega o mesmo nome do cabeçalho (FR-004).
  title: "ticket.com — ingressos de cinema",
  description: "Compre ingressos para os filmes em cartaz.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        {/* O cabeçalho mora no layout raiz, não em cada página: é isso que
         * garante a mesma composição em todas elas (FR-001). */}
        <SiteHeader />
        {children}
      </body>
    </html>
  );
}
