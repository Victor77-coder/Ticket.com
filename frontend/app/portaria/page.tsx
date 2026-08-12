import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { COOKIE_SESSAO, fetchSessoesDaPortaria } from "@/lib/api";

import PortariaCliente from "./PortariaCliente";
import estilos from "./portaria.module.css";

/**
 * `/portaria` — a validação na entrada.
 *
 * É a tela que fecha o fluxo ponta a ponta: catálogo → sessão → assento →
 * pagamento → ingresso → **entrada**.
 *
 * `force-dynamic` porque o estado depende da sessão e do papel — uma resposta
 * guardada serviria a pessoa errada.
 *
 * VISITANTE é conduzido à entrada e volta para cá. PAPEL ERRADO **não é**:
 * entrar de novo não muda o papel, e o caminho não teria saída. É a mesma
 * distinção que a 009 já aplica em "Meus ingressos", agora do outro lado.
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Portaria — ticket.com",
};

export default async function PortariaPage() {
  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;

  if (!chave) redirect("/entrar?next=/portaria");

  const resultado = await fetchSessoesDaPortaria(chave);

  if (!resultado.ok) {
    if (resultado.status === 401) redirect("/entrar?next=/portaria");

    if (resultado.status === 403) {
      return (
        <main className={estilos.pagina}>
          <section className={estilos.aviso} role="alert">
            <h1 className={estilos.avisoTitulo}>Esta área é da portaria</h1>
            <p className={estilos.avisoTexto}>
              A validação de ingressos é feita pela equipe da entrada. Sua conta tem
              outro papel neste sistema.
            </p>
            <Link href="/" className={estilos.acao}>
              Voltar ao início
            </Link>
          </section>
        </main>
      );
    }

    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1 className={estilos.avisoTitulo}>Não conseguimos carregar as sessões</h1>
          <p className={estilos.avisoTexto}>
            O servidor não respondeu agora. Atualize a página em alguns instantes.
          </p>
          <Link href="/" className={estilos.acao}>
            Voltar ao início
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className={estilos.pagina}>
      <PortariaCliente sessoes={resultado.data.sessoes} />
    </main>
  );
}
