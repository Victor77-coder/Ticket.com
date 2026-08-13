"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { SalaDoPainel } from "@/lib/types";

import { EstadoVazio } from "./EstadoVazio";
import estilos from "./programacao.module.css";

/**
 * As salas: listar, criar e trocar a capacidade.
 *
 * O CONTROLE DE CAPACIDADE FICA DESABILITADO COM EXPLICAÇÃO quando a sala tem
 * ocupação — nunca escondido. Um campo que some não ensina nada e faz a pessoa
 * procurar o que sumiu; um campo desabilitado ao lado de "3 lugares ocupados"
 * diz o que aconteceu e o que fazer.
 *
 * E ISSO NÃO É AUTORIZAÇÃO: `pode_trocar_capacidade` é dica de interface. O
 * `PATCH` revalida a ocupação no servidor e devolve `409` com a frase, e o
 * PROTECT de `Seat` é a rede embaixo dos dois (FR-020, FR-037).
 */

type Props = {
  salas: SalaDoPainel[];
};

function frase(valor: unknown): string {
  if (Array.isArray(valor)) return String(valor[0] ?? "");
  return String(valor ?? "");
}

export function PainelDeSalas({ salas: iniciais }: Props) {
  const router = useRouter();

  const [salas, setSalas] = useState(iniciais);
  const [nome, setNome] = useState("");
  const [capacidade, setCapacidade] = useState("");
  const [erros, setErros] = useState<{ nome?: string; capacidade?: string }>({});
  const [aviso, setAviso] = useState("");
  const [enviando, setEnviando] = useState(false);

  // Qual sala está com a capacidade em edição, e o valor digitado.
  const [editando, setEditando] = useState<number | null>(null);
  const [novaCapacidade, setNovaCapacidade] = useState("");

  async function criar(evento: React.FormEvent) {
    evento.preventDefault();
    setEnviando(true);
    setErros({});
    setAviso("");

    try {
      const resposta = await fetch("/api/programacao/salas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nome, capacidade }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        if (resposta.status === 400 && corpo) {
          setErros({
            nome: frase(corpo.nome) || undefined,
            capacidade: frase(corpo.capacidade) || undefined,
          });
          return;
        }
        setAviso(frase(corpo?.detail) || "Não foi possível criar a sala agora.");
        return;
      }

      setSalas((atual) => [...atual, corpo as SalaDoPainel]);
      setNome("");
      setCapacidade("");
      // A grade e o formulário de sessão leem as salas do servidor.
      router.refresh();
    } finally {
      setEnviando(false);
    }
  }

  async function trocarCapacidade(sala: SalaDoPainel) {
    setEnviando(true);
    setAviso("");

    try {
      const resposta = await fetch(`/api/programacao/salas/${sala.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ capacidade: novaCapacidade }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        // O `409` traz quantos lugares estão ocupados — a frase é do servidor,
        // e é ela que explica um controle que a tela já mostrava desabilitado.
        setAviso(
          frase(corpo?.detail) ||
            frase(corpo?.capacidade) ||
            "Não foi possível mudar a capacidade agora.",
        );
        return;
      }

      setSalas((atual) =>
        atual.map((item) => (item.id === sala.id ? (corpo as SalaDoPainel) : item)),
      );
      setEditando(null);
      router.refresh();
    } finally {
      setEnviando(false);
    }
  }

  return (
    <>
      {aviso && (
        <p className={estilos.alerta} role="alert">
          {aviso}
        </p>
      )}

      {salas.length === 0 ? (
        <EstadoVazio
          titulo="Nenhuma sala ainda"
          texto="Uma sala precisa de nome e capacidade. Os lugares nascem junto, com fileiras por letra e a acessibilidade no fundo."
        />
      ) : (
        <ul className={estilos.linhas}>
          {salas.map((sala) => (
            <li key={sala.id} className={estilos.linhaDeSala}>
              <span className={estilos.salaNome}>{sala.nome}</span>

              <span className={estilos.salaLugares}>
                {sala.lugares} lugares
                <span className={estilos.salaDetalhe}>
                  {sala.acessiveis} de acessibilidade
                </span>
              </span>

              {editando === sala.id ? (
                <span className={estilos.trocaDeCapacidade}>
                  <label className={estilos.campo}>
                    <span className={estilos.rotulo}>Nova capacidade</span>
                    <input
                      type="number"
                      min="1"
                      className={estilos.entrada}
                      value={novaCapacidade}
                      onChange={(e) => setNovaCapacidade(e.target.value)}
                    />
                  </label>
                  <button
                    type="button"
                    className={estilos.acao}
                    onClick={() => trocarCapacidade(sala)}
                    disabled={enviando}
                  >
                    Refazer lugares
                  </button>
                  <button
                    type="button"
                    className={estilos.acaoSecundaria}
                    onClick={() => setEditando(null)}
                  >
                    Cancelar
                  </button>
                </span>
              ) : (
                <span className={estilos.trocaDeCapacidade}>
                  <button
                    type="button"
                    className={estilos.acaoSecundaria}
                    disabled={!sala.pode_trocar_capacidade}
                    onClick={() => {
                      setEditando(sala.id);
                      setNovaCapacidade(String(sala.capacidade));
                    }}
                  >
                    Mudar capacidade
                  </button>
                  {!sala.pode_trocar_capacidade && (
                    <span className={estilos.salaDetalhe}>
                      {sala.ocupacao_viva}{" "}
                      {sala.ocupacao_viva === 1 ? "lugar ocupado" : "lugares ocupados"}
                    </span>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}

      <form className={estilos.formulario} onSubmit={criar}>
        <h2 className={estilos.buscaTitulo}>Criar sala</h2>

        <label className={estilos.campo}>
          <span className={estilos.rotulo}>Nome</span>
          <input
            className={estilos.entrada}
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            aria-invalid={erros.nome ? true : undefined}
            aria-describedby={erros.nome ? "erro-nome" : undefined}
          />
          {erros.nome && (
            <span id="erro-nome" className={estilos.erroDeCampo}>
              {erros.nome}
            </span>
          )}
        </label>

        <label className={estilos.campo}>
          <span className={estilos.rotulo}>Capacidade</span>
          <input
            type="number"
            min="1"
            className={estilos.entrada}
            value={capacidade}
            onChange={(e) => setCapacidade(e.target.value)}
            aria-invalid={erros.capacidade ? true : undefined}
            aria-describedby={erros.capacidade ? "erro-capacidade" : undefined}
          />
          {erros.capacidade && (
            <span id="erro-capacidade" className={estilos.erroDeCampo}>
              {erros.capacidade}
            </span>
          )}
        </label>

        <div className={estilos.acoes}>
          <button type="submit" className={estilos.acao} disabled={enviando}>
            {enviando ? "Criando…" : "Criar sala"}
          </button>
        </div>
      </form>
    </>
  );
}
