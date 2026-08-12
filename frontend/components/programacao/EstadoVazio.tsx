import Link from "next/link";

import estilos from "./programacao.module.css";

/**
 * O estado vazio de qualquer superfície da área de programação.
 *
 * FR-007 exige sucesso, erro e vazio em TODA superfície, e o vazio é o que
 * costuma faltar: uma tela em branco não é neutra, ela parece defeito. Aqui ele
 * diz o que não existe ainda e oferece a próxima ação — nunca só "nada por
 * aqui".
 *
 * Um componente só para os três casos (grade, salas, busca) porque a diferença
 * entre eles é texto, não estrutura. Três componentes iguais divergiriam na
 * primeira revisão de redação.
 */

type Props = {
  titulo: string;
  texto: string;
  acao?: { href: string; rotulo: string };
};

export function EstadoVazio({ titulo, texto, acao }: Props) {
  return (
    <section className={estilos.vazio}>
      <h2 className={estilos.vazioTitulo}>{titulo}</h2>
      <p className={estilos.vazioTexto}>{texto}</p>
      {acao && (
        <Link href={acao.href} className={estilos.acao}>
          {acao.rotulo}
        </Link>
      )}
    </section>
  );
}
