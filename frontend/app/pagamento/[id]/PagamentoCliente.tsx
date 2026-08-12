"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import FormularioDeCartao from "@/components/payment/FormularioDeCartao";
import ResumoDaCompra from "@/components/payment/ResumoDaCompra";
import Ingresso from "@/components/tickets/Ingresso";
import type { Ingresso as IngressoTipo, Pagamento, Reserva } from "@/lib/types";

import estilos from "./pagamento.module.css";

/**
 * A parte viva de `/pagamento/[id]`: o formulário, a recusa e os ingressos.
 *
 * A página é uma rota só com quatro estados (R13). Este componente cobre os
 * dois que mudam por interação — "a pagar" e "paga" —, e os estados de
 * reserva vencida ou não encontrada ficam no Server Component, que já sabe
 * deles sem precisar de JavaScript.
 *
 * O RESULTADO DA COBRANÇA VEM SEMPRE DO SERVIDOR. Este componente não conhece
 * a tabela de cartões, não decide aprovação e não infere motivo de recusa: ele
 * exibe a frase que o Django mandou. É o que impede a regra de existir em dois
 * lugares, e o que faz a recusa continuar valendo quando alguém chama a API
 * direto (FR-042).
 */

type Props = {
  reserva: Reserva;
  filme: string;
  sala: string;
  inicio: string;
};

type Recusa = { motivo: string; frase: string } | null;

function restante(expiraEm: string, agora: number) {
  return Math.max(0, Math.floor((new Date(expiraEm).getTime() - agora) / 1000));
}

function formatarRestante(segundos: number) {
  const min = Math.floor(segundos / 60);
  const seg = segundos % 60;
  return `${min}:${String(seg).padStart(2, "0")}`;
}

export default function PagamentoCliente({ reserva, filme, sala, inicio }: Props) {
  const [pago, setPago] = useState<{
    pagamento: Pagamento;
    ingressos: IngressoTipo[];
  } | null>(
    reserva.situacao === "paga" && reserva.pagamento && reserva.ingressos
      ? { pagamento: reserva.pagamento, ingressos: reserva.ingressos }
      : null,
  );
  const [recusa, setRecusa] = useState<Recusa>(null);
  const [erroForma, setErroForma] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [segundos, setSegundos] = useState(() =>
    restante(reserva.expira_em, Date.now()),
  );

  // A contagem só corre enquanto há o que pagar. Reserva paga não vence, então
  // exibir prazo nela seria mentira — `expira_em` continua vindo do servidor
  // com o valor original, mas perde o significado depois da compra.
  useEffect(() => {
    if (pago) return;
    const id = setInterval(() => {
      setSegundos(restante(reserva.expira_em, Date.now()));
    }, 1000);
    return () => clearInterval(id);
  }, [pago, reserva.expira_em]);

  const venceuNaTela = !pago && segundos === 0;

  async function pagar(dados: {
    numero: string;
    nome: string;
    validade: string;
    cvv: string;
  }) {
    setEnviando(true);
    setRecusa(null);
    setErroForma(null);

    try {
      const resposta = await fetch("/api/pagar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reserva: reserva.id, ...dados }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (resposta.status === 201 && corpo) {
        setPago({ pagamento: corpo.pagamento, ingressos: corpo.ingressos });
        return;
      }

      if (resposta.status === 402 && corpo) {
        // Recusa de COBRANÇA: a pessoa troca de cartão. O formulário
        // permanece preenchível e o prazo segue correndo do mesmo instante.
        setRecusa({ motivo: corpo.motivo, frase: corpo.detail });
        return;
      }

      if (resposta.status === 409 && corpo?.situacao === "paga" && corpo.ingressos) {
        // Clique duplo, ou a corrida perdida. Em vez de negar, leva aos
        // ingressos que já existem.
        setPago({ pagamento: corpo.pagamento, ingressos: corpo.ingressos });
        return;
      }

      if (resposta.status === 409 || resposta.status === 401 || resposta.status === 403) {
        // Estados que não se resolvem no formulário: recarregar traz a tela
        // certa do servidor, que é quem sabe o estado de verdade.
        window.location.reload();
        return;
      }

      // Erro de PREENCHIMENTO: a pessoa corrige o que digitou. É outra coisa
      // que a recusa de cobrança, e a tela diz isso com palavras diferentes.
      setErroForma(corpo?.detail ?? "Confira os dados do cartão.");
    } catch {
      setErroForma("Não foi possível falar com o servidor. Tente de novo.");
    } finally {
      setEnviando(false);
    }
  }

  if (pago) {
    return (
      <section className={estilos.emitidos} aria-labelledby="emitidos-titulo">
        <p className={estilos.selo} role="status">
          Pagamento aprovado
        </p>
        <h1 id="emitidos-titulo" className={estilos.tituloEmitidos}>
          {pago.ingressos.length > 1
            ? `Seus ${pago.ingressos.length} ingressos`
            : "Seu ingresso"}
        </h1>
        <p className={estilos.subtitulo}>
          Apresente o código na entrada da sala. Cartão final {pago.pagamento.cartao_final}
          {" · "}
          {new Intl.NumberFormat("pt-BR", {
            style: "currency",
            currency: "BRL",
          }).format(Number(pago.pagamento.total))}
        </p>

        <ul className={estilos.listaIngressos}>
          {pago.ingressos.map((ingresso, i) => (
            <Ingresso
              key={ingresso.codigo}
              ingresso={ingresso}
              indice={i + 1}
              total={pago.ingressos.length}
              variante="objeto"
            />
          ))}
        </ul>

        {/* A 008 deixava a confirmação como único lugar onde o ingresso
          * aparecia — sair daqui e ele ficava inalcançável. Este é o caminho
          * para o endereço permanente (FR-003). */}
        <Link href="/meus-ingressos" className={estilos.voltar}>
          Ver em Meus ingressos
        </Link>
      </section>
    );
  }

  if (venceuNaTela) {
    return (
      <section className={estilos.aviso} role="alert">
        <h1>O prazo desta reserva terminou</h1>
        <p>
          Os lugares voltaram para outras pessoas e nada foi cobrado. Escolha os lugares
          de novo para continuar.
        </p>
        <Link href={`/sessoes/${reserva.sessao}`} className={estilos.voltar}>
          Escolher lugares de novo
        </Link>
      </section>
    );
  }

  return (
    <>
      <h1 className={estilos.titulo}>Confira e pague</h1>

      <p className={estilos.prazo} role="timer" aria-live="polite">
        Você tem {formatarRestante(segundos)} para concluir o pagamento.
      </p>

      <div className={estilos.colunas}>
        <ResumoDaCompra reserva={reserva} filme={filme} sala={sala} inicio={inicio} />

        <div className={estilos.coluna}>
          {/* `role="alert"` nos dois: o desfecho da cobrança precisa chegar a
              quem não está olhando para a tela (FR-047). As duas caixas são
              visualmente distintas porque exigem ações diferentes. */}
          {recusa && (
            <p className={estilos.recusa} role="alert">
              <strong>Pagamento recusado.</strong> {recusa.frase}
            </p>
          )}
          {erroForma && (
            <p className={estilos.erroForma} role="alert">
              {erroForma}
            </p>
          )}

          <FormularioDeCartao enviando={enviando} onEnviar={pagar} />

          <p className={estilos.nota}>
            Cobrança simulada: nenhum valor é movimentado de verdade.
          </p>
        </div>
      </div>
    </>
  );
}
