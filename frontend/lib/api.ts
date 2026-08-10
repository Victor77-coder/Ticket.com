/**
 * Acesso à API do Django — sempre no servidor.
 *
 * A home é Server Component e busca aqui durante a renderização (R5). O
 * navegador nunca fala com o Django direto, então nenhuma configuração de
 * back-end chega ao bundle.
 */

import type { ApiResult, HighlightsResponse, MovieDetail } from "./types";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const TIMEOUT_MS = 8000;

async function getJson<T>(path: string): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      signal: controller.signal,
      headers: { Accept: "application/json" },
      // A elegibilidade ao destaque depende de "sessão futura", que muda com o
      // relógio. Uma página estática mostraria destaque obsoleto (R5).
      cache: "no-store",
    });

    if (response.status === 404) {
      return { ok: false, error: "NAO_ENCONTRADO" };
    }

    if (!response.ok) {
      return {
        ok: false,
        error: "Não foi possível carregar os filmes em cartaz.",
      };
    }

    return { ok: true, data: (await response.json()) as T };
  } catch (error) {
    const abortou = error instanceof Error && error.name === "AbortError";
    return {
      ok: false,
      error: abortou
        ? "A sessão demorou demais para responder."
        : "Não foi possível falar com o servidor.",
    };
  } finally {
    clearTimeout(timer);
  }
}

export function fetchHighlights(): Promise<ApiResult<HighlightsResponse>> {
  return getJson<HighlightsResponse>("/api/v1/highlights/");
}

export function fetchMovie(slug: string): Promise<ApiResult<MovieDetail>> {
  return getJson<MovieDetail>(`/api/v1/filmes/${encodeURIComponent(slug)}/`);
}
