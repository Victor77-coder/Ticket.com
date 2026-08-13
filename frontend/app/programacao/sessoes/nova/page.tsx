import Link from "next/link";

import { EstadoVazio } from "@/components/programacao/EstadoVazio";
import { ProgramarSessao } from "@/components/programacao/ProgramarSessao";
import { fetchFilmesDoPainel, fetchSalas } from "@/lib/api";

import {
  chaveDeSessao,
  conduzirAEntrada,
  TelaDeErro,
  TelaDeRecusa,
} from "../../guarda";
import estilos from "@/components/programacao/programacao.module.css";

/**
 * `/programacao/sessoes/nova` — o formulário que alimenta a grade.
 *
 * O CATÁLOGO LOCAL VEM PRIMEIRO, e a busca no TMDb fica ao lado como segunda
 * porta. É a ordem que FR-013 e FR-014 pedem juntos: programar com o que já
 * existe não pode depender da API externa, e com o TMDb fora do ar esta tela
 * continua inteira — só a busca degrada.
 *
 * SEM SALA NENHUMA o formulário não é exibido: um seletor de sala vazio faria
 * a pessoa preencher tudo para receber uma recusa no fim. O estado vazio manda
 * criar a sala primeiro (FR-007).
 */

export const dynamic = "force-dynamic";

export const metadata = {
  title: "Programar sessão — ticket.com",
};

const DESTINO = "/programacao/sessoes/nova";

export default async function NovaSessaoPage() {
  const chave = await chaveDeSessao(DESTINO);

  const [filmes, salas] = await Promise.all([
    fetchFilmesDoPainel(chave),
    fetchSalas(chave),
  ]);

  for (const resultado of [filmes, salas]) {
    if (!resultado.ok) {
      if (resultado.status === 401) conduzirAEntrada(DESTINO);
      if (resultado.status === 403) return <TelaDeRecusa />;
      return <TelaDeErro titulo="Não conseguimos abrir o formulário" />;
    }
  }

  // O laço acima já devolveu para todo caso de falha; o TypeScript não
  // acompanha isso através do array, então as leituras abaixo são explícitas.
  const listaDeFilmes = filmes.ok ? filmes.data.results : [];
  const listaDeSalas = salas.ok ? salas.data.results : [];

  return (
    <main className={estilos.pagina}>
      <header className={estilos.cabecalho}>
        <div>
          <h1 className={estilos.titulo}>Programar sessão</h1>
          <p className={estilos.subtitulo}>
            Escolha o filme, a sala e o horário. Publicar coloca à venda na hora.
          </p>
        </div>
        <Link href="/programacao" className={estilos.acaoSecundaria}>
          Voltar à grade
        </Link>
      </header>

      {listaDeSalas.length === 0 ? (
        <EstadoVazio
          titulo="Nenhuma sala cadastrada"
          texto="Uma sessão precisa de uma sala com lugares. Crie a primeira e volte aqui."
          acao={{ href: "/programacao/salas", rotulo: "Criar uma sala" }}
        />
      ) : (
        <ProgramarSessao filmes={listaDeFilmes} salas={listaDeSalas} />
      )}
    </main>
  );
}
