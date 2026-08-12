"use client";

import { useState } from "react";

import { TrailerFrame } from "@/components/highlights/TrailerFrame";
import type { MovieDetail, TrailerDoFilme } from "@/lib/types";

import GradeDoDia from "./GradeDoDia";
import styles from "./filme.module.css";

type Secao = "sessoes" | "sobre" | "trailers";

function formatarDuracao(minutos: number | null) {
  if (!minutos) return null;
  const horas = Math.floor(minutos / 60);
  const resto = minutos % 60;
  return resto === 0 ? `${horas}h` : `${horas}h${String(resto).padStart(2, "0")}`;
}

function trailerDaHome(trailer: TrailerDoFilme) {
  return { provider: "youtube" as const, external_key: trailer.external_key };
}

export default function FilmeCliente({ filme }: { filme: MovieDetail }) {
  const [secao, setSecao] = useState<Secao>("sessoes");
  const [reproduzindo, setReproduzindo] = useState<TrailerDoFilme | null>(null);

  const duracao = formatarDuracao(filme.runtime_minutes);

  return (
    <div className={styles.corpo}>
      <div className={styles.abas} role="tablist" aria-label="Seções do filme">
        {(
          [
            ["sessoes", "Sessões"],
            ["sobre", "Sobre"],
            ["trailers", "Trailers"],
          ] as const
        ).map(([id, rotulo]) => {
          const ativa = secao === id;
          return (
            <button
              key={id}
              type="button"
              role="tab"
              id={`aba-${id}`}
              aria-selected={ativa}
              aria-controls={`painel-${id}`}
              className={ativa ? `${styles.aba} ${styles.abaAtiva}` : styles.aba}
              onClick={() => {
                setSecao(id);
                setReproduzindo(null);
              }}
            >
              {rotulo}
            </button>
          );
        })}
      </div>

      <div
        role="tabpanel"
        id="painel-sessoes"
        aria-labelledby="aba-sessoes"
        hidden={secao !== "sessoes"}
      >
        <GradeDoDia sessoes={filme.screenings} releaseDate={filme.release_date} />
      </div>

      <div
        role="tabpanel"
        id="painel-sobre"
        aria-labelledby="aba-sobre"
        hidden={secao !== "sobre"}
      >
        <div className={styles.sobre}>
          {filme.synopsis ? (
            <p className={styles.sinopse}>{filme.synopsis}</p>
          ) : null}
          <dl className={styles.ficha}>
            {filme.certification_br ? (
              <div>
                <dt>Classificação</dt>
                <dd>{filme.certification_br}</dd>
              </div>
            ) : null}
            {duracao ? (
              <div>
                <dt>Duração</dt>
                <dd>{duracao}</dd>
              </div>
            ) : null}
            {filme.genres.length > 0 ? (
              <div>
                <dt>Gênero</dt>
                <dd>{filme.genres.join(", ")}</dd>
              </div>
            ) : null}
          </dl>
        </div>
      </div>

      <div
        role="tabpanel"
        id="painel-trailers"
        aria-labelledby="aba-trailers"
        hidden={secao !== "trailers"}
      >
        {filme.trailers.length === 0 ? (
          <div className={styles.vazio}>
            <p className={styles.vazioTexto}>
              Este filme ainda não tem trailer disponível.
            </p>
          </div>
        ) : (
          <ul className={styles.listaTrailers}>
            {filme.trailers.map((trailer) => {
              const aberto = reproduzindo?.external_key === trailer.external_key;
              const rotulo = trailer.name.trim() || (trailer.kind === "teaser" ? "Teaser" : "Trailer");

              return (
                <li key={`${trailer.provider}-${trailer.external_key}`} className={styles.itemTrailer}>
                  <p className={styles.trailerNome}>{rotulo}</p>
                  {aberto ? (
                    <div className={styles.palcoTrailer}>
                      <TrailerFrame
                        trailer={trailerDaHome(trailer)}
                        tituloDoFilme={filme.title}
                        onFechar={() => setReproduzindo(null)}
                      />
                    </div>
                  ) : (
                    <button
                      type="button"
                      className={styles.reproduzir}
                      onClick={() => setReproduzindo(trailer)}
                    >
                      Reproduzir {rotulo}
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
