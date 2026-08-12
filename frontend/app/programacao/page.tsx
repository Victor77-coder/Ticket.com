import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { EstadoVazio } from "@/components/programacao/EstadoVazio";
import { Grade } from "@/components/programacao/Grade";
import { COOKIE_SESSAO, fetchGrade } from "@/lib/api";

import estilos from "@/components/programacao/programacao.module.css";

/**
 * `/programacao` — a casa do organizador.
 *
 * É onde ele pousa ao entrar (FR-003) e, diferente da portaria, **não** é onde
 * ele fica preso: o catálogo público continua aberto, porque é ali que ele
 * confere que a sessão publicada apareceu à venda.
 *
 * `force-dynamic` porque o estado depende da sessão e do papel — uma resposta
 * guardada serviria a pessoa errada.
 *
 * OS TRÊS DESFECHOS, e a distinção é a mesma que `/portaria` já aplica:
 *   sem cookie ou `401` → conduz à entrada, e volta para cá depois;
 *   `403`               → RENDERIZA a recusa, com frase própria e saída para o
 *                         catálogo. Entrar de novo não muda o papel, então
 *                         mandar para a entrada seria caminho sem saída;
 *   qualquer outra      → o servidor não respondeu, e a página diz isso.
 *
 * A recusa existe PORQUE a autorização é do servidor: ela é a apresentação de
 * um `403` real, não um botão escondido (FR-037).
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Programação — ticket.com",
};

export default async function ProgramacaoPage() {
  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;

  if (!chave) redirect("/entrar?next=/programacao");

  const resultado = await fetchGrade(chave);

  if (!resultado.ok) {
    if (resultado.status === 401) redirect("/entrar?next=/programacao");

    if (resultado.status === 403) {
      return (
        <main className={estilos.pagina}>
          <section className={estilos.aviso} role="alert">
            <h1 className={estilos.avisoTitulo}>Esta área é da programação</h1>
            <p className={estilos.avisoTexto}>
              Programar filmes, salas e sessões é trabalho de quem organiza a
              grade. Sua conta tem outro papel neste sistema.
            </p>
            <Link href="/" className={estilos.acao}>
              Voltar ao catálogo
            </Link>
          </section>
        </main>
      );
    }

    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1 className={estilos.avisoTitulo}>Não conseguimos carregar a grade</h1>
          <p className={estilos.avisoTexto}>
            O servidor não respondeu agora. Atualize a página em alguns instantes.
          </p>
          <Link href="/" className={estilos.acao}>
            Voltar ao catálogo
          </Link>
        </section>
      </main>
    );
  }

  const { count, results } = resultado.data;

  return (
    <main className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <div>
          <h1 className={estilos.titulo}>Programação</h1>
          <p className={estilos.subtitulo}>
            {count === 0
              ? "Nenhuma sessão programada"
              : `${count} ${count === 1 ? "sessão programada" : "sessões programadas"}`}
          </p>
        </div>

        <nav className={estilos.atalhos} aria-label="Ações da programação">
          <Link href="/programacao/sessoes/nova" className={estilos.acao}>
            Programar sessão
          </Link>
          <Link href="/programacao/salas" className={estilos.acaoSecundaria}>
            Salas
          </Link>
        </nav>
      </header>

      {count === 0 ? (
        <EstadoVazio
          titulo="Nenhuma sessão programada ainda"
          texto="Escolha um filme, uma sala e um horário. A sessão publicada aparece no catálogo na hora, sem passo nenhum no meio."
          acao={{ href: "/programacao/sessoes/nova", rotulo: "Programar a primeira" }}
        />
      ) : (
        <Grade sessoes={results} />
      )}
    </main>
  );
}
