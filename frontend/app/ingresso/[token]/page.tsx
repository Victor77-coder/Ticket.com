import type { Metadata } from "next";

import Ingresso from "@/components/tickets/Ingresso";
import { fetchIngressoCompartilhado } from "@/lib/api";

import estilos from "./publico.module.css";

/**
 * `/ingresso/[token]` — o ingresso compartilhado. **Pública.**
 *
 * A única página do sistema que mostra um ingresso a quem não entrou em conta
 * nenhuma. Compartilhar ingresso é entregar o direito de entrar: quem recebe
 * precisa do QR na fila, e uma página compartilhada sem ele seria decorativa.
 *
 * A consequência é assumida — o link é CREDENCIAL AO PORTADOR —, e por isso
 * três coisas nesta página não são opcionais:
 *
 * 1. `force-dynamic`. Sem ele, a revogação continua correta no banco e
 *    IRRELEVANTE na tela: a credencial seguiria sendo servida do cache por
 *    quanto tempo o cache durar. É a falha mais discreta desta feature —
 *    nenhum teste de back-end a pegaria, e o comportamento observável seria
 *    "revoguei e o link continua abrindo".
 *
 * 2. `noindex`. O endereço É a credencial. Indexado, passa a ser encontrável
 *    por quem nunca o recebeu, e revogar um por um não recupera o que já foi
 *    rastreado.
 *
 * 3. `no-referrer`. Sem isso, qualquer navegação a partir daqui manda o
 *    endereço completo — token incluído — no cabeçalho `Referer` do destino.
 *    A página não tem link de saída hoje; o cabeçalho faz a garantia
 *    sobreviver ao dia em que alguém acrescentar um.
 *
 * E O COOKIE DE SESSÃO NÃO É REPASSADO. `fetchIngressoCompartilhado` não o
 * aceita, e do lado do Django a view declara `authentication_classes = []`.
 * Nos dois lados a mesma ideia: não existe caminho pelo qual esta página
 * enxergue quem está olhando.
 */

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Ingresso — ticket.com",
  robots: { index: false, follow: false },
  referrer: "no-referrer",
};

export default async function IngressoCompartilhadoPage({
  params,
}: {
  params: Promise<{ token: string }>;
}) {
  const { token } = await params;

  const resultado = await fetchIngressoCompartilhado(token);

  if (!resultado.ok) {
    // Token inexistente, revogado e substituído chegam aqui do mesmo jeito —
    // o servidor já os fez convergir. Esta tela é a mesma para os três.
    //
    // NÃO é `notFound()`: a 404 genérica do site mandaria quem recebeu o
    // ingresso de um amigo concluir que o site quebrou. A frase diz o que
    // houve e qual é a próxima ação (FR-052).
    const foraDoAr = resultado.status !== 404 && resultado.status !== 0;

    return (
      <main className={estilos.pagina}>
        <section className={estilos.morto} role="alert">
          <h1 className={estilos.mortoTitulo}>
            {foraDoAr ? "Não conseguimos abrir este ingresso" : "Este link não vale mais"}
          </h1>
          <p className={estilos.mortoTexto}>
            {foraDoAr
              ? "O servidor não respondeu agora. Tente atualizar a página em alguns instantes."
              : "Quem enviou o ingresso pode ter cancelado o link. Peça um novo a essa pessoa."}
          </p>
        </section>
      </main>
    );
  }

  return (
    <main className={estilos.pagina}>
      <section className={estilos.cartao} aria-labelledby="titulo-ingresso">
        <h1 id="titulo-ingresso" className={estilos.titulo}>
          Ingresso
        </h1>
        <p className={estilos.subtitulo}>
          Apresente o código na entrada da sala.
        </p>

        {/* Uma lista de um item: o componente é o mesmo cartão da lista e da
          * confirmação. Ele só aceita a forma `Ingresso` — então não TEM COMO
          * renderizar comprador, valor ou os outros ingressos da compra,
          * porque não recebe esses campos. */}
        <ul className={estilos.lista}>
          <Ingresso ingresso={resultado.data} />
        </ul>
      </section>
    </main>
  );
}
