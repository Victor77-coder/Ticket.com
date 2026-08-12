"use client";

import { useState } from "react";

import type { LinkDeCompartilhamento } from "@/lib/types";

import estilos from "./tickets.module.css";

/**
 * Copiar, gerar e revogar o link de um ingresso.
 *
 * ILHA CLIENTE: as três ações são de rede e mudam estado na tela. A página do
 * ingresso é Server Component e não pode hospedá-las — mesmo arranjo do
 * `AccountMenu` da 003.
 *
 * O TEXTO DIZ QUE O LINK É CREDENCIAL, e isso não é decoração. A pessoa está
 * prestes a mandar num aplicativo de mensagens algo que abre o QR para quem
 * tiver o endereço. Esconder isso atrás de "compartilhar" faria a interface
 * mentir sobre o que a ação faz — e a revogação existe justamente porque a
 * consequência é real.
 *
 * `aria-live` no resultado: quem usa leitor de tela precisa saber que o link
 * foi gerado, copiado ou revogado. Sem isso a ação acontece em silêncio
 * (FR-054).
 */

type Props = {
  ingressoId: string;
  inicial: LinkDeCompartilhamento;
};

type Situacao = "parado" | "trabalhando";

export default function PainelDeLink({ ingressoId, inicial }: Props) {
  const [link, setLink] = useState<LinkDeCompartilhamento>(inicial);
  const [situacao, setSituacao] = useState<Situacao>("parado");
  const [aviso, setAviso] = useState("");
  const [erro, setErro] = useState("");

  async function chamar(metodo: "POST" | "DELETE", mensagem: string) {
    setSituacao("trabalhando");
    setErro("");
    setAviso("");
    try {
      const resposta = await fetch("/api/link-do-ingresso", {
        method: metodo,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingresso: ingressoId }),
      });
      const corpo = await resposta.json().catch(() => null);

      if (!resposta.ok) {
        // A frase vem do Django, já em pt-BR. Traduzir de novo aqui faria a
        // mesma regra existir em dois lugares.
        setErro(corpo?.detail ?? "Não foi possível concluir agora. Tente de novo.");
        return;
      }

      setLink(corpo as LinkDeCompartilhamento);
      setAviso(mensagem);
    } catch {
      setErro("Não conseguimos falar com o servidor. Tente de novo em instantes.");
    } finally {
      setSituacao("parado");
    }
  }

  async function copiar() {
    if (!link.endereco) return;
    try {
      await navigator.clipboard.writeText(link.endereco);
      setAviso("Link copiado.");
      setErro("");
    } catch {
      // Área de transferência negada é comum e não é falha nossa. O endereço
      // fica visível em texto selecionável justamente para este caso.
      setErro("Seu navegador não deixou copiar. Selecione o endereço acima e copie.");
    }
  }

  const trabalhando = situacao === "trabalhando";

  return (
    <section className={estilos.painel} aria-labelledby="painel-link">
      <h2 id="painel-link" className={estilos.painelTitulo}>
        Compartilhar este ingresso
      </h2>

      {link.ativo && link.endereco ? (
        <>
          <p className={estilos.painelTexto}>
            Quem abrir este link vê o ingresso <strong>com o código</strong> e pode
            usá-lo para entrar. Mande só para quem vai com você — e revogue se ele for
            parar no lugar errado.
          </p>

          {/* Selecionável, não só copiável: se a área de transferência for
            * negada, isto é o que resta. */}
          <p className={estilos.endereco}>
            <code className={estilos.enderecoValor}>{link.endereco}</code>
          </p>

          <div className={estilos.acoes}>
            <button type="button" className={estilos.botaoPrimario} onClick={copiar}>
              Copiar link
            </button>
            <button
              type="button"
              className={estilos.botaoSecundario}
              onClick={() => chamar("DELETE", "Link revogado. Ele não abre mais.")}
              disabled={trabalhando}
            >
              {trabalhando ? "Revogando…" : "Revogar link"}
            </button>
          </div>
        </>
      ) : (
        <>
          <p className={estilos.painelTexto}>
            Você pode gerar um link para mostrar este ingresso a outra pessoa, sem que
            ela precise entrar em nenhuma conta.{" "}
            <strong>O link mostra o código de entrada</strong> — você pode revogá-lo
            quando quiser.
          </p>

          <div className={estilos.acoes}>
            <button
              type="button"
              className={estilos.botaoPrimario}
              onClick={() => chamar("POST", "Link gerado. Copie e mande para quem vai com você.")}
              disabled={trabalhando}
            >
              {trabalhando ? "Gerando…" : "Gerar link"}
            </button>
          </div>
        </>
      )}

      {/* O resultado de cada ação é anunciado, sempre (FR-054). */}
      <p className={estilos.aviso} role="status" aria-live="polite">
        {aviso}
      </p>
      {erro && (
        <p className={estilos.erro} role="alert">
          {erro}
        </p>
      )}
    </section>
  );
}
