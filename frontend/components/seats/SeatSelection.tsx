"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { totalPrevisto } from "@/lib/meia";
import type { Assento, LugarReservado, MapaSessao, Reserva } from "@/lib/types";

import ReservationPanel from "./ReservationPanel";
import SeatMap from "./SeatMap";
import SelectionSummary from "./SelectionSummary";
import estilos from "./seats.module.css";

/**
 * Guarda a seleção, confirma a reserva e coordena mapa e resumo.
 *
 * A seleção vive só aqui, no navegador: o servidor não sabe o que alguém
 * marcou até a confirmação virar reserva. É por isso que `situacao` no
 * contrato só tem "livre" e "tomado" — "selecionado" não é estado do
 * sistema, é estado de quem está escolhendo.
 */

export type SeatSelectionProps = {
  mapa: MapaSessao;
};

/** Gera a chave de idempotência. `crypto.randomUUID` falta em ambiente antigo. */
function novaChave() {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function formatarHorario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function SeatSelection({ mapa }: SeatSelectionProps) {
  const router = useRouter();

  const [selecionados, setSelecionados] = useState<LugarReservado[]>([]);
  const [ids, setIds] = useState<Set<number>>(new Set());
  // Quais lugares saem como meia. CONJUNTO, e não campo em cada item: o padrão
  // é inteira, e um conjunto vazio já significa "todos inteira" sem que nada
  // precise ser preenchido. É a mesma forma que o corpo da reserva usa.
  const [meias, setMeias] = useState<Set<number>>(new Set());
  const [aviso, setAviso] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [reserva, setReserva] = useState<Reserva | null>(null);

  // A chave é gerada UMA VEZ por seleção, não por clique. Uma chave por
  // clique não seria idempotência nenhuma: cada reenvio traria chave nova e
  // criaria reserva nova, que é exatamente o que ela existe para impedir.
  //
  // Ela só é renovada quando a seleção recomeça do zero — depois de uma
  // reserva criada, ou depois de um 409 que desfez a escolha.
  const [chave, setChave] = useState(novaChave);

  function alternar(assento: Assento, fileira: string) {
    setAviso(null);

    if (ids.has(assento.id)) {
      const proximos = new Set(ids);
      proximos.delete(assento.id);
      setIds(proximos);
      // O tipo morre junto com a escolha do lugar: uma meia pendurada num
      // assento que saiu da seleção reapareceria se ele fosse escolhido de novo.
      setMeias((atual) => {
        const restantes = new Set(atual);
        restantes.delete(assento.id);
        return restantes;
      });
      setSelecionados((atual) =>
        atual.filter((l) => !(l.fileira === fileira && l.numero === assento.numero)),
      );
      return;
    }

    if (ids.size >= mapa.limite_por_reserva) {
      setAviso(
        `São no máximo ${mapa.limite_por_reserva} lugares por reserva. ` +
          "Desmarque um para escolher outro.",
      );
      return;
    }

    setIds(new Set(ids).add(assento.id));
    setSelecionados((atual) => [...atual, { id: assento.id, fileira, numero: assento.numero }]);
  }

  /** Marca ou desmarca a meia de UM lugar já escolhido. */
  function alternarMeia(id: number) {
    setMeias((atual) => {
      const proximos = new Set(atual);
      if (proximos.has(id)) proximos.delete(id);
      else proximos.add(id);
      return proximos;
    });
  }

  async function confirmar() {
    if (ids.size === 0) {
      setAviso("Escolha ao menos um lugar.");
      return;
    }

    setEnviando(true);
    setAviso(null);

    try {
      const resposta = await fetch("/api/reservar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sessao: mapa.id,
          assentos: [...ids],
          meias: [...meias],
          chave_idempotencia: chave,
        }),
      });

      const corpo = await resposta.json().catch(() => null);

      if (resposta.status === 401) {
        // Conduzir à entrada, e voltar para este mapa ao concluir (FR-026).
        router.push(`/entrar?next=${encodeURIComponent(`/sessoes/${mapa.id}`)}`);
        return;
      }

      if (!resposta.ok) {
        setAviso(corpo?.detail ?? "Não foi possível reservar agora. Tente de novo.");
        if (resposta.status === 409) {
          // O mapa mudou embaixo da seleção: recarregar é o que impede a
          // pessoa de tentar de novo contra um estado que já não existe.
          setIds(new Set());
          setSelecionados([]);
          setMeias(new Set());
          setChave(novaChave());
          router.refresh();
        }
        return;
      }

      setReserva(corpo as Reserva);
    } catch {
      setAviso("Não foi possível falar com o servidor. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  if (mapa.esgotada) {
    return (
      <div className={estilos.confirmada}>
        <p className={estilos.confirmadaTitulo}>Esta sessão esgotou</p>
        <p className={estilos.confirmadaLugares}>
          Todos os lugares desta sessão já foram reservados. Escolha outro horário na
          página do filme.
        </p>
      </div>
    );
  }

  // PREVISÃO, e o servidor é quem decide. Até a 014 esta linha era a terceira
  // cópia de `preço × quantidade`; agora ela consome a mesma derivação que o
  // back-end usa, espelhada em `lib/meia`. Nada daqui é enviado — o corpo da
  // reserva manda quais lugares são meia, nunca quanto eles custam.
  const total = totalPrevisto(
    mapa.preco,
    [...ids].map((id) => (meias.has(id) ? "meia" : "inteira")),
  );

  return (
    <div className={estilos.compra} data-layout="compra">
      <div className={estilos.mapaColuna}>
        <SeatMap
          fileiras={mapa.fileiras}
          selecionados={ids}
          onAlternar={reserva ? () => {} : alternar}
        />
      </div>
      <aside className={estilos.resumoColuna}>
        {reserva ? (
          <ReservationPanel reserva={reserva} />
        ) : (
          <SelectionSummary
            filme={mapa.filme.titulo}
            horario={formatarHorario(mapa.inicio)}
            sala={mapa.sala.nome}
            lugares={selecionados}
            precoUnitario={mapa.preco}
            meias={meias}
            onAlternarMeia={alternarMeia}
            total={total}
            limite={mapa.limite_por_reserva}
            aviso={aviso}
            enviando={enviando}
            onConfirmar={confirmar}
          />
        )}
      </aside>
    </div>
  );
}
