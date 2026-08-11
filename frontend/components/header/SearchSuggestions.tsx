"use client";

import Image from "next/image";

import type { EstadoBusca } from "@/lib/search-client";
import styles from "./header.module.css";

type Props = {
  estado: EstadoBusca;
  idLista: string;
  idOpcao: (indice: number) => string;
  indiceAtivo: number;
  onEscolher: (caminho: string) => void;
  onApontar: (indice: number) => void;
};

/**
 * Painel de sugestões da busca.
 *
 * Os quatro estados são visualmente distintos (FR-012, FR-013, SC-008).
 * `sem-resultados` NUNCA é derivado de "lista vazia": `buscando` também
 * produz lista vazia, e confundir os dois é o bug que o caso de borda
 * "busca lenta" descreve.
 */
export function SearchSuggestions({
  estado,
  idLista,
  idOpcao,
  indiceAtivo,
  onEscolher,
  onApontar,
}: Props) {
  if (estado.situacao === "ocioso") return null;

  if (estado.situacao === "buscando") {
    return (
      <div className={styles.painel}>
        <p className={styles.painelAviso}>Buscando filmes…</p>
      </div>
    );
  }

  if (estado.situacao === "erro") {
    return (
      <div className={styles.painel}>
        <p className={`${styles.painelAviso} ${styles.painelErro}`} role="alert">
          {estado.mensagemErro}
        </p>
      </div>
    );
  }

  if (estado.situacao === "sem-resultados") {
    return (
      <div className={styles.painel}>
        <p className={styles.painelAviso}>
          Nenhum filme encontrado para <strong>{estado.termoAplicado}</strong>.
        </p>
        <p className={styles.painelDica}>
          Tente parte do título, sem precisar de acento — ou veja o que está em cartaz na página
          inicial.
        </p>
      </div>
    );
  }

  return (
    <div className={styles.painel}>
      <ul className={styles.lista} id={idLista} role="listbox" aria-label="Filmes encontrados">
        {estado.sugestoes.map((sugestao, indice) => (
          <li
            key={sugestao.slug}
            id={idOpcao(indice)}
            role="option"
            aria-selected={indice === indiceAtivo}
            className={`${styles.opcao} ${indice === indiceAtivo ? styles.opcaoAtiva : ""}`}
            // `onMouseDown` e não `onClick`: o clique só completa depois do
            // blur, que fecharia a lista antes de o clique registrar.
            onMouseDown={(evento) => {
              evento.preventDefault();
              onEscolher(sugestao.movie_path);
            }}
            onMouseEnter={() => onApontar(indice)}
          >
            {sugestao.poster_url ? (
              <Image
                src={sugestao.poster_url}
                alt=""
                width={36}
                height={54}
                className={styles.opcaoArte}
              />
            ) : (
              <span className={styles.opcaoArteVazia} aria-hidden="true" />
            )}
            <span className={styles.opcaoTexto}>
              <span className={styles.opcaoTitulo}>{sugestao.title}</span>
              {sugestao.year !== null && <span className={styles.opcaoAno}>{sugestao.year}</span>}
            </span>
          </li>
        ))}
      </ul>

      {estado.truncado && (
        <p className={styles.painelDica}>
          Há mais resultados para <strong>{estado.termoAplicado}</strong>. Escreva mais um pedaço
          do título para afinar a busca.
        </p>
      )}
    </div>
  );
}
