import { diaCivil, rotuloDoDia } from "@/lib/grade-sessoes";
import type { SessaoDaGrade } from "@/lib/types";

import estilos from "./programacao.module.css";

/**
 * A grade do organizador, agrupada por dia.
 *
 * POR DIA, e não uma lista corrida: quem programa pensa em "o que vai ao ar
 * amanhã", e uma lista de trinta linhas ordenada por horário obriga a pessoa a
 * reconstruir os dias com o olho. É o mesmo agrupamento que a página do filme
 * usa desde a 012, e a leitura de dia vem de lá — não de uma segunda cópia.
 *
 * O ESTADO SE DISTINGUE POR RÓTULO + FORMA, NUNCA SÓ POR COR (FR-029). Cada
 * pastilha carrega a palavra ("Rascunho", "Publicada", "Cancelada") e uma forma
 * própria: rascunho tem contorno tracejado, publicada tem preenchimento sólido,
 * cancelada vem com o horário riscado. Em escala de cinza as três continuam
 * distinguíveis — é a mesma disciplina que o mapa de assentos cumpre.
 */

const FUSO = "America/Sao_Paulo";

function horario(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function moeda(valor: string): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number(valor));
}

function agruparPorDia(sessoes: SessaoDaGrade[]) {
  const porDia = new Map<string, SessaoDaGrade[]>();

  for (const sessao of [...sessoes].sort(
    (a, b) => new Date(a.inicio).getTime() - new Date(b.inicio).getTime(),
  )) {
    const dia = diaCivil(sessao.inicio);
    porDia.set(dia, [...(porDia.get(dia) ?? []), sessao]);
  }

  return [...porDia.entries()].map(([dia, linhas]) => ({
    dia,
    rotulo: rotuloDoDia(dia),
    linhas,
  }));
}

export function Grade({ sessoes }: { sessoes: SessaoDaGrade[] }) {
  const dias = agruparPorDia(sessoes);

  return (
    <div className={estilos.grade}>
      {dias.map((dia) => (
        <section key={dia.dia} className={estilos.dia}>
          <h2 className={estilos.diaTitulo}>{dia.rotulo}</h2>

          <ul className={estilos.linhas}>
            {dia.linhas.map((sessao) => (
              <li key={sessao.id} className={estilos.linha} data-estado={sessao.estado}>
                <span className={estilos.horario}>{horario(sessao.inicio)}</span>

                <span className={estilos.filme}>{sessao.filme.titulo}</span>

                <span className={estilos.sala}>{sessao.sala.nome}</span>

                <span className={estilos.preco}>{moeda(sessao.preco)}</span>

                {/* Ocupação sobre lugares, e não porcentagem: "12 de 60" diz
                    quantas poltronas ainda dá para vender, que é a decisão que
                    o organizador toma olhando esta linha. */}
                <span className={estilos.ocupacao}>
                  <span className={estilos.ocupacaoNumero}>{sessao.ocupacao}</span>
                  <span className={estilos.ocupacaoTotal}>de {sessao.sala.lugares}</span>
                </span>

                <span className={estilos.estado} data-estado={sessao.estado}>
                  {sessao.estado_rotulo}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
