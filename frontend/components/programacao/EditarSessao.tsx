"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { FilmeDoPainel, SalaDoPainel, SessaoDaGrade } from "@/lib/types";

import estilos from "./programacao.module.css";

/**
 * Corrigir um rascunho — os mesmos quatro campos, já preenchidos.
 *
 * NÃO PUBLICA. Depois de salvar, a sessão continua em rascunho e a pessoa volta
 * à grade, onde o botão de publicar espera com as pré-condições dele (FR-023).
 * Um "salvar e publicar" aqui esconderia essas pré-condições dentro de um
 * formulário.
 *
 * O horário chega em ISO com fuso e o campo `datetime-local` só entende
 * `YYYY-MM-DDTHH:mm` no relógio local — a conversão é feita na entrada e o
 * servidor reinterpreta no fuso da aplicação, que é o mesmo que o organizador
 * enxerga na grade.
 */

type Props = {
  sessao: SessaoDaGrade;
  filmes: FilmeDoPainel[];
  salas: SalaDoPainel[];
};

function paraCampoLocal(iso: string): string {
  const quando = new Date(iso);
  const dois = (n: number) => String(n).padStart(2, "0");
  return (
    `${quando.getFullYear()}-${dois(quando.getMonth() + 1)}-${dois(quando.getDate())}` +
    `T${dois(quando.getHours())}:${dois(quando.getMinutes())}`
  );
}

function frase(valor: unknown): string {
  if (Array.isArray(valor)) return String(valor[0] ?? "");
  return String(valor ?? "");
}

export function EditarSessao({ sessao, filmes, salas }: Props) {
  const router = useRouter();

  const [filme, setFilme] = useState(String(sessao.filme.id));
  const [sala, setSala] = useState(String(sessao.sala.id));
  const [inicio, setInicio] = useState(paraCampoLocal(sessao.inicio));
  const [preco, setPreco] = useState(sessao.preco);

  const [erros, setErros] = useState<Record<string, string>>({});
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function salvar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErros({});
    setAviso("");

    try {
      const resposta = await fetch(`/api/programacao/sessoes/${sessao.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filme, sala, inicio, preco }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (resposta.ok) {
        router.refresh();
        router.push("/programacao");
        return;
      }

      if (resposta.status === 400 && corpo) {
        setErros({
          filme: frase(corpo.filme),
          sala: frase(corpo.sala),
          inicio: frase(corpo.inicio),
          preco: frase(corpo.preco),
        });
        return;
      }

      // `409` — conflito de horário, ou a sessão deixou de ser rascunho entre
      // a leitura da página e o envio. As duas frases vêm do servidor.
      setAviso(frase(corpo?.detail) || "Não foi possível salvar agora.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <form className={estilos.formulario} onSubmit={salvar}>
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
          onChange={(e) => setFilme(e.target.value)}
          aria-invalid={erros.filme ? true : undefined}
        >
          {filmes.map((item) => (
            <option key={item.id} value={item.id}>
              {item.titulo}
            </option>
          ))}
        </select>
        {erros.filme && <span className={estilos.erroDeCampo}>{erros.filme}</span>}
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Sala</span>
        <select
          className={estilos.entrada}
          value={sala}
          onChange={(e) => setSala(e.target.value)}
          aria-invalid={erros.sala ? true : undefined}
        >
          {salas.map((item) => (
            <option key={item.id} value={item.id}>
              {item.nome} — {item.lugares} lugares
            </option>
          ))}
        </select>
        {erros.sala && <span className={estilos.erroDeCampo}>{erros.sala}</span>}
      </label>

      <label className={estilos.campo}>
        <span className={estilos.rotulo}>Data e hora</span>
        <input
          type="datetime-local"
          className={estilos.entrada}
          value={inicio}
          onChange={(e) => setInicio(e.target.value)}
          aria-invalid={erros.inicio ? true : undefined}
        />
        {erros.inicio && <span className={estilos.erroDeCampo}>{erros.inicio}</span>}
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
        />
        {erros.preco && <span className={estilos.erroDeCampo}>{erros.preco}</span>}
      </label>

      <div className={estilos.acoes}>
        <button type="submit" className={estilos.acao} disabled={enviando}>
          {enviando ? "Salvando…" : "Salvar rascunho"}
        </button>
        <span className={estilos.salaDetalhe}>
          Salvar não publica — a sessão continua em rascunho.
        </span>
      </div>
    </form>
  );
}
