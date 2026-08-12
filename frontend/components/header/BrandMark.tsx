import Link from "next/link";

import { MarcaGrafica } from "./MarcaGrafica";
import styles from "./header.module.css";

/**
 * Identidade do site (FR-002).
 *
 * Wordmark textual, não imagem (R8): escala com o zoom, é selecionável e é
 * lido corretamente por leitor de tela sem precisar de texto alternativo.
 *
 * O sufixo `.com` é parte do nome, não uma URL.
 *
 * O DESTINO NEM SEMPRE É A HOME. Um papel de tela única — a portaria — não
 * alcança o catálogo, e uma marca que o levasse até lá só produziria um
 * redirecionamento de volta. Para ele a marca aponta para a própria tela.
 * **Este comportamento é da 010 e não pode se perder aqui**: ele não é óbvio
 * olhando um componente de logotipo, e `tests/marca.test.tsx` o guarda.
 *
 * A MARCA TEM DUAS PARTES desde a 011: o desenho e o nome. O desenho é
 * geometria própria em SVG e aparece sempre; o nome usa a família da marca e
 * some em tela estreita, onde o desenho sozinho já identifica o site.
 *
 * A VARIANTE COMPACTA É POR CSS, não por JavaScript: o cabeçalho é server
 * component, e decidir a variante no cliente faria a marca piscar entre as
 * duas formas no primeiro quadro.
 *
 * O `aria-label` não é redundante: o algoritmo de nome acessível insere um
 * espaço na fronteira entre elementos, e sem ele o link seria anunciado como
 * "ticket .com". A separação em dois elementos existe só para o tratamento
 * tipográfico e não pode vazar para o que o leitor de tela fala.
 */
export function BrandMark({ destino = "/" }: { destino?: string } = {}) {
  // O rótulo acompanha o destino. Dizer "ir para a página inicial" a quem vai
  // para a portaria descreveria a viagem errada — defeito que a 010 deixou ao
  // tornar o destino variável sem mexer no rótulo, e que só aparece para quem
  // usa leitor de tela.
  const paraOndeVai =
    destino === "/" ? "ir para a página inicial" : "ir para a tela de validação";

  return (
    <Link
      href={destino}
      className={styles.marca}
      aria-label={`ticket.com, ${paraOndeVai}`}
    >
      <MarcaGrafica className={styles.marcaDesenho} tamanho={1.35} />
      <span className={styles.marcaNome}>
        ticket<span className={styles.marcaSufixo}>.com</span>
      </span>
    </Link>
  );
}
