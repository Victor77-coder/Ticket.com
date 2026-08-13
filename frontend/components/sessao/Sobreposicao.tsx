"use client";

import { useEffect, useRef } from "react";

import estilos from "./sessao.module.css";

/**
 * A sobreposição dos dois painéis do cartão — assentos e preços.
 *
 * A BASE É `<dialog>` NATIVO, e não uma biblioteca. Trazer uma para dois painéis
 * contradiria a disciplina de tokens da 006: componente de terceiro chega com
 * espaçamento, raio e transição próprios, que é exatamente o que
 * `tokens.test.ts` reprova.
 *
 * O nativo já entrega duas das quatro regras — `Esc` fecha, e o foco fica preso
 * enquanto o modal está aberto. Este componente existe pelas outras duas:
 *
 *   M4 — DEVOLVER O FOCO à ação que abriu. É a que quase sempre falta, e é
 *        invisível para quem usa mouse: a pessoa fecha o painel e o foco
 *        reaparece no topo da página, com a navegação por teclado perdida.
 *   M5 — ser anunciada como diálogo ROTULADO, ligando o título ao elemento.
 *
 * M6 (um painel por vez) é do consumidor, não daqui: o cartão guarda **qual**
 * painel está aberto num estado só, então abrir um fecha o outro por construção.
 */

type Props = {
  aberta: boolean;
  titulo: string;
  subtitulo?: string;
  aoFechar: () => void;
  children: React.ReactNode;
};

export default function Sobreposicao({ aberta, titulo, subtitulo, aoFechar, children }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const origemRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog || !aberta) return;

    // Guardado ANTES de mover o foco: depois de `showModal` o elemento ativo já
    // é outro, e a origem estaria perdida.
    origemRef.current = document.activeElement as HTMLElement | null;

    // `showModal` não existe em toda parte: o jsdom 25 — o ambiente dos testes
    // — não implementa `<dialog>`, e navegadores anteriores a 2022 também não.
    // Onde falta, o atributo `open` deixa o conteúdo presente e acessível; o
    // que se perde é o véu e a inércia do fundo, que são acabamento.
    if (typeof dialog.showModal === "function") {
      dialog.showModal();
    } else {
      dialog.setAttribute("open", "");
    }

    // Explícito, e não pelo comportamento padrão do `<dialog>`: o padrão foca o
    // primeiro elemento focável, que aqui seria o botão de fechar — anunciar
    // "Fechar" como primeira coisa do painel diz o que abandonar antes de dizer
    // o que se está vendo.
    dialog.focus();

    return () => {
      // Mesmo guarda da abertura, e pelo mesmo motivo: onde `<dialog>` não é
      // implementado, `close` também não existe. Remover o atributo fecha os
      // dois caminhos.
      if (typeof dialog.close === "function" && dialog.open) dialog.close();
      dialog.removeAttribute("open");
      // M4. O `?.` cobre a origem que saiu da árvore enquanto o painel estava
      // aberto — devolver foco a um elemento removido lançaria.
      origemRef.current?.focus?.();
    };
  }, [aberta]);

  if (!aberta) return null;

  const idTitulo = "sobreposicao-titulo";

  return (
    <dialog
      ref={dialogRef}
      className={estilos.sobreposicao}
      aria-labelledby={idTitulo}
      tabIndex={-1}
      // O `<dialog>` emite `close` também quando o navegador fecha por `Esc`,
      // sem passar por nenhum manipulador nosso. É por aqui que o `Esc` chega.
      onClose={aoFechar}
      onCancel={(evento) => {
        evento.preventDefault();
        aoFechar();
      }}
      // Sem `showModal` não há `Esc` nativo — o ouvinte cobre o mesmo gesto.
      onKeyDown={(evento) => {
        if (evento.key === "Escape") {
          evento.preventDefault();
          aoFechar();
        }
      }}
    >
      <div className={estilos.sobreposicaoCabecalho}>
        <div>
          <h2 className={estilos.sobreposicaoTitulo} id={idTitulo}>
            {titulo}
          </h2>
          {subtitulo && <p className={estilos.sobreposicaoSubtitulo}>{subtitulo}</p>}
        </div>
        <button
          type="button"
          className={estilos.fechar}
          onClick={aoFechar}
          aria-label={`Fechar ${titulo}`}
        >
          <span aria-hidden="true">×</span>
        </button>
      </div>

      <div className={estilos.sobreposicaoCorpo}>{children}</div>
    </dialog>
  );
}
