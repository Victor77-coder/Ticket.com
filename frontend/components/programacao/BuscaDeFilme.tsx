"use client";

import { useState } from "react";

import type { FilmeDoPainel, ResultadoTmdb } from "@/lib/types";

import estilos from "./programacao.module.css";

/**
 * Trazer um filme que o catálogo local ainda não tem.
 *
 * A SEGUNDA PORTA, e não a primeira: programar com o catálogo local não pode
 * depender do TMDb (FR-014). Com a API externa fora do ar, este bloco exibe a
 * frase que o servidor mandou e o formulário ao lado continua inteiro.
 *
 * OS TRÊS ESTADOS de FR-007 estão aqui, e nenhum deles é uma área em branco:
 *   resultados  → cada linha diz se o filme já está no catálogo;
 *   nada achado → "nada encontrado para <termo>", com o termo dentro;
 *   TMDb fora   → a frase do servidor, mais o convite a seguir com o local.
 *
 * A BUSCA É POR ENVIO, não a cada tecla. Cada busca é uma requisição ao TMDb
 * pelo nosso servidor, e disparar a cada letra gastaria dez chamadas externas
 * para uma palavra — diferente da busca do cabeçalho, que lê o banco local.
 */

type Props = {
  /** Chamado com o filme já persistido localmente. */
  onImportado: (filme: FilmeDoPainel) => void;
};

export function BuscaDeFilme({ onImportado }: Props) {
  const [termo, setTermo] = useState("");
  const [buscado, setBuscado] = useState("");
  const [resultados, setResultados] = useState<ResultadoTmdb[] | null>(null);
  const [falha, setFalha] = useState("");
  const [buscando, setBuscando] = useState(false);
  const [importando, setImportando] = useState<number | null>(null);

  async function buscar() {
    const limpo = termo.trim();
    if (!limpo) return;

    setBuscando(true);
    setFalha("");

    try {
      const resposta = await fetch(
        `/api/programacao/filmes/busca?q=${encodeURIComponent(limpo)}`,
      );
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        setResultados(null);
        setFalha(corpo?.detail ?? "A busca não respondeu agora.");
        return;
      }

      setBuscado(corpo.termo);
      setResultados(corpo.results);
    } finally {
      setBuscando(false);
    }
  }

  async function importar(resultado: ResultadoTmdb) {
    setImportando(resultado.tmdb_id);
    setFalha("");

    try {
      const resposta = await fetch("/api/programacao/filmes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tmdb_id: resultado.tmdb_id }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        setFalha(corpo?.detail ?? "Não foi possível trazer este filme agora.");
        return;
      }

      // `201` e `200` seguem pelo mesmo caminho: pediram um filme e receberam
      // um filme. O segundo só significa que ele já estava aqui (FR-012).
      onImportado(corpo as FilmeDoPainel);
    } finally {
      setImportando(null);
    }
  }

  return (
    <section className={estilos.busca} aria-label="Buscar filme no TMDb">
      <h2 className={estilos.buscaTitulo}>Não achou o filme?</h2>
      <p className={estilos.buscaTexto}>
        Busque no catálogo do TMDb. Escolher um resultado traz o filme para cá,
        com pôster, sinopse e trailers.
      </p>

      <div className={estilos.buscaLinha}>
        <label className={estilos.campo}>
          <span className={estilos.rotulo}>Título</span>
          <input
            type="search"
            className={estilos.entrada}
            value={termo}
            onChange={(e) => setTermo(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                // Enter num campo de busca busca. `preventDefault` porque um
                // campo de busca solto ainda dispara envio implícito quando
                // alguém aninha este bloco num formulário depois.
                e.preventDefault();
                buscar();
              }
            }}
          />
        </label>
        <button
          type="button"
          className={estilos.acaoSecundaria}
          onClick={buscar}
          disabled={buscando || !termo.trim()}
        >
          {buscando ? "Buscando…" : "Buscar"}
        </button>
      </div>

      {falha && (
        <p className={estilos.alerta} role="alert">
          {falha} Você continua podendo programar com os filmes do catálogo.
        </p>
      )}

      {resultados !== null && resultados.length === 0 && (
        <p className={estilos.buscaVazia}>
          Nada encontrado para “{buscado}”. Tente outro título.
        </p>
      )}

      {resultados !== null && resultados.length > 0 && (
        <ul className={estilos.resultados}>
          {resultados.map((item) => (
            <li key={item.tmdb_id} className={estilos.resultado}>
              <span className={estilos.resultadoTitulo}>
                {item.titulo}
                {item.ano ? ` (${item.ano})` : ""}
              </span>

              {item.ja_no_catalogo && (
                <span className={estilos.jaNoCatalogo}>Já no catálogo</span>
              )}

              <button
                type="button"
                className={estilos.acaoSecundaria}
                onClick={() => importar(item)}
                disabled={importando !== null}
              >
                {importando === item.tmdb_id ? "Trazendo…" : "Usar este"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
