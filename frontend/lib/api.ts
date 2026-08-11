/**
 * Acesso à API do Django — sempre no servidor.
 *
 * A home é Server Component e busca aqui durante a renderização (R5). O
 * navegador nunca fala com o Django direto, então nenhuma configuração de
 * back-end chega ao bundle.
 */

import type {
  ApiResult,
  HighlightsResponse,
  HomeRowsResponse,
  LoginResponse,
  MapaSessao,
  MovieDetail,
  SearchResponse,
  Sessao,
} from "./types";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 8000;

/** Nome do cookie de sessão, tanto no Django quanto no cookie que o Next emite. */
export const COOKIE_SESSAO = "sessionid";

type Opcoes = {
  /** Cabeçalhos extras — usado para repassar o cookie de sessão (R1). */
  headers?: Record<string, string>;
};

/**
 * Resultado de uma chamada que precisa distinguir o motivo da recusa.
 *
 * A entrada precisa do status: 401 é credencial inválida e 429 é limite de
 * tentativas, e as duas mensagens chegam prontas do Django em pt-BR.
 */
export type ApiResultComStatus<T> = ApiResult<T> & { status: number };

async function pedir<T>(
  path: string,
  init: RequestInit,
  opcoes: Opcoes = {},
): Promise<ApiResultComStatus<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: { Accept: "application/json", ...opcoes.headers, ...init.headers },
      // Boa parte do conteúdo depende do relógio (elegibilidade ao destaque) ou
      // da sessão. Uma resposta guardada serviria estado de outra pessoa.
      cache: "no-store",
    });

    if (response.status === 404) {
      return { ok: false, error: "NAO_ENCONTRADO", status: 404 };
    }

    if (!response.ok) {
      // O Django já devolve a frase em pt-BR; preservá-la evita traduzir
      // duas vezes a mesma regra.
      const corpo = await response.json().catch(() => null);
      return {
        ok: false,
        error: corpo?.detail ?? "Não foi possível completar a operação.",
        status: response.status,
      };
    }

    if (response.status === 204) {
      return { ok: true, data: undefined as T, status: 204 };
    }

    return { ok: true, data: (await response.json()) as T, status: response.status };
  } catch (error) {
    const abortou = error instanceof Error && error.name === "AbortError";
    return {
      ok: false,
      error: abortou
        ? "O servidor demorou demais para responder."
        : "Não foi possível falar com o servidor.",
      status: 0,
    };
  } finally {
    clearTimeout(timer);
  }
}

function getJson<T>(path: string, opcoes?: Opcoes): Promise<ApiResultComStatus<T>> {
  return pedir<T>(path, { method: "GET" }, opcoes);
}

function postJson<T>(path: string, corpo?: unknown, opcoes?: Opcoes): Promise<ApiResultComStatus<T>> {
  return pedir<T>(
    path,
    {
      method: "POST",
      headers: corpo === undefined ? {} : { "Content-Type": "application/json" },
      body: corpo === undefined ? undefined : JSON.stringify(corpo),
    },
    opcoes,
  );
}

export function fetchHighlights(): Promise<ApiResult<HighlightsResponse>> {
  return getJson<HighlightsResponse>("/api/v1/highlights/");
}

export function fetchMovie(slug: string): Promise<ApiResult<MovieDetail>> {
  return getJson<MovieDetail>(`/api/v1/filmes/${encodeURIComponent(slug)}/`);
}

/**
 * Busca de filmes por título.
 *
 * Chamada apenas pelo Route Handler `/api/busca`, nunca pelo navegador: no
 * Compose `API_BASE_URL` é `http://backend:8000`, um nome que só resolve
 * dentro da rede do Compose (R1).
 */
export function fetchSearch(termo: string, limite?: number): Promise<ApiResult<SearchResponse>> {
  const params = new URLSearchParams({ q: termo });
  if (limite !== undefined) params.set("limite", String(limite));

  return getJson<SearchResponse>(`/api/v1/busca/?${params}`);
}

// --- Autenticação ---------------------------------------------------------
// O navegador nunca chama estas funções: elas só rodam no servidor, a partir
// dos Route Handlers e de `lib/session.ts`. O cookie de sessão viaja no
// cabeçalho `Cookie` desta chamada servidor-a-servidor (R1).

/** Descreve a sessão de uma chave. Recusa (401) é estado normal, não falha. */
export function fetchSession(sessionKey: string): Promise<ApiResultComStatus<Sessao>> {
  return getJson<Sessao>("/api/v1/auth/me/", {
    headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` },
  });
}

export function postLogin(
  username: string,
  password: string,
): Promise<ApiResultComStatus<LoginResponse>> {
  return postJson<LoginResponse>("/api/v1/auth/login/", { username, password });
}

export function postLogout(sessionKey: string): Promise<ApiResultComStatus<void>> {
  return postJson<void>("/api/v1/auth/logout/", undefined, {
    headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` },
  });
}

/** As três trilhas da home em uma requisição (R4). */
export function fetchHomeRows(): Promise<ApiResult<HomeRowsResponse>> {
  return getJson<HomeRowsResponse>("/api/v1/home/");
}

// --- Mapa de assentos (feature 007) --------------------------------------

/**
 * O mapa de uma sessão.
 *
 * Público: não repassa cookie. Sala, sessão e assentos são dados locais, e a
 * resposta é idêntica com o TMDb fora do ar (FR-032).
 */
export function fetchSeatMap(id: number): Promise<ApiResultComStatus<MapaSessao>> {
  return getJson<MapaSessao>(`/api/v1/sessoes/${id}/mapa/`);
}
