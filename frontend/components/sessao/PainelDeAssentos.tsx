"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { MapaSessao, Screening } from "@/lib/types";

import SeletorDeHorario from "./SeletorDeHorario";
import Sobreposicao from "./Sobreposicao";
import estilos from "./sessao.module.css";

/**
 * A lotação, antes de escolher o horário.
 *
 * É PRÉVIA, E ISSO É O CONTRATO INTEIRO (FR-007). Nenhum assento aqui é botão,
 * link ou campo. Selecionar continua acontecendo no mapa da 007, e criar um
 * segundo caminho de reserva seria duplicar a regra mais cara do projeto — a que
 * `UNIQUE(sessão, assento)` protege.
 *
 * A SITUAÇÃO É DESENHADA COMO VEM. O painel não recalcula quem ocupa: essa regra
 * é `Reservation.OCUPANDO` e tem dono desde a 008. Aqui só se lê `livre` ou
 * `tomado`.
 *
 * É UM RETRATO, NÃO UMA TRANSMISSÃO. O painel mostra o estado do instante em que
 * abriu e não se atualiza sozinho — ocupação em tempo real é item separado da
 * etapa 6 da constitution. A verdade continua sendo a reserva: quem seguir para
 * o mapa e tentar um lugar já vendido recebe a recusa que a 007 já dá.
 */

type Props = {
  aberta: boolean;
  sala: string;
  horarios: Screening[];
  inicial: Screening;
  aoFechar: () => void;
};

type Estado =
  | { fase: "carregando" }
  | { fase: "pronto"; mapa: MapaSessao }
  | { fase: "erro"; mensagem: string };

export default function PainelDeAssentos({ aberta, sala, horarios, inicial, aoFechar }: Props) {
  const [sessao, setSessao] = useState(inicial);
  const [estado, setEstado] = useState<Estado>({ fase: "carregando" });

  useEffect(() => {
    if (aberta) setSessao(inicial);
  }, [aberta, inicial]);

  useEffect(() => {
    if (!aberta) return;

    let vivo = true;
    setEstado({ fase: "carregando" });

    fetch(`/api/mapa/${sessao.id}`, { cache: "no-store" })
      .then(async (resposta) => {
        const corpo = await resposta.json().catch(() => null);
        if (!vivo) return;
        if (!resposta.ok) {
          setEstado({
            fase: "erro",
            mensagem:
              corpo?.detail ??
              "Não foi possível carregar a lotação desta sessão. Tente de novo.",
          });
          return;
        }
        setEstado({ fase: "pronto", mapa: corpo as MapaSessao });
      })
      .catch(() => {
        if (!vivo) return;
        setEstado({
          fase: "erro",
          mensagem: "Não foi possível falar com o servidor. Verifique a conexão e tente de novo.",
        });
      });

    return () => {
      vivo = false;
    };
  }, [aberta, sessao.id]);

  return (
    <Sobreposicao aberta={aberta} titulo={`Assentos — ${sala}`} aoFechar={aoFechar}>
      <SeletorDeHorario horarios={horarios} atual={sessao} aoTrocar={setSessao} />

      {estado.fase === "carregando" && (
        <p className={estilos.aviso} role="status">
          Carregando a lotação…
        </p>
      )}

      {estado.fase === "erro" && (
        <p className={estilos.avisoErro} role="alert">
          {estado.mensagem}
        </p>
      )}

      {estado.fase === "pronto" && <Lotacao mapa={estado.mapa} sessao={sessao} />}
    </Sobreposicao>
  );
}

function Lotacao({ mapa, sessao }: { mapa: MapaSessao; sessao: Screening }) {
  const assentos = mapa.fileiras.flatMap((fileira) => fileira.assentos);
  const livres = assentos.filter((assento) => assento.situacao === "livre").length;

  if (assentos.length === 0) {
    return (
      <p className={estilos.aviso} role="status">
        Esta sala ainda não tem lugares cadastrados.
      </p>
    );
  }

  return (
    <>
      <p className={estilos.tela} aria-hidden="true">
        TELA
      </p>

      <div className={estilos.salaDesenho}>
        {mapa.fileiras.map((fileira) => (
          <div key={fileira.letra} className={estilos.fileira}>
            <span className={estilos.fileiraLetra} aria-hidden="true">
              {fileira.letra}
            </span>
            {fileira.assentos.map((assento) => (
              <span
                key={assento.id}
                className={
                  assento.situacao === "livre"
                    ? estilos.lugarLivre
                    : `${estilos.lugarLivre} ${estilos.lugarTomado}`
                }
                // Sem texto por assento: sessenta lugares anunciados um a um
                // afogam quem usa leitor de tela. A contagem abaixo é o que
                // responde à pergunta que trouxe a pessoa aqui.
                aria-hidden="true"
              />
            ))}
          </div>
        ))}
      </div>

      {/* Legenda por FORMA além de cor: o vazado é livre, o preenchido é
          ocupado. Em escala de cinza a distinção sobrevive. */}
      <ul className={estilos.legenda}>
        <li className={estilos.itemDaLegenda}>
          <span className={estilos.lugarLivre} aria-hidden="true" /> Livre
        </li>
        <li className={estilos.itemDaLegenda}>
          <span className={`${estilos.lugarLivre} ${estilos.lugarTomado}`} aria-hidden="true" />{" "}
          Ocupado
        </li>
      </ul>

      <p className={estilos.contagem}>
        <strong>{livres}</strong> {livres === 1 ? "lugar livre" : "lugares livres"} de{" "}
        {assentos.length}
      </p>

      {mapa.esgotada || livres === 0 ? (
        <p className={estilos.aviso}>
          Esta sessão está esgotada. Veja os outros horários acima.
        </p>
      ) : (
        <Link href={`/sessoes/${sessao.id}`} className={estilos.seguir}>
          Escolher lugares
        </Link>
      )}
    </>
  );
}
