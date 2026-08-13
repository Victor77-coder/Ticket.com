"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { diaCivil, rotuloDoDia } from "@/lib/grade-sessoes";
import { formatarPreco } from "@/lib/moeda";
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
 *
 * OS BOTÕES SÃO DESABILITADOS COM EXPLICAÇÃO, NUNCA ESCONDIDOS. `pode_editar`,
 * `pode_publicar` e `pode_cancelar` vêm do servidor como CONVENIÊNCIA — cada
 * ação revalida tudo lá, e a recusa que chega de volta é a frase que a pessoa
 * lê. Esconder o controle não seria autorização e ainda deixaria a pessoa sem
 * saber por que o caminho sumiu (FR-037).
 *
 * CANCELAR PEDE CONFIRMAÇÃO EM DOIS PASSOS, dentro da própria linha. Cancelada
 * é estado terminal — não há "descancelar" —, e um clique acidental que tira
 * uma sessão da venda não tem desfazer. A confirmação inline evita o
 * `window.confirm`, que sequestra a página e não é estilizável nem testável.
 */

const FUSO = "America/Sao_Paulo";

function horario(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: FUSO,
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
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

export function Grade({ sessoes: iniciais }: { sessoes: SessaoDaGrade[] }) {
  const router = useRouter();

  const [sessoes, setSessoes] = useState(iniciais);
  const [aviso, setAviso] = useState("");
  const [trabalhando, setTrabalhando] = useState<number | null>(null);
  const [confirmando, setConfirmando] = useState<number | null>(null);

  async function agir(sessao: SessaoDaGrade, acao: "publicar" | "cancelar") {
    setTrabalhando(sessao.id);
    setAviso("");

    try {
      const resposta = await fetch(
        `/api/programacao/sessoes/${sessao.id}/${acao}`,
        { method: "POST" },
      );
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        // A frase é do servidor — inclusive as de horário passado e sala sem
        // lugares, que chegam por campo.
        setAviso(
          corpo?.detail ??
            corpo?.inicio ??
            corpo?.sala ??
            "Não foi possível concluir a ação agora.",
        );
        return;
      }

      setSessoes((atual) =>
        atual.map((item) => (item.id === sessao.id ? (corpo as SessaoDaGrade) : item)),
      );
      setConfirmando(null);
      // A home e a página do filme leem a grade no servidor: sem o refresh, a
      // sessão publicada só apareceria lá no próximo recarregamento.
      router.refresh();
    } finally {
      setTrabalhando(null);
    }
  }

  const dias = agruparPorDia(sessoes);

  return (
    <div className={estilos.grade}>
      {aviso && (
        <p className={estilos.alerta} role="alert">
          {aviso}
        </p>
      )}

      {dias.map((dia) => (
        <section key={dia.dia} className={estilos.dia}>
          <h2 className={estilos.diaTitulo}>{dia.rotulo}</h2>

          <ul className={estilos.linhas}>
            {dia.linhas.map((sessao) => (
              <li key={sessao.id} className={estilos.linha} data-estado={sessao.estado}>
                <span className={estilos.horario}>{horario(sessao.inicio)}</span>

                <span className={estilos.filme}>{sessao.filme.titulo}</span>

                <span className={estilos.sala}>{sessao.sala.nome}</span>

                <span className={estilos.preco}>{formatarPreco(sessao.preco)}</span>

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

                <span className={estilos.acoesDaLinha}>
                  {sessao.pode_editar && (
                    <Link
                      href={`/programacao/sessoes/${sessao.id}`}
                      className={estilos.acaoDeLinha}
                    >
                      Editar
                    </Link>
                  )}

                  {sessao.estado === "draft" && (
                    <button
                      type="button"
                      className={estilos.acaoDeLinha}
                      disabled={!sessao.pode_publicar || trabalhando === sessao.id}
                      onClick={() => agir(sessao, "publicar")}
                    >
                      Publicar
                    </button>
                  )}

                  {sessao.pode_cancelar &&
                    (confirmando === sessao.id ? (
                      <>
                        <button
                          type="button"
                          className={estilos.acaoDeLinhaPerigo}
                          disabled={trabalhando === sessao.id}
                          onClick={() => agir(sessao, "cancelar")}
                        >
                          Confirmar
                        </button>
                        <button
                          type="button"
                          className={estilos.acaoDeLinha}
                          onClick={() => setConfirmando(null)}
                        >
                          Voltar
                        </button>
                      </>
                    ) : (
                      <button
                        type="button"
                        className={estilos.acaoDeLinha}
                        onClick={() => setConfirmando(sessao.id)}
                      >
                        Cancelar
                      </button>
                    ))}

                  {sessao.estado === "draft" && !sessao.pode_publicar && (
                    <span className={estilos.salaDetalhe}>
                      {sessao.sala.lugares === 0
                        ? "sala sem lugares"
                        : "horário no passado"}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
