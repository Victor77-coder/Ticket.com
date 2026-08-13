"use client";

import { useEffect, useState } from "react";

import Desfecho from "@/components/gate/Desfecho";
import LeitorDeCodigo from "@/components/gate/LeitorDeCodigo";
import type { Desfecho as DesfechoTipo, SessaoDaPorta } from "@/lib/types";

import estilos from "./portaria.module.css";

/**
 * A tela de validação — escolha da sessão, leitura e desfecho.
 *
 * A SESSÃO DA PORTA É ESCOLHIDA ANTES DE QUALQUER LEITURA, e não é conveniência
 * de interface: sem ela o desfecho "sessão errada" seria IMPOSSÍVEL. O código
 * carrega a sessão a que o ingresso pertence, e comparar esse valor com ele
 * mesmo sempre dá igual. Entregar três desfechos onde a constitution exige
 * quatro é tela pela metade.
 *
 * A escolha vive no ARMAZENAMENTO LOCAL, não na conta: dois operadores podem
 * usar a mesma conta do seed em portas diferentes, e guardá-la no usuário faria
 * uma sobrescrever a outra. É também o que a faz sobreviver a um recarregamento
 * — trocar de porta é decisão do operador, não efeito de recarregar.
 *
 * O DESFECHO NÃO SE APAGA SOZINHO. Numa fila o operador pode olhar tarde, e um
 * resultado que sumiu vira uma segunda leitura desnecessária.
 */

const CHAVE_DA_PORTA = "portaria:sessao";

type Props = {
  sessoes: SessaoDaPorta[];
};

function horario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    timeZone: "America/Sao_Paulo",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function PortariaCliente({ sessoes }: Props) {
  const [sessaoId, setSessaoId] = useState<number | null>(null);
  const [pronto, setPronto] = useState(false);
  const [codigo, setCodigo] = useState("");
  const [desfecho, setDesfecho] = useState<DesfechoTipo | null>(null);
  const [aviso, setAviso] = useState("");
  const [ocupado, setOcupado] = useState(false);

  // Reidrata a sessão da porta, descartando-a se ela não estiver mais na lista
  // — a grade muda de um dia para o outro, e uma escolha órfã deixaria a tela
  // validando contra uma sessão que já não existe.
  useEffect(() => {
    const guardada = window.localStorage.getItem(CHAVE_DA_PORTA);
    const numero = guardada ? Number(guardada) : NaN;
    if (Number.isInteger(numero) && sessoes.some((s) => s.id === numero)) {
      setSessaoId(numero);
    }
    setPronto(true);
  }, [sessoes]);

  function escolher(id: number) {
    window.localStorage.setItem(CHAVE_DA_PORTA, String(id));
    setSessaoId(id);
    setDesfecho(null);
    setAviso("");
  }

  function trocarDePorta() {
    window.localStorage.removeItem(CHAVE_DA_PORTA);
    setSessaoId(null);
    setDesfecho(null);
    setAviso("");
  }

  async function validar(codigoLido: string) {
    const limpo = codigoLido.trim();

    // Campo vazio NÃO é "inválido": nada foi apresentado, e não há o que
    // julgar. Dizer "ingresso não reconhecido" faria o operador procurar
    // defeito no ingresso da pessoa.
    if (!limpo) {
      setAviso("Apresente ou digite um código.");
      setDesfecho(null);
      return;
    }
    if (sessaoId === null) return;

    setOcupado(true);
    setAviso("");
    try {
      const resposta = await fetch("/api/validar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ codigo: limpo, sessao: sessaoId }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        // A frase vem do Django, já em pt-BR.
        setAviso(corpo?.detail ?? "Não foi possível validar agora. Tente de novo.");
        setDesfecho(null);
        return;
      }

      setDesfecho(corpo as DesfechoTipo);
      setCodigo("");
    } catch {
      setAviso("Não conseguimos falar com o servidor. Tente de novo em instantes.");
      setDesfecho(null);
    } finally {
      setOcupado(false);
    }
  }

  if (!pronto) return null;

  // --- Nenhuma sessão hoje ---
  if (sessoes.length === 0) {
    return (
      <section className={estilos.aviso} role="status">
        <h1 className={estilos.avisoTitulo}>Nenhuma sessão hoje</h1>
        <p className={estilos.avisoTexto}>
          Não há sessões programadas para hoje, então não há entrada a receber. Assim
          que a grade do dia existir, ela aparece aqui.
        </p>
      </section>
    );
  }

  // --- Sessão da porta ainda não escolhida ---
  if (sessaoId === null) {
    return (
      <section className={estilos.escolha} aria-labelledby="escolha-titulo">
        <h1 id="escolha-titulo" className={estilos.titulo}>
          Qual sessão esta porta está recebendo?
        </h1>
        <p className={estilos.subtitulo}>
          Escolha antes de começar. É com essa sessão que cada ingresso vai ser
          comparado — é o que permite recusar quem chegou na porta errada.
        </p>

        <ul className={estilos.listaDeSessoes}>
          {sessoes.map((sessao) => (
            <li key={sessao.id}>
              <button
                type="button"
                className={estilos.opcaoDeSessao}
                onClick={() => escolher(sessao.id)}
              >
                <span className={estilos.opcaoHorario}>{horario(sessao.inicio)}</span>
                <span className={estilos.opcaoFilme}>{sessao.filme}</span>
                <span className={estilos.opcaoSala}>{sessao.sala}</span>
              </button>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  const escolhida = sessoes.find((s) => s.id === sessaoId)!;

  return (
    <section className={estilos.posto} aria-labelledby="posto-titulo">
      <header className={estilos.cabecalhoDoPosto}>
        <div>
          <p className={estilos.rotuloDaPorta}>Esta porta está recebendo</p>
          <h1 id="posto-titulo" className={estilos.sessaoDaPorta}>
            {escolhida.filme}
          </h1>
          <p className={estilos.sessaoDetalhe}>
            {horario(escolhida.inicio)} · {escolhida.sala}
          </p>
        </div>
        <button type="button" className={estilos.trocar} onClick={trocarDePorta}>
          Trocar de porta
        </button>
      </header>

      <div className={estilos.entradas}>
        <LeitorDeCodigo aoLer={validar} ocupado={ocupado} />

        {/* SEMPRE VISÍVEL, mesmo com a câmera funcionando. A constitution
          * exige a digitação como alternativa "sempre disponível" — e é ela
          * que mantém a portaria de pé quando a câmera não está em contexto
          * seguro, que é o cenário mais provável de demonstração. */}
        <form
          className={estilos.formulario}
          onSubmit={(evento) => {
            evento.preventDefault();
            validar(codigo);
          }}
        >
          <label className={estilos.rotulo} htmlFor="codigo">
            Ou digite o código do ingresso
          </label>
          <textarea
            id="codigo"
            className={estilos.campo}
            value={codigo}
            onChange={(evento) => setCodigo(evento.target.value)}
            rows={3}
            spellCheck={false}
            autoComplete="off"
          />
          <button type="submit" className={estilos.botao} disabled={ocupado}>
            {ocupado ? "Validando…" : "Validar"}
          </button>
        </form>
      </div>

      {aviso && (
        <p className={estilos.preenchimento} role="alert">
          {aviso}
        </p>
      )}

      {desfecho && <Desfecho desfecho={desfecho} />}
    </section>
  );
}
