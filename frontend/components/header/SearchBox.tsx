"use client";

import { useRouter } from "next/navigation";
import { useId, useRef, useState } from "react";

import { useSugestoes } from "@/lib/search-client";
import { SearchSuggestions } from "./SearchSuggestions";
import styles from "./header.module.css";

const TERMO_MAX_CHARS = 80;

/**
 * Busca de filmes do cabeçalho.
 *
 * Combobox do padrão WAI-ARIA 1.2 escrito à mão (R4). O foco do DOM nunca sai
 * do campo: `aria-activedescendant` aponta para a opção destacada, o que
 * permite continuar digitando enquanto se navega pela lista.
 */
export function SearchBox() {
  const router = useRouter();
  const prefixo = useId();
  const idLista = `${prefixo}-lista`;
  const idOpcao = (indice: number) => `${prefixo}-opcao-${indice}`;

  const [termo, setTermo] = useState("");
  const [indiceAtivo, setIndiceAtivo] = useState(-1);
  const [fechadaManualmente, setFechadaManualmente] = useState(false);

  const campoRef = useRef<HTMLInputElement>(null);
  const estado = useSugestoes(termo);

  const aberta = !fechadaManualmente && estado.situacao !== "ocioso";
  const opcoes = estado.situacao === "com-resultados" ? estado.sugestoes : [];

  function alterar(valor: string) {
    setTermo(valor);
    setIndiceAtivo(-1);
    setFechadaManualmente(false);
  }

  function escolher(caminho: string) {
    setFechadaManualmente(true);
    setIndiceAtivo(-1);
    router.push(caminho);
  }

  function mover(passo: number) {
    if (opcoes.length === 0) return;
    setIndiceAtivo((atual) => {
      const proximo = atual + passo;
      if (proximo < 0) return opcoes.length - 1;
      if (proximo >= opcoes.length) return 0;
      return proximo;
    });
  }

  function aoTeclar(evento: React.KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "ArrowDown") {
      evento.preventDefault();
      mover(1);
    } else if (evento.key === "ArrowUp") {
      evento.preventDefault();
      mover(-1);
    } else if (evento.key === "Enter") {
      const escolhida = opcoes[indiceAtivo];
      if (escolhida) {
        evento.preventDefault();
        escolher(escolhida.movie_path);
      }
    } else if (evento.key === "Escape") {
      evento.preventDefault();
      setFechadaManualmente(true);
      setIndiceAtivo(-1);
      // O foco permanece no campo: fechar a lista não é sair da busca.
      campoRef.current?.focus();
    }
  }

  function aoPerderFoco(evento: React.FocusEvent<HTMLDivElement>) {
    // Só fecha quando o foco sai da busca inteira. Sem esta guarda, mover o
    // foco para dentro da própria lista já a fecharia.
    if (evento.currentTarget.contains(evento.relatedTarget as Node | null)) return;
    setFechadaManualmente(true);
    setIndiceAtivo(-1);
  }

  return (
    <div className={styles.busca} onBlur={aoPerderFoco}>
      <label className={styles.buscaRotulo} htmlFor={`${prefixo}-campo`}>
        Buscar filme pelo nome
      </label>

      <input
        ref={campoRef}
        id={`${prefixo}-campo`}
        className={styles.buscaCampo}
        type="text"
        role="combobox"
        autoComplete="off"
        maxLength={TERMO_MAX_CHARS}
        placeholder="Buscar filme pelo nome"
        value={termo}
        aria-expanded={aberta && opcoes.length > 0}
        aria-controls={idLista}
        aria-autocomplete="list"
        aria-activedescendant={indiceAtivo >= 0 ? idOpcao(indiceAtivo) : undefined}
        onChange={(evento) => alterar(evento.target.value)}
        onKeyDown={aoTeclar}
        onFocus={() => setFechadaManualmente(false)}
      />

      {aberta && (
        <SearchSuggestions
          estado={estado}
          idLista={idLista}
          idOpcao={idOpcao}
          indiceAtivo={indiceAtivo}
          onEscolher={escolher}
          onApontar={setIndiceAtivo}
        />
      )}

      {/* Anuncia só quando a busca conclui — anunciar a cada tecla inundaria
       * o leitor de tela (FR-027). */}
      <p className={styles.apenasLeitorDeTela} role="status" aria-live="polite">
        {estado.situacao === "com-resultados" &&
          `${estado.sugestoes.length} ${estado.sugestoes.length === 1 ? "filme encontrado" : "filmes encontrados"} para ${estado.termoAplicado}.`}
        {estado.situacao === "sem-resultados" &&
          `Nenhum filme encontrado para ${estado.termoAplicado}.`}
      </p>
    </div>
  );
}
