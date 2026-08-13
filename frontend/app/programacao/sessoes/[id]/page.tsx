import Link from "next/link";

import { EditarSessao } from "@/components/programacao/EditarSessao";
import { fetchFilmesDoPainel, fetchGrade, fetchSalas } from "@/lib/api";

import {
  chaveDeSessao,
  conduzirAEntrada,
  TelaDeErro,
  TelaDeRecusa,
} from "../../guarda";
import estilos from "@/components/programacao/programacao.module.css";

/**
 * `/programacao/sessoes/[id]` — corrigir um rascunho.
 *
 * SÓ RASCUNHO CHEGA AQUI COM FORMULÁRIO. Sessão publicada ou cancelada abre a
 * mesma página com a explicação de que a correção não é o caminho — cancelar e
 * programar outra é (FR-024). A recusa é do servidor de qualquer forma: o
 * `PATCH` devolve `409`, e esta tela existe para dizer isso ANTES de a pessoa
 * digitar de novo o que já estava certo.
 *
 * A sessão é lida da GRADE, e não de um endpoint de detalhe: a linha da grade
 * já traz tudo o que o formulário precisa, e um endereço novo para o mesmo dado
 * seria uma segunda forma de perguntar a mesma coisa.
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Editar sessão — ticket.com",
};

export default async function EditarSessaoPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const destino = `/programacao/sessoes/${id}`;

  const chave = await chaveDeSessao(destino);

  const [grade, filmes, salas] = await Promise.all([
    fetchGrade(chave),
    fetchFilmesDoPainel(chave),
    fetchSalas(chave),
  ]);

  for (const resultado of [grade, filmes, salas]) {
    if (!resultado.ok) {
      if (resultado.status === 401) conduzirAEntrada(destino);
      if (resultado.status === 403) return <TelaDeRecusa />;
      return <TelaDeErro titulo="Não conseguimos abrir esta sessão" />;
    }
  }

  const sessao = grade.ok
    ? grade.data.results.find((linha) => String(linha.id) === id)
    : undefined;

  if (!sessao) {
    return (
      <main className={estilos.pagina}>
        <section className={estilos.aviso} role="alert">
          <h1 className={estilos.avisoTitulo}>Sessão não encontrada</h1>
          <p className={estilos.avisoTexto}>
            Ela pode ter sido removida, ou o endereço está errado.
          </p>
          <Link href="/programacao" className={estilos.acao}>
            Voltar à grade
          </Link>
        </section>
      </main>
    );
  }

  return (
    <main className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <div>
          <h1 className={estilos.titulo}>Editar sessão</h1>
          <p className={estilos.subtitulo}>
            {sessao.filme.titulo} · {sessao.sala.nome}
          </p>
        </div>
        <Link href="/programacao" className={estilos.acaoSecundaria}>
          Voltar à grade
        </Link>
      </header>

      {sessao.pode_editar ? (
        <EditarSessao
          sessao={sessao}
          filmes={filmes.ok ? filmes.data.results : []}
          salas={salas.ok ? salas.data.results : []}
        />
      ) : (
        <section className={estilos.aviso} role="alert">
          <h2 className={estilos.avisoTitulo}>
            Esta sessão não está mais em rascunho
          </h2>
          <p className={estilos.avisoTexto}>
            Só é possível alterar uma sessão em rascunho. Depois de publicada,
            filme, sala, horário e preço ficam fixos — mudar algum deles mudaria
            o que já foi vendido. Para corrigir esta, cancele e programe outra.
          </p>
          <Link href="/programacao/sessoes/nova" className={estilos.acao}>
            Programar outra
          </Link>
        </section>
      )}
    </main>
  );
}
