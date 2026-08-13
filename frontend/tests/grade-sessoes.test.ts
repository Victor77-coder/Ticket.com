import { describe, expect, it } from "vitest";

import { agruparSessoesPorDia, dataNumerica, diaCivil, hojeCivil, nomeDoDia } from "@/lib/grade-sessoes";
import type { Screening } from "@/lib/types";

function sessao(sobrescreve: Partial<Screening> & Pick<Screening, "id" | "starts_at" | "room_name">): Screening {
  return {
    price: "32.00",
    has_available_seats: true,
    ...sobrescreve,
  };
}

describe("agruparSessoesPorDia", () => {
  it("junta no mesmo dia civil sessões de salas diferentes", () => {
    const grade = agruparSessoesPorDia([
      sessao({ id: 1, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
      sessao({ id: 2, starts_at: "2026-08-12T21:00:00-03:00", room_name: "Sala 2" }),
    ]);

    expect(grade).toHaveLength(1);
    expect(grade[0].dia).toBe("2026-08-12");
    expect(grade[0].salas.map((s) => s.nome)).toEqual(["Sala 1", "Sala 2"]);
    expect(grade[0].salas[0].horarios.map((h) => h.id)).toEqual([1]);
    expect(grade[0].salas[1].horarios.map((h) => h.id)).toEqual([2]);
  });

  it("não inventa dia sem sessão", () => {
    const grade = agruparSessoesPorDia([
      sessao({ id: 1, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
      sessao({ id: 2, starts_at: "2026-08-14T19:00:00-03:00", room_name: "Sala 1" }),
    ]);

    expect(grade.map((d) => d.dia)).toEqual(["2026-08-12", "2026-08-14"]);
  });

  it("um único dia continua no seletor — a lista não some por ter uma opção só", () => {
    const grade = agruparSessoesPorDia([
      sessao({ id: 1, starts_at: "2026-08-12T19:00:00-03:00", room_name: "Sala 1" }),
    ]);

    expect(grade).toHaveLength(1);
    expect(grade[0].salas).toHaveLength(1);
  });

  it("usa o dia civil em America/Sao_Paulo, não o UTC", () => {
    // 02:00 UTC de 13/08 é 23:00 de 12/08 em São Paulo (UTC−3, sem horário de verão).
    expect(diaCivil("2026-08-13T02:00:00.000Z")).toBe("2026-08-12");
    expect(diaCivil("2026-08-13T03:00:00.000Z")).toBe("2026-08-13");

    const grade = agruparSessoesPorDia([
      sessao({ id: 1, starts_at: "2026-08-13T02:00:00.000Z", room_name: "Sala 1" }),
      sessao({ id: 2, starts_at: "2026-08-13T03:00:00.000Z", room_name: "Sala 1" }),
    ]);

    expect(grade.map((d) => d.dia)).toEqual(["2026-08-12", "2026-08-13"]);
  });
});

describe("rótulo do dia na grade", () => {
  it("hoje também tem data numérica", () => {
    const hoje = hojeCivil();
    const [, mes, diaDoMes] = hoje.split("-");

    expect(nomeDoDia(hoje)).toBe("hoje");
    expect(dataNumerica(hoje)).toBe(`${diaDoMes}/${mes}`);
  });

  it("outro dia é o weekday abreviado e DD/MM", () => {
    expect(nomeDoDia("2026-08-12")).toBe("qua");
    expect(dataNumerica("2026-08-12")).toBe("12/08");
  });
});
