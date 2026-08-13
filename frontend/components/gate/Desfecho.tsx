import type { Desfecho as DesfechoTipo } from "@/lib/types";

import estilos from "./gate.module.css";

/**
 * O desfecho de uma apresentação, na tela da portaria.
 *
 * A ESCOLHA É PELO CAMPO `situacao`, NUNCA PELA FRASE. A frase é apresentação
 * e muda numa revisão de redação; se a tela dependesse dela, a revisão
 * quebraria a interface.
 *
 * OS QUATRO SE DISTINGUEM POR SÍMBOLO E TÍTULO, e a cor é o QUARTO sinal —
 * depois de símbolo, título e disposição. O Princípio III exige que os quatro
 * desfechos sejam distinguíveis "sem ambiguidade", e o Princípio V proíbe
 * depender só de cor, como o mapa de assentos da 007 já aplica às poltronas.
 *
 * "Já utilizado" e "sessão errada" COMPARTILHAM a cor de alerta de propósito:
 * para o operador as duas significam "não entra por aqui, e não é fraude". Se
 * a cor fosse o sinal principal elas seriam indistinguíveis; como o sinal
 * principal é símbolo + título, a cor pode agrupar por gravidade sem perder a
 * distinção.
 */

const APRESENTACAO = {
  valido: { simbolo: "✓", titulo: "Pode entrar", classe: "valido" },
  ja_utilizado: { simbolo: "⟳", titulo: "Este ingresso já foi usado", classe: "usado" },
  sessao_errada: { simbolo: "⇄", titulo: "Ingresso de outra sessão", classe: "outraSessao" },
  invalido: { simbolo: "✕", titulo: "Ingresso não reconhecido", classe: "invalido" },
} as const;

function horario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

function diaEHora(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function Desfecho({ desfecho }: { desfecho: DesfechoTipo }) {
  const { simbolo, titulo, classe } = APRESENTACAO[desfecho.situacao];

  return (
    <section
      className={`${estilos.desfecho} ${estilos[classe]}`}
      role="status"
      aria-live="assertive"
    >
      {/* `aria-hidden` no símbolo: ele é reforço visual, e o título já diz
        * tudo a quem ouve. Lido em voz alta viraria "seta curva". */}
      <p className={estilos.simbolo} aria-hidden="true">
        {simbolo}
      </p>

      <h2 className={estilos.titulo}>{titulo}</h2>
      <p className={estilos.frase}>{desfecho.detail}</p>

      {desfecho.ingresso && (
        <dl className={estilos.detalhes}>
          <div className={estilos.linha}>
            <dt>Filme</dt>
            <dd>{desfecho.ingresso.filme}</dd>
          </div>
          <div className={estilos.linha}>
            <dt>Sala</dt>
            <dd>{desfecho.ingresso.sala}</dd>
          </div>
          <div className={estilos.linha}>
            <dt>Lugar</dt>
            <dd className={estilos.lugar}>
              {desfecho.ingresso.assento.fileira}
              {desfecho.ingresso.assento.numero}
            </dd>
          </div>
          {/* SÓ NA MEIA, e só como informação. O operador lê e pede o
              documento — a plataforma vende, quem confere é ele. Este campo
              não decide desfecho nenhum: os quatro continuam sendo os quatro,
              e "meia sem documento" não existe no sistema (FR-024). */}
          {desfecho.ingresso.tipo === "meia" && (
            <div className={estilos.linha}>
              <dt>Tipo</dt>
              <dd>Meia-entrada — confira o documento</dd>
            </div>
          )}
          {desfecho.utilizado_em && (
            <div className={estilos.linha}>
              <dt>Usado às</dt>
              <dd>{horario(desfecho.utilizado_em)}</dd>
            </div>
          )}
        </dl>
      )}

      {desfecho.sessao_do_ingresso && (
        /* Sem isto o operador nega sem saber orientar a pessoa — e orientar é
         * a única coisa útil que ele pode fazer neste desfecho. */
        <dl className={estilos.detalhes}>
          <div className={estilos.linha}>
            <dt>Este ingresso é de</dt>
            <dd>{desfecho.sessao_do_ingresso.filme}</dd>
          </div>
          <div className={estilos.linha}>
            <dt>Sessão</dt>
            <dd>{diaEHora(desfecho.sessao_do_ingresso.inicio)}</dd>
          </div>
          <div className={estilos.linha}>
            <dt>Sala</dt>
            <dd>{desfecho.sessao_do_ingresso.sala}</dd>
          </div>
        </dl>
      )}
    </section>
  );
}
