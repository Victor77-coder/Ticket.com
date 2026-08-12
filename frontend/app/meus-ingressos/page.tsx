import Link from "next/link";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";

import Ingresso from "@/components/tickets/Ingresso";
import { COOKIE_SESSAO, fetchMeusIngressos } from "@/lib/api";
import type { MeuIngresso } from "@/lib/types";

import estilos from "./meus-ingressos.module.css";

/**
 * `/meus-ingressos` — o endereço permanente do que já foi comprado.
 *
 * A feature 008 emitiu o ingresso e o mostrou na confirmação da compra. O
 * problema era que ele existia e era **inalcançável**: quem saía da
 * confirmação não tinha caminho de volta. Esta página é esse caminho.
 *
 * OS GRUPOS VÊM SEPARADOS E ORDENADOS DO SERVIDOR, e a tela não recompara
 * datas. A fronteira entre futuro e passado é decisão do servidor, com o
 * relógio do banco (FR-010): o navegador pode estar com a hora errada, e
 * "meu ingresso sumiu do topo" é o defeito que isso produziria.
 *
 * O ESTADO VEM DO SERVIDOR A CADA VISITA. Ingresso não mora em estado de
 * componente — é o mesmo princípio que faz a confirmação da 008 sobreviver a
 * um recarregamento.
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Meus ingressos — ticket.com",
};

export default async function MeusIngressosPage() {
  const chave = (await cookies()).get(COOKIE_SESSAO)?.value;

  // Visitante vai para a entrada e volta para cá — o mesmo retorno seguro que
  // a 003 validou. Nenhum dado de ingresso é exibido no caminho (FR-051).
  if (!chave) redirect("/entrar?next=/meus-ingressos");

  const resultado = await fetchMeusIngressos(chave);

  if (!resultado.ok) {
    if (resultado.status === 401) redirect("/entrar?next=/meus-ingressos");

    if (resultado.status === 403) {
      // Papel sem ingressos. NÃO conduzir à entrada: entrar de novo não muda
      // o papel, e o caminho não teria saída.
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

    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1 className={estilos.avisoTitulo}>Não conseguimos carregar seus ingressos</h1>
          <p className={estilos.avisoTexto}>
            O servidor não respondeu agora. Atualize a página em alguns instantes — seus
            ingressos continuam guardados.
          </p>
          <Link href="/" className={estilos.acao}>
            Voltar ao início
          </Link>
        </section>
      </main>
    );
  }

  const { futuros, passados } = resultado.data;

  // O estado vazio é para quem NÃO TEM INGRESSO NENHUM. Quem só tem ingressos
  // de sessões passadas vê a lista normal — ele comprou, e dizer "você ainda
  // não tem ingressos" seria mentira (FR-013).
  if (futuros.length === 0 && passados.length === 0) {
    return (
      <main className={estilos.pagina}>
        <h1 className={estilos.titulo}>Meus ingressos</h1>
        <section className={estilos.vazio}>
          <p className={estilos.vazioTitulo}>Você ainda não tem ingressos.</p>
          <p className={estilos.vazioTexto}>
            Quando você comprar, eles ficam aqui — com o código para apresentar na
            entrada do cinema.
          </p>
          <Link href="/" className={estilos.acao}>
            Ver filmes em cartaz
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className={estilos.pagina}>
      <h1 className={estilos.titulo}>Meus ingressos</h1>

      {futuros.length > 0 && (
        <Grupo
          titulo="Próximas sessões"
          descricao="Do que acontece primeiro para o mais distante."
          ingressos={futuros}
        />
      )}

      {passados.length > 0 && (
        <Grupo
          titulo="Já aconteceram"
          descricao="Continuam aqui, com o código, do mais recente para o mais antigo."
          ingressos={passados}
          esmaecido
        />
      )}
    </main>
  );
}

function Grupo({
  titulo,
  descricao,
  ingressos,
  esmaecido = false,
}: {
  titulo: string;
  descricao: string;
  ingressos: MeuIngresso[];
  esmaecido?: boolean;
}) {
  return (
    /* A distinção entre os grupos NÃO depende só de cor: cada um tem título
     * próprio e uma linha dizendo o que ele é. O esmaecimento é reforço, não
     * o sinal (FR-006). */
    <section className={estilos.grupo} aria-labelledby={`grupo-${titulo}`}>
      <h2 id={`grupo-${titulo}`} className={estilos.grupoTitulo}>
        {titulo}
      </h2>
      <p className={estilos.grupoDescricao}>{descricao}</p>

      <ul className={esmaecido ? estilos.listaPassada : estilos.lista}>
        {ingressos.map((ingresso) => (
          <li key={ingresso.id} className={estilos.item}>
            {ingresso.sessao_cancelada && (
              /* Não esconder o ingresso de sessão cancelada é o ponto: some
               * justamente aquele sobre o qual a pessoa precisa de
               * explicação (FR-011). */
              <p className={estilos.cancelada} role="status">
                Esta sessão foi cancelada. Procure a bilheteria do cinema sobre a
                devolução.
              </p>
            )}

            {/* O mesmo cartão da confirmação da 008. Sem `indice`/`total`:
              * aqui cada ingresso é uma linha da lista, não "1 de 2" de uma
              * compra. */}
            <ul className={estilos.cartao}>
              <Ingresso ingresso={ingresso} />
            </ul>

            {/* `aria-label` em vez de um `<span>` escondido: a lista tem um
              * link por ingresso, e "Abrir e compartilhar" repetido cinco
              * vezes não diz a quem navega por links QUAL deles é qual. O
              * rótulo resolve isso sem duplicar o utilitário de texto
              * invisível que já existe no cabeçalho. */}
            <Link
              href={`/meus-ingressos/${ingresso.id}`}
              className={estilos.abrir}
              aria-label={`Abrir e compartilhar o ingresso do lugar ${ingresso.assento.fileira}${ingresso.assento.numero}`}
            >
              Abrir e compartilhar
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
