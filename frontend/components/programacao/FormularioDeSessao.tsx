"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { FilmeDoPainel, SalaDoPainel } from "@/lib/types";

import estilos from "./programacao.module.css";

/**
 * Programar uma sessão: filme, sala, horário, preço.
 *
 * DUAS AÇÕES EXPLÍCITAS, e não uma caixa "publicar" ao lado de um botão
 * "salvar": rascunho e publicada são desfechos diferentes, e o segundo coloca
 * algo à venda. Uma caixa marcada por engano publica; dois botões obrigam a
 * escolher qual das duas coisas se está fazendo (FR-022).
 *
 * AS RECUSAS SÃO DO SERVIDOR, E CHEGAM PRONTAS. Este componente não decide se
 * o horário é futuro nem se a sala tem lugares — ele exibe o que o Django
 * respondeu, campo a campo. Validar aqui daria a impressão de garantia e
 * criaria a segunda redação de cada frase; o conflito de (sala, horário), em
 * particular, é impossível de saber no navegador.
 */

type Props = {
  filmes: FilmeDoPainel[];
  salas: SalaDoPainel[];
  /**
   * O filme escolhido é CONTROLADO de fora porque a busca no TMDb, ao lado,
   * precisa selecioná-lo depois de importar. Estado interno faria a pessoa
   * trazer um filme e ter de procurá-lo na lista logo em seguida.
   */
  filme: string;
  onFilmeChange: (valor: string) => void;
};

type ErrosDeCampo = Partial<Record<"filme" | "sala" | "inicio" | "preco", string>>;

function frase(valor: unknown): string {
  // O DRF devolve lista por campo; o corpo de conflito devolve string. As duas
  // formas chegam aqui, e a tela mostra a primeira frase de qualquer uma.
  if (Array.isArray(valor)) return String(valor[0] ?? "");
  return String(valor ?? "");
}

export function FormularioDeSessao({ filmes, salas, filme, onFilmeChange }: Props) {
  const router = useRouter();

  const [sala, setSala] = useState(salas[0] ? String(salas[0].id) : "");
  const [inicio, setInicio] = useState("");
  const [preco, setPreco] = useState("");

  const [erros, setErros] = useState<ErrosDeCampo>({});
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(publicar: boolean) {
    setEnviando(true);
    setErros({});
    setAviso("");

    try {
      const resposta = await fetch("/api/programacao/sessoes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filme, sala, inicio, preco, publicar }),
      });

      if (resposta.ok) {
        // `refresh` antes de navegar: a grade é renderizada no servidor, e sem
        // ele a sessão recém-criada não apareceria até um recarregamento.
        router.refresh();
        router.push("/programacao");
        return;
      }

      const corpo = await resposta.json().catch(() => null);

      if (resposta.status === 400 && corpo) {
        setErros({
          filme: frase(corpo.filme) || undefined,
          sala: frase(corpo.sala) || undefined,
          inicio: frase(corpo.inicio) || undefined,
          preco: frase(corpo.preco) || undefined,
        });
        setAviso(frase(corpo.detail));
        return;
      }

      setAviso(
        frase(corpo?.detail) || "Não foi possível programar a sessão agora.",
      );
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form
      className={estilos.formulario}
      onSubmit={(evento) => {
        evento.preventDefault();
        enviar(true);
      }}
    >
      {aviso && (
        <p className={estilos.alerta} role="alert">
          {aviso}
        </p>
      )}

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Filme</span>
        <select
          className={estilos.entrada}
          value={filme}
          onChange={(e) => onFilmeChange(e.target.value)}
          aria-invalid={erros.filme ? true : undefined}
          aria-describedby={erros.filme ? "erro-filme" : undefined}
        >
          <option value="">Escolha um filme</option>
          {filmes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.titulo}
              {item.ano ? ` (${item.ano})` : ""}
            </option>
          ))}
        </select>
        {erros.filme && (
          <span id="erro-filme" className={estilos.erroDeCampo}>
            {erros.filme}
          </span>
        )}
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Sala</span>
        <select
          className={estilos.entrada}
          value={sala}
          onChange={(e) => setSala(e.target.value)}
          aria-invalid={erros.sala ? true : undefined}
          aria-describedby={erros.sala ? "erro-sala" : undefined}
        >
          {salas.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nome} — {item.lugares} lugares
            </option>
          ))}
        </select>
        {erros.sala && (
          <span id="erro-sala" className={estilos.erroDeCampo}>
            {erros.sala}
          </span>
        )}
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Data e hora</span>
        <input
          type="datetime-local"
          className={estilos.entrada}
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
          aria-invalid={erros.inicio ? true : undefined}
          aria-describedby={erros.inicio ? "erro-inicio" : undefined}
        />
        {erros.inicio && (
          <span id="erro-inicio" className={estilos.erroDeCampo}>
            {erros.inicio}
          </span>
        )}
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Preço</span>
        <input
          type="number"
          inputMode="decimal"
          step="0.01"
          min="0"
          className={estilos.entrada}
          value={preco}
          onChange={(e) => setPreco(e.target.value)}
          aria-invalid={erros.preco ? true : undefined}
          aria-describedby={erros.preco ? "erro-preco" : undefined}
        />
        {erros.preco && (
          <span id="erro-preco" className={estilos.erroDeCampo}>
            {erros.preco}
          </span>
        )}
      </label>

      <div className={estilos.acoes}>
        <button type="submit" className={estilos.acao} disabled={enviando}>
          {enviando ? "Enviando…" : "Publicar"}
        </button>
        <button
          type="button"
          className={estilos.acaoSecundaria}
          onClick={() => enviar(false)}
          disabled={enviando}
        >
          Salvar rascunho
        </button>
      </div>
    </form>
  );
}
