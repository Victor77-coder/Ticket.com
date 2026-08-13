"use client";

import type { Screening } from "@/lib/types";

import estilos from "./sessao.module.css";

/**
 * Trocar de horário sem fechar o painel.
 *
 * As ações do cartão abrem sobre o primeiro horário disponível; quem quer
 * comparar dois horários da mesma sala não deveria precisar fechar, escolher
 * outro e reabrir — comparar é justamente o motivo de o painel existir.
 *
 * Some quando há um horário só: um seletor de uma opção é ruído com aparência
 * de escolha.
 */

type Props = {
  horarios: Screening[];
  atual: Screening;
  aoTrocar: (sessao: Screening) => void;
};

function formatarHora(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function SeletorDeHorario({ horarios, atual, aoTrocar }: Props) {
  if (horarios.length < 2) {
    return <p className={estilos.horarioUnico}>{formatarHora(atual.starts_at)}</p>;
  }

  return (
    <div className={estilos.seletor} role="group" aria-label="Horário">
      {horarios.map((sessao) => {
        const ativo = sessao.id === atual.id;
        return (
          <button
            key={sessao.id}
            type="button"
            className={ativo ? `${estilos.opcao} ${estilos.opcaoAtiva}` : estilos.opcao}
            aria-pressed={ativo}
            onClick={() => aoTrocar(sessao)}
          >
            {formatarHora(sessao.starts_at)}
          </button>
        );
      })}
    </div>
  );
}
