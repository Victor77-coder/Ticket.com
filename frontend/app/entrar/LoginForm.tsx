"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import styles from "./entrar.module.css";

type Props = {
  /** Destino após a entrada, já validado no servidor (FR-011). */
  caminhoDeRetorno: string;
};

type ErrosDeCampo = {
  username?: string;
  password?: string;
};

export function LoginForm({ caminhoDeRetorno }: Props) {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [errosDeCampo, setErrosDeCampo] = useState<ErrosDeCampo>({});
  const [enviando, setEnviando] = useState(false);

  async function aoEnviar(evento: React.FormEvent<HTMLFormElement>) {
    evento.preventDefault();

    const usuario = username.trim();
    const senha = password;

    // Validação antes de qualquer tentativa de autenticar (FR-006): campo
    // faltando é erro de formulário e não deve gastar o limite de tentativas.
    const erros: ErrosDeCampo = {};
    if (!usuario) erros.username = "Informe o usuário.";
    if (!senha) erros.password = "Informe a senha.";

    if (Object.keys(erros).length > 0) {
      setErrosDeCampo(erros);
      setErroGeral(null);
      return;
    }

    setErrosDeCampo({});
    setErroGeral(null);
    setEnviando(true);

    try {
      const resposta = await fetch("/api/entrar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: usuario, password: senha }),
      });

      if (!resposta.ok) {
        const corpo = await resposta.json().catch(() => null);
        setErroGeral(corpo?.detail ?? "Não foi possível entrar. Tente novamente.");
        // FR-005: o identificador fica, a senha nunca. Deixá-la no campo
        // mantém a credencial exposta na tela após uma recusa.
        setPassword("");
        setEnviando(false);
        return;
      }

      // `refresh` faz o cabeçalho reler a sessão no servidor antes da
      // navegação, senão o nome só apareceria depois de um recarregamento.
      router.replace(caminhoDeRetorno);
      router.refresh();
    } catch {
      setErroGeral("Não foi possível falar com o servidor. Verifique sua conexão.");
      setEnviando(false);
    }
  }

  return (
    <form onSubmit={aoEnviar} noValidate>
      {erroGeral && (
        <p className={styles.erroGeral} role="alert">
          {erroGeral}
        </p>
      )}

      <div className={styles.campos}>
        <div className={styles.campo}>
          <label className={styles.rotulo} htmlFor="username">
            Usuário
          </label>
          <input
            id="username"
            name="username"
            type="text"
            // Reconhecido por gerenciadores de senha do navegador (FR-030).
            autoComplete="username"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            className={`${styles.entrada} ${errosDeCampo.username ? styles.entradaComErro : ""}`}
            // O identificador é preservado após uma recusa; a senha nunca é
            // (FR-005).
            value={username}
            onChange={(evento) => setUsername(evento.target.value)}
            aria-invalid={errosDeCampo.username ? true : undefined}
            aria-describedby={errosDeCampo.username ? "erro-username" : undefined}
          />
          {errosDeCampo.username && (
            <span id="erro-username" className={styles.erroCampo}>
              {errosDeCampo.username}
            </span>
          )}
        </div>

        <div className={styles.campo}>
          <label className={styles.rotulo} htmlFor="password">
            Senha
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            className={`${styles.entrada} ${errosDeCampo.password ? styles.entradaComErro : ""}`}
            value={password}
            onChange={(evento) => setPassword(evento.target.value)}
            aria-invalid={errosDeCampo.password ? true : undefined}
            aria-describedby={errosDeCampo.password ? "erro-password" : undefined}
          />
          {errosDeCampo.password && (
            <span id="erro-password" className={styles.erroCampo}>
              {errosDeCampo.password}
            </span>
          )}
        </div>

        <button type="submit" className={styles.enviar} disabled={enviando}>
          {enviando ? "Entrando…" : "Entrar"}
        </button>
      </div>
    </form>
  );
}
