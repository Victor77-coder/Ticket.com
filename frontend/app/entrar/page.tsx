import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";

import { caminhoDeRetornoSeguro, getSessao } from "@/lib/session";
import styles from "./entrar.module.css";
import { LoginForm } from "./LoginForm";

export const metadata: Metadata = {
  title: "Entrar — ticket.com",
};

export default async function EntrarPage({
  searchParams,
}: {
  searchParams: Promise<{ next?: string }>;
}) {
  const { next } = await searchParams;

  // FR-011: só endereço interno. Validado no servidor, antes de descer para o
  // formulário — um destino externo aqui seria redirecionamento aberto.
  const caminhoDeRetorno = caminhoDeRetornoSeguro(next);

  // FR-008: quem já tem sessão não vê o formulário de novo.
  const sessao = await getSessao();
  if (sessao) {
    redirect(caminhoDeRetorno);
  }

  return (
    <main className={styles.pagina}>
      <div className={styles.cartao}>
        <Link href="/" className={styles.voltar}>
          ← Filmes em cartaz
        </Link>

        <h1 className={styles.titulo}>Entrar na sua conta</h1>
        <p className={styles.subtitulo}>
          Use suas credenciais para acompanhar compras e ingressos.
        </p>

        <LoginForm caminhoDeRetorno={caminhoDeRetorno} />

        <p className={styles.ajuda}>
          Ainda não é possível criar conta por aqui. As contas de demonstração estão listadas no
          README do projeto.
        </p>
      </div>
    </main>
  );
}
