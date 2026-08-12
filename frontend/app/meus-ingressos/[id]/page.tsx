import Link from "next/link";
import { cookies } from "next/headers";
import { notFound, redirect } from "next/navigation";

import Ingresso from "@/components/tickets/Ingresso";
import PainelDeLink from "@/components/tickets/PainelDeLink";
import { COOKIE_SESSAO, fetchIngresso } from "@/lib/api";

import estilos from "../meus-ingressos.module.css";

/**
 * `/meus-ingressos/[id]` — o endereço próprio de UM ingresso.
 *
 * É aqui que moram as ações de compartilhamento, e não na lista: gerar e
 * revogar são decisões sobre um ingresso específico, e uma lista com um painel
 * de link por linha empurraria a decisão para junto de um botão de rolagem.
 *
 * O `id` é o `public_id` — UUID, nunca sequencial. A escolha é da 008 e vale
 * aqui pelo mesmo motivo: um identificador sequencial na barra de endereços
 * revelaria quantos ingressos existem e convidaria a tentar o vizinho.
 *
 * `404` para ingresso alheio, nunca `403`: o servidor já decide assim, e esta
 * página só repassa. Um `403` confirmaria que aquele `public_id` existe.
 */

export const dynamic = "force-dynamic";

export default async function IngressoDoDonoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const destino = `/meus-ingressos/${id}`;

  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;
  if (!chave) redirect(`/entrar?next=${destino}`);

  const resultado = await fetchIngresso(chave, id);

  if (!resultado.ok) {
    if (resultado.status === 401) redirect(`/entrar?next=${destino}`);

    if (resultado.status === 403) {
      // Papel sem ingressos. NÃO conduzir à entrada: entrar de novo não muda
      // o papel (FR-051).
      return (
        <main className={estilos.pagina}>
          <section className={estilos.aviso} role="alert">
            <h1 className={estilos.avisoTitulo}>Esta área é de quem compra</h1>
            <p className={estilos.avisoTexto}>
              Ingressos ficam na conta de cliente que fez a compra. Sua conta tem outro
              papel neste sistema.
            </p>
            <Link href="/" className={estilos.acao}>
              Voltar ao início
            </Link>
          </section>
        </main>
      );
    }

    if (resultado.status === 404) notFound();

    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1 className={estilos.avisoTitulo}>Não conseguimos carregar este ingresso</h1>
          <p className={estilos.avisoTexto}>
            O servidor não respondeu agora. Atualize a página em alguns instantes — seu
            ingresso continua guardado.
          </p>
          <Link href="/meus-ingressos" className={estilos.acao}>
            Voltar aos meus ingressos
          </Link>
        </section>
      </main>
    );
  }

  const ingresso = resultado.data;

  return (
    <main className={estilos.pagina}>
      <Link href="/meus-ingressos" className={estilos.voltar}>
        ← Meus ingressos
      </Link>

      {ingresso.sessao_cancelada && (
        <p className={estilos.cancelada} role="status">
          Esta sessão foi cancelada. Procure a bilheteria do cinema sobre a devolução.
        </p>
      )}

      {/* O mesmo cartão da lista e da confirmação. Um ingresso só, então sem
        * "1 de N" para anunciar. */}
      <ul className={estilos.cartao}>
        <Ingresso ingresso={ingresso} />
      </ul>

      <PainelDeLink
        ingressoId={ingresso.id}
        inicial={ingresso.link ?? { ativo: false, endereco: null }}
      />
    </main>
  );
}
