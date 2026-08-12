import type { Ingresso as IngressoTipo } from "@/lib/types";

import estilos from "./tickets.module.css";

/**
 * Um ingresso — **um por lugar**, nunca um por reserva.
 *
 * O QR entra como `<img>` com `alt`, a partir de um `data:` URI que o servidor
 * montou. Não é `dangerouslySetInnerHTML`: a imagem vem de biblioteca nossa,
 * mas injetar markup no DOM para desenhar um quadrado é abrir uma porta que
 * não precisa existir.
 *
 * E o CÓDIGO EM TEXTO fica visível junto da imagem, sempre. É o que a portaria
 * digita quando a câmera falha ou é negada — alternativa que a constitution
 * exige que esteja "sempre disponível" —, e é o que resta se o QR não
 * carregar (FR-038).
 */

export type IngressoProps = {
  ingresso: IngressoTipo;
  /** Posição na lista, para quem lê com leitor de tela saber quantos são. */
  indice: number;
  total: number;
};

function formatarHorario(iso: string) {
  return new Intl.DateTimeFormat("pt-BR", {
    weekday: "long",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export default function Ingresso({ ingresso, indice, total }: IngressoProps) {
  const lugar = `${ingresso.assento.fileira}${ingresso.assento.numero}`;

  return (
    <li className={estilos.ingresso}>
      <div className={estilos.dados}>
        <p className={estilos.contagem}>
          Ingresso {indice} de {total}
        </p>
        <h3 className={estilos.filme}>{ingresso.filme}</h3>
        <p className={estilos.detalhe}>{formatarHorario(ingresso.sessao)}</p>
        <p className={estilos.detalhe}>
          {ingresso.sala} · lugar <strong className={estilos.lugar}>{lugar}</strong>
        </p>
      </div>

      <div className={estilos.codigo}>
        <img
          className={estilos.qr}
          src={ingresso.qr_svg}
          alt={`Código do ingresso do lugar ${lugar}, em QR`}
          width={160}
          height={160}
        />
        {/* O texto não é redundância do QR: é a via alternativa de leitura. */}
        <p className={estilos.codigoTexto}>
          <span className={estilos.codigoRotulo}>Código para digitação</span>
          <code className={estilos.codigoValor}>{ingresso.codigo}</code>
        </p>
      </div>
    </li>
  );
}
