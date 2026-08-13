"use client";

import { useState } from "react";

import type { FilmeDoPainel, SalaDoPainel } from "@/lib/types";

import { BuscaDeFilme } from "./BuscaDeFilme";
import { FormularioDeSessao } from "./FormularioDeSessao";
import estilos from "./programacao.module.css";

/**
 * Costura o formulário e a busca no TMDb.
 *
 * Existe por um motivo só, e ele é a experiência: trazer um filme do TMDb e
 * depois ter de procurá-lo na lista seria uma tarefa a mais criada pela
 * própria ferramenta. O filme importado entra na lista **e** fica selecionado.
 *
 * A busca é a segunda porta, e a página funciona inteira sem ela — é o que
 * FR-014 pede: com o TMDb fora do ar, programar com o catálogo local continua.
 */

type Props = {
  filmes: FilmeDoPainel[];
  salas: SalaDoPainel[];
};

export function ProgramarSessao({ filmes: iniciais, salas }: Props) {
  const [filmes, setFilmes] = useState(iniciais);
  const [filme, setFilme] = useState("");

  function aoImportar(novo: FilmeDoPainel) {
    setFilmes((atual) =>
      atual.some((item) => item.id === novo.id)
        ? atual
        : [...atual, novo].sort((a, b) => a.titulo.localeCompare(b.titulo, "pt-BR")),
    );
    setFilme(String(novo.id));
  }

  return (
    <div className={estilos.colunas}>
      <FormularioDeSessao
        filmes={filmes}
        salas={salas}
        filme={filme}
        onFilmeChange={setFilme}
      />
      <BuscaDeFilme onImportado={aoImportar} />
    </div>
  );
}
