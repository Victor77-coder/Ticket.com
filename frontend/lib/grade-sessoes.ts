import type { Screening } from "./types";

/**
 * Agrupa sessões já recebidas por dia civil e depois por sala.
 *
 * Não chama API e não cria sessão: a página do filme continua recebendo
 * `screenings[]` como a 001 entregou (012 / R1).
 */

const FUSO = "America/Sao_Paulo";

export type SalaDaGrade = {
  nome: string;
  horarios: Screening[];
};

export type DiaDaGrade = {
  /** YYYY-MM-DD no fuso de São Paulo. */
  dia: string;
  rotulo: string;
  salas: SalaDaGrade[];
};

export function diaCivil(iso: string): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: FUSO,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date(iso));
}

export function hojeCivil(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: FUSO,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function rotuloDoDia(dia: string): string {
  if (dia === hojeCivil()) return "Hoje";

  const instante = new Date(`${dia}T12:00:00-03:00`);
  const semana = new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    weekday: "short",
  })
    .format(instante)
    .replace(".", "");
  const [, mes, diaDoMes] = dia.split("-");
  return `${semana} ${diaDoMes}/${mes}`;
}

export function agruparSessoesPorDia(sessoes: Screening[]): DiaDaGrade[] {
  const ordenadas = [...sessoes].sort(
    (a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime(),
  );

  const porDia = new Map<string, Screening[]>();
  for (const sessao of ordenadas) {
    const dia = diaCivil(sessao.starts_at);
    const lista = porDia.get(dia) ?? [];
    lista.push(sessao);
    porDia.set(dia, lista);
  }

  return [...porDia.entries()].map(([dia, lista]) => {
    const porSala = new Map<string, Screening[]>();
    for (const sessao of lista) {
      const daSala = porSala.get(sessao.room_name) ?? [];
      daSala.push(sessao);
      porSala.set(sessao.room_name, daSala);
    }

    return {
      dia,
      rotulo: rotuloDoDia(dia),
      salas: [...porSala.entries()].map(([nome, horarios]) => ({ nome, horarios })),
    };
  });
}
