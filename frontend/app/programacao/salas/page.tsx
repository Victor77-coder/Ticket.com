import Link from "next/link";

import { PainelDeSalas } from "@/components/programacao/PainelDeSalas";
import { fetchSalas } from "@/lib/api";

import { chaveDeSessao, conduzirAEntrada, TelaDeErro, TelaDeRecusa } from "../guarda";
import estilos from "@/components/programacao/programacao.module.css";

/**
 * `/programacao/salas` — as salas e os lugares que nascem com elas.
 *
 * O mapa físico segue a MESMA regra do cenário de demonstração: fileiras
 * identificadas por letra, última fileira possivelmente incompleta, e os
 * lugares de acessibilidade no fundo. A regra tem um dono só
 * (`screening/services/salas.py`), consumido pelo painel e pelo seed — e há
 * teste comparando lugar a lugar o que os dois produzem (FR-017).
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Salas — ticket.com",
};

const DESTINO = "/programacao/salas";

export default async function SalasPage() {
  const chave = await chaveDeSessao(DESTINO);
  const resultado = await fetchSalas(chave);

  if (!resultado.ok) {
    if (resultado.status === 401) conduzirAEntrada(DESTINO);
    if (resultado.status === 403) return <TelaDeRecusa />;
    return <TelaDeErro titulo="Não conseguimos carregar as salas" />;
  }

  return (
    <main className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <div>
          <h1 className={estilos.titulo}>Salas</h1>
          <p className={estilos.subtitulo}>
            Os lugares nascem com a sala: fileiras por letra, e a acessibilidade
            na última.
          </p>
        </div>
        <Link href="/programacao" className={estilos.acaoSecundaria}>
          Voltar à grade
        </Link>
      </header>

      <PainelDeSalas salas={resultado.data.results} />
    </main>
  );
}
