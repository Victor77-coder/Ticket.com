"use client";

import { useId, useState } from "react";

import estilos from "./payment.module.css";

/**
 * O formulário de cartão fictício.
 *
 * NENHUMA VALIDAÇÃO DE DESFECHO AQUI. A forma é conferida só o bastante para
 * não mandar campo vazio ao servidor; quem decide aprovar ou recusar é o
 * Django, sempre. Reproduzir a tabela de cartões no navegador colocaria a
 * regra em dois lugares — e o cliente é justamente onde ela não vale nada.
 *
 * `<label>` real ligado a cada campo, `inputMode` numérico e `autoComplete`
 * padrão: é o que faz o formulário funcionar por teclado e ser anunciado por
 * leitor de tela sem nenhum `aria-` extra (FR-047).
 */

export type FormularioDeCartaoProps = {
  enviando: boolean;
  onEnviar: (dados: {
    numero: string;
    nome: string;
    validade: string;
    cvv: string;
  }) => void;
};

function apenasDigitos(valor: string) {
  return valor.replace(/\D/g, "");
}

function agruparNumero(valor: string) {
  return apenasDigitos(valor)
    .slice(0, 16)
    .replace(/(.{4})/g, "$1 ")
    .trim();
}

function formatarValidade(valor: string) {
  const digitos = apenasDigitos(valor).slice(0, 6);
  if (digitos.length <= 2) return digitos;
  return `${digitos.slice(0, 2)}/${digitos.slice(2)}`;
}

export default function FormularioDeCartao({
  enviando,
  onEnviar,
}: FormularioDeCartaoProps) {
  const id = useId();
  const [numero, setNumero] = useState("");
  const [nome, setNome] = useState("");
  const [validade, setValidade] = useState("");
  const [cvv, setCvv] = useState("");

  function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    if (enviando) return;
    onEnviar({ numero: apenasDigitos(numero), nome, validade, cvv });
  }

  return (
    // `method="post"` mesmo com o envio sendo por JavaScript. Sem ele, um
    // envio ANTES de a página hidratar cai no comportamento nativo do
    // navegador, que é um GET para a URL atual — e o número do cartão iria
    // parar na barra de endereço, no histórico e em qualquer log de proxy
    // pelo caminho. Com `post`, o mesmo envio prematuro não carrega os campos
    // na URL. Encontrado ao rodar o e2e desta feature (FR-011).
    <form className={estilos.formulario} method="post" onSubmit={enviar} noValidate>
      <h2 className={estilos.formularioTitulo}>Dados do cartão</h2>

      <div className={estilos.campo}>
        <label htmlFor={`${id}-numero`}>Número do cartão</label>
        <input
          id={`${id}-numero`}
          name="numero"
          value={numero}
          onChange={(e) => setNumero(agruparNumero(e.target.value))}
          inputMode="numeric"
          autoComplete="cc-number"
          placeholder="0000 0000 0000 0000"
          disabled={enviando}
        />
      </div>

      <div className={estilos.campo}>
        <label htmlFor={`${id}-nome`}>Nome impresso no cartão</label>
        <input
          id={`${id}-nome`}
          name="nome"
          value={nome}
          onChange={(e) => setNome(e.target.value.toUpperCase())}
          autoComplete="cc-name"
          disabled={enviando}
        />
      </div>

      <div className={estilos.dupla}>
        <div className={estilos.campo}>
          <label htmlFor={`${id}-validade`}>Validade</label>
          <input
            id={`${id}-validade`}
            name="validade"
            value={validade}
            onChange={(e) => setValidade(formatarValidade(e.target.value))}
            inputMode="numeric"
            autoComplete="cc-exp"
            placeholder="MM/AAAA"
            disabled={enviando}
          />
        </div>

        <div className={estilos.campo}>
          <label htmlFor={`${id}-cvv`}>Código de segurança</label>
          <input
            id={`${id}-cvv`}
            name="cvv"
            value={cvv}
            onChange={(e) => setCvv(apenasDigitos(e.target.value).slice(0, 4))}
            inputMode="numeric"
            autoComplete="cc-csc"
            placeholder="123"
            disabled={enviando}
          />
        </div>
      </div>

      <button type="submit" className={estilos.pagar} disabled={enviando}>
        {enviando ? "Processando…" : "Pagar e receber ingressos"}
      </button>
    </form>
  );
}
