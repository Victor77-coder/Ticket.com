import styles from "./header.module.css";

/**
 * A marca gráfica de `ticket.com`.
 *
 * DE ONDE ELA VEM. O nome tem uma única pontuação — o ponto do `.com` —, e ele
 * já era elemento de marca desde a 002, onde o sufixo sai na cor de destaque.
 * A logo não inventa um símbolo: promove o que o nome já tem. É o `t` inicial,
 * e o ponto que o nome carrega, sentado no ponto de partida do traço.
 *
 * POR QUE NÃO UM ÍCONE DE INGRESSO, CLAQUETE OU PIPOCA. Esses três são o
 * vocabulário de biblioteca do domínio: qualquer um deles seria intercambiável
 * com o de qualquer outro cinema, que é o oposto de marca. O `t` com ponto só
 * significa alguma coisa para ESTE nome.
 *
 * POR QUE GEOMETRIA PRÓPRIA, E NÃO O `t` DA FONTE VETORIZADO. Duas razões, e a
 * segunda só apareceu ao ler a licença:
 *
 *   1. Como caminho desenhado por nós, a marca aparece igual no primeiro
 *      quadro — não espera fonte nenhuma — e serve como ícone de aba, onde não
 *      existe fonte.
 *   2. A EULA da Fontshare concede criar logos (§01), mas o §05 diz que
 *      "any derivative works are the exclusive property of the Licensor". Um
 *      `t` vetorizado da Cabinet Grotesk seria trabalho derivado, e a marca do
 *      produto passaria a ser propriedade do licenciador da fonte.
 *
 * O NOME por extenso continua usando a fonte como TEXTO, que é o uso mais
 * direto que a licença concede e não cria derivado nenhum.
 *
 * SEM BRILHO, HALO OU SOMBRA. O destaque tem 5.64:1 sobre o fundo escuro — a
 * marca não precisa de efeito para se destacar, e efeito é item proibido do
 * contrato anti-slop.
 */

type Props = {
  /** Lado do quadrado, em unidades de `em` do contexto. */
  tamanho?: number;
  className?: string;
};

export function MarcaGrafica({ tamanho = 1, className }: Props) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={`${tamanho}em`}
      height={`${tamanho}em`}
      className={className}
      // A marca é decorativa AQUI: quem nomeia o site é o rótulo do link que a
      // envolve. Anunciá-la também faria o leitor de tela dizer o nome duas
      // vezes.
      aria-hidden="true"
      focusable="false"
    >
      {/* A haste e a barra do `t` — traços retos, sem serifa, com a mesma
        * inclinação de terminal que o resto da marca não tem: nenhuma. */}
      <path
        d="M11 3 v14.2 a3.8 3.8 0 0 0 3.8 3.8 H18"
        fill="none"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="square"
      />
      <path d="M5 8.5 H17" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="square" />

      {/* O ponto do `.com`, no destaque. É o único elemento colorido da marca,
        * e é o que a liga ao nome. */}
      <circle cx="5" cy="19.2" r="2.6" className={styles.marcaPonto} />
    </svg>
  );
}
