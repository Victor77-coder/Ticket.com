"use client";

import { useEffect, useState } from "react";

import { valorDoLugar } from "@/lib/meia";
import { formatarPreco } from "@/lib/moeda";
import type { Screening } from "@/lib/types";

import SeletorDeHorario from "./SeletorDeHorario";
import Sobreposicao from "./Sobreposicao";
import estilos from "./sessao.module.css";

/**
 * Quanto custa, antes de entrar no mapa.
 *
 * A TABELA É POR SESSÃO, e não por filme: duas sessões do mesmo filme na mesma
 * semana podem ter preços diferentes, e uma tabela única mentiria para uma das
 * duas. Daí o seletor de horário aqui dentro.
 *
 * A META DA FRASE SOBRE DOCUMENTO não é jurídica, é operacional: a plataforma
 * VENDE meia e quem CONFERE é a pessoa na porta, como em qualquer cinema. Dizer
 * isso aqui é o que impede a expectativa de que o sistema vá pedir comprovação
 * no checkout.
 */

type Props = {
  aberta: boolean;
  sala: string;
  horarios: Screening[];
  inicial: Screening;
  aoFechar: () => void;
};

export default function PainelDePrecos({ aberta, sala, horarios, inicial, aoFechar }: Props) {
  const [sessao, setSessao] = useState(inicial);

  // Reabrir o painel volta ao horário de referência do cartão: o estado de uma
  // consulta anterior não deve sobreviver ao fechamento.
  useEffect(() => {
    if (aberta) setSessao(inicial);
  }, [aberta, inicial]);

  const inteira = Number(sessao.price);
  const meia = valorDoLugar(sessao.price, "meia");

  return (
    <Sobreposicao aberta={aberta} titulo={`Preços — ${sala}`} aoFechar={aoFechar}>
      <SeletorDeHorario horarios={horarios} atual={sessao} aoTrocar={setSessao} />

      <dl className={estilos.tabelaDePrecos}>
        <div className={estilos.linhaDePreco}>
          <dt>Inteira</dt>
          <dd>{formatarPreco(inteira)}</dd>
        </div>
        <div className={estilos.linhaDePreco}>
          <dt>Meia</dt>
          <dd>{formatarPreco(meia)}</dd>
        </div>
      </dl>

      <p className={estilos.notaDePreco}>
        A meia-entrada é conferida na entrada do cinema, mediante documento.
      </p>
    </Sobreposicao>
  );
}
