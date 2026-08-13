"use client";

import Link from "next/link";
import { useState } from "react";

import type { Screening } from "@/lib/types";

import PainelDeAssentos from "./PainelDeAssentos";
import PainelDePrecos from "./PainelDePrecos";
import estilos from "./sessao.module.css";

/**
 * Uma sala, seus horários, e as duas ações de leitura.
 *
 * ATÉ A 013 A GRADE ERA UMA LISTA de horários sob um `<h3>`. O cartão fecha o
 * grupo: o que é da sala fica dentro dela, e as ações que valem para aquela sala
 * ficam no topo dela — não numa barra da página, onde valeriam para tudo e para
 * nada.
 *
 * O CABEÇALHO É A SALA, e não nome e endereço de cinema como na referência que
 * originou a feature. Esta plataforma modela UM cinema; a sala é a menor unidade
 * que distingue uma sessão de outra. Um campo de local só existe junto com o
 * conceito de praça, pendente desde a 002 — e um campo que teria o mesmo valor
 * em todas as linhas é ruído, não informação.
 *
 * AS AÇÕES OPERAM SOBRE O PRIMEIRO HORÁRIO DISPONÍVEL do cartão, e o painel
 * aberto oferece os demais. A alternativa — uma dupla de ações por horário —
 * multiplicaria três alvos por doze horários e devolveria a grade à condição de
 * formulário, que é o que a recomposição da 012 tirou dela.
 *
 * M6 mora aqui: um estado só guarda QUAL painel está aberto, então abrir um
 * fecha o outro por construção, sem ninguém precisar lembrar.
 */

type Props = {
  sala: string;
  horarios: Screening[];
};

type PainelAberto = "assentos" | "precos" | null;

const FUSO = "America/Sao_Paulo";

function formatarHora(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function formatarHorarioAcessivel(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

/** Um assento de poltrona, desenhado — não é ícone genérico de biblioteca. */
function IconeDeAssento() {
  return (
    <svg className={estilos.acaoIcone} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path
        d="M4 6.5V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2.5"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path
        d="M3 7h10a1 1 0 0 1 1 1v3H2V8a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M3.5 11v2M12.5 11v2" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

function IconeDePreco() {
  return (
    <svg className={estilos.acaoIcone} viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M8 4.5v7M9.9 6.2a2 2 0 0 0-3.6 1c0 1.6 3.4 1 3.4 2.6a2 2 0 0 1-3.6 1"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export default function CartaoDeSessao({ sala, horarios }: Props) {
  const [painel, setPainel] = useState<PainelAberto>(null);

  // O primeiro DISPONÍVEL, não o primeiro da lista: abrir a prévia num horário
  // esgotado seria mostrar uma sala cheia como resposta a "quero ver a lotação".
  const referencia = horarios.find((h) => h.has_available_seats) ?? horarios[0];
  const quando = formatarHorarioAcessivel(referencia.starts_at);

  return (
    <section className={estilos.cartao} aria-label={sala}>
      <div className={estilos.cabecalho}>
        <h3 className={estilos.sala}>{sala}</h3>

        <div className={estilos.acoes}>
          <button
            type="button"
            className={estilos.acao}
            onClick={() => setPainel("assentos")}
            aria-label={`Assentos — ${sala}, ${quando}`}
          >
            <IconeDeAssento />
            Assentos
          </button>
          <button
            type="button"
            className={estilos.acao}
            onClick={() => setPainel("precos")}
            aria-label={`Preços — ${sala}, ${quando}`}
          >
            <IconeDePreco />
            Preços
          </button>
        </div>
      </div>

      <hr className={estilos.regua} />

      <ul className={estilos.horarios}>
        {horarios.map((sessao) => {
          const hora = formatarHora(sessao.starts_at);
          // SEM PREÇO NO ALVO (014). Ele esteve aqui por algumas horas e saiu:
          // repetir em doze chips o que a ação "Preços" já mostra transforma a
          // grade num mural de números, e o preço da sessão raramente varia
          // dentro da mesma sala. O alvo volta a ser sobre HORÁRIO.
          const acessivel = `Escolher lugares — ${formatarHorarioAcessivel(sessao.starts_at)}, ${sessao.room_name}`;

          return (
            <li key={sessao.id}>
              {sessao.has_available_seats ? (
                <Link
                  href={`/sessoes/${sessao.id}`}
                  className={estilos.horario}
                  aria-label={acessivel}
                >
                  {hora}
                </Link>
              ) : (
                <span className={estilos.horarioEsgotado}>
                  <span className={estilos.horarioHora}>{hora}</span>
                  <span>Esgotada</span>
                </span>
              )}
            </li>
          );
        })}
      </ul>

      <PainelDeAssentos
        aberta={painel === "assentos"}
        sala={sala}
        horarios={horarios}
        inicial={referencia}
        aoFechar={() => setPainel(null)}
      />
      <PainelDePrecos
        aberta={painel === "precos"}
        sala={sala}
        horarios={horarios}
        inicial={referencia}
        aoFechar={() => setPainel(null)}
      />
    </section>
  );
}
