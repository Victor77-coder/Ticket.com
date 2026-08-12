import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import { COOKIE_SESSAO } from "@/lib/api";

import estilos from "@/components/programacao/programacao.module.css";

/**
 * A guarda que toda página da área de programação repete.
 *
 * Existe porque são TRÊS páginas com o mesmo desfecho triplo, e a terceira
 * cópia é onde uma delas passa a mandar o papel errado para a entrada sem que
 * ninguém perceba:
 *
 *   sem cookie ou `401` → conduz à entrada, com `next` para voltar;
 *   `403`               → RENDERIZA a recusa. Entrar de novo não muda o papel,
 *                         então redirecionar seria caminho sem saída;
 *   qualquer outra      → o servidor não respondeu, e a página diz isso.
 *
 * ISTO NÃO É AUTORIZAÇÃO. A recusa é do Django, e esta função apenas
 * APRESENTA o `403` que ele devolveu — é o oposto de esconder o controle
 * (FR-037). Se este arquivo sumisse, nada ficaria exposto: a API continuaria
 * recusando igual.
 */

export async function chaveDeSessao(destino: string): Promise<string> {
  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;
  if (!chave) redirect(`/entrar?next=${destino}`);
  return chave;
}

export function conduzirAEntrada(destino: string): never {
  redirect(`/entrar?next=${destino}`);
}

export function TelaDeRecusa() {
  return (
    <main className={estilos.pagina}>
      <section className={estilos.aviso} role="alert">
        <h1 className={estilos.avisoTitulo}>Esta área é da programação</h1>
        <p className={estilos.avisoTexto}>
          Programar filmes, salas e sessões é trabalho de quem organiza a grade.
          Sua conta tem outro papel neste sistema.
        </p>
        <Link href="/" className={estilos.acao}>
          Voltar ao catálogo
        </Link>
      </section>
    </main>
  );
}

export function TelaDeErro({ titulo }: { titulo: string }) {
  return (
    <main className={estilos.pagina}>
      <section className={estilos.aviso} role="alert">
        <h1 className={estilos.avisoTitulo}>{titulo}</h1>
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
