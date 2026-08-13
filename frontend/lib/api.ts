/**
 * Acesso à API do Django — sempre no servidor.
 *
 * A home é Server Component e busca aqui durante a renderização (R5). O
 * navegador nunca fala com o Django direto, então nenhuma configuração de
 * back-end chega ao bundle.
 */

import type {
  ApiResult,
  BuscaTmdbResponse,
  FilmeDoPainel,
  GradeResponse,
  HighlightsResponse,
  HomeRowsResponse,
  Ingresso,
  ListaDeFilmesDoPainel,
  ListaDeSalas,
  NovaSessao,
  SalaDoPainel,
  SessaoDaGrade,
  LinkDeCompartilhamento,
  ListaDeIngressos,
  Desfecho,
  SessaoDaPorta,
  LoginResponse,
  MapaSessao,
  MeuIngresso,
  MovieDetail,
  Reserva,
  SearchResponse,
  Sessao,
} from "./types";

const API_BASE_URL = process.env.API_BASE_URL ?? "http://localhost:8000";
const TIMEOUT_MS = Number(process.env.API_TIMEOUT_MS ?? 8000) || 8000;

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
        corpoErro: corpo,
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

/**
 * Cria a reserva. Só o Route Handler `/api/reservar` chama isto.
 *
 * O cookie viaja no cabeçalho desta chamada servidor-a-servidor: ele é
 * `httpOnly`, então script na página não o alcança, e sem o proxy ou o
 * cookie deixaria de ser `httpOnly` — reabrindo o que a 003 fechou — ou o
 * Django teria de aceitar CORS com credencial (R1).
 */
export function postReserva(
  sessionKey: string | undefined,
  corpo: { sessao: number; assentos: number[]; chave_idempotencia: string },
): Promise<ApiResultComStatus<Reserva>> {
  return postJson<Reserva>(
    "/api/v1/reservas/",
    corpo,
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

// --- Pagamento e ingresso (feature 008) ----------------------------------

/**
 * A reserva do dono, com pagamento e ingressos quando já foi paga.
 *
 * É esta chamada que faz a confirmação sobreviver a um recarregamento: os
 * ingressos não vivem em estado de componente, são lidos do servidor a cada
 * visita (FR-022).
 */
export function fetchReserva(
  sessionKey: string | undefined,
  id: number,
): Promise<ApiResultComStatus<Reserva>> {
  return getJson<Reserva>(
    `/api/v1/reservas/${id}/`,
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/** A lista de "Meus ingressos" do cliente autenticado. */
export function fetchMeusIngressos(
  sessionKey: string | undefined,
): Promise<ApiResultComStatus<ListaDeIngressos>> {
  return getJson<ListaDeIngressos>(
    "/api/v1/meus-ingressos/",
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/** Um ingresso do dono, com o estado do link de compartilhamento. */
export function fetchIngresso(
  sessionKey: string | undefined,
  id: string,
): Promise<ApiResultComStatus<MeuIngresso>> {
  return getJson<MeuIngresso>(
    `/api/v1/ingressos/${encodeURIComponent(id)}/`,
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/**
 * O ingresso de um link compartilhado. **Sem cookie de sessão, nunca.**
 *
 * A ausência do cookie não é esquecimento: a página é pública, não pede conta
 * e não conduz a nenhuma entrada (FR-036). Repassar a sessão faria a resposta
 * depender de quem está olhando, que é exatamente o que ela não pode fazer.
 */
export function fetchIngressoCompartilhado(
  token: string,
): Promise<ApiResultComStatus<Ingresso>> {
  return getJson<Ingresso>(
    `/api/v1/ingressos-compartilhados/${encodeURIComponent(token)}/`,
  );
}

/** Gera o link do ingresso. Idempotente: já havendo link ativo, devolve o mesmo. */
export function postLink(
  sessionKey: string | undefined,
  id: string,
): Promise<ApiResultComStatus<LinkDeCompartilhamento>> {
  return postJson<LinkDeCompartilhamento>(
    `/api/v1/ingressos/${encodeURIComponent(id)}/link/`,
    {},
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/** Revoga o link ativo. Idempotente: sem link ativo, devolve o mesmo estado. */
export function deleteLink(
  sessionKey: string | undefined,
  id: string,
): Promise<ApiResultComStatus<LinkDeCompartilhamento>> {
  return pedir<LinkDeCompartilhamento>(
    `/api/v1/ingressos/${encodeURIComponent(id)}/link/`,
    { method: "DELETE" },
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/** As sessões que este posto de portaria pode receber hoje. */
export function fetchSessoesDaPortaria(
  sessionKey: string | undefined,
): Promise<ApiResultComStatus<{ sessoes: SessaoDaPorta[] }>> {
  return getJson<{ sessoes: SessaoDaPorta[] }>(
    "/api/v1/portaria/sessoes/",
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/**
 * Valida um código contra a sessão da porta. Só o Route Handler chama isto.
 *
 * Os QUATRO desfechos voltam com `200` — nenhum deles é erro da requisição. A
 * portaria perguntou "posso deixar entrar?" e recebeu resposta.
 */
export function postValidacao(
  sessionKey: string | undefined,
  corpo: { codigo: string; sessao: number },
): Promise<ApiResultComStatus<Desfecho>> {
  return postJson<Desfecho>(
    "/api/v1/portaria/validar/",
    corpo,
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

/**
 * Cobra a reserva. Só o Route Handler `/api/pagar` chama isto.
 *
 * Este é o **único ponto do sistema por onde o número completo do cartão
 * passa**, e ele passa sem parar: nada aqui guarda, registra ou ecoa o corpo
 * (FR-011, R10).
 */
export function postPagamento(
  sessionKey: string | undefined,
  reserva: number,
  corpo: { numero: string; nome: string; validade: string; cvv: string },
): Promise<ApiResultComStatus<unknown>> {
  return postJson<unknown>(
    `/api/v1/reservas/${reserva}/pagamento/`,
    corpo,
    sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {},
  );
}

// --- Programação do organizador (feature 013) -----------------------------
//
// TODAS as chamadas desta seção repassam o cookie de sessão, e todas falam com
// endereços sob `/api/v1/programacao/`. O prefixo é a regra de autorização
// legível de fora: tudo ali exige o papel organizador, e um endpoint novo
// nasce coberto por estar ali (contracts/programacao-api.md).
//
// A distinção de status importa mais aqui do que em qualquer outra seção deste
// arquivo, e quem a consome é a página: `401` conduz à entrada, `403` RENDERIZA
// a recusa. Mandar um cliente à entrada por causa de um `403` é caminho sem
// saída — entrar de novo não muda o papel (R11).

function comSessao(sessionKey: string | undefined): Opcoes {
  return sessionKey ? { headers: { Cookie: `${COOKIE_SESSAO}=${sessionKey}` } } : {};
}

function patchJson<T>(
  path: string,
  corpo: unknown,
  opcoes?: Opcoes,
): Promise<ApiResultComStatus<T>> {
  return pedir<T>(
    path,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(corpo),
    },
    opcoes,
  );
}

/** A grade inteira — os três estados. É a leitura que a área de trabalho pousa. */
export function fetchGrade(
  sessionKey: string | undefined,
): Promise<ApiResultComStatus<GradeResponse>> {
  return getJson<GradeResponse>("/api/v1/programacao/sessoes/", comSessao(sessionKey));
}

/** O catálogo LOCAL, para programar sem depender do TMDb (FR-013, FR-014). */
export function fetchFilmesDoPainel(
  sessionKey: string | undefined,
): Promise<ApiResultComStatus<ListaDeFilmesDoPainel>> {
  return getJson<ListaDeFilmesDoPainel>(
    "/api/v1/programacao/filmes/",
    comSessao(sessionKey),
  );
}

/**
 * Busca no TMDb — **pelo back-end**.
 *
 * A chave da API nunca sai do Django (FR-010), e o `502` traz a frase que o
 * `TMDBError` já escreve em português. Não traduzir de novo: seriam duas
 * redações da mesma falha.
 */
export function fetchBuscaTmdb(
  sessionKey: string | undefined,
  termo: string,
): Promise<ApiResultComStatus<BuscaTmdbResponse>> {
  return getJson<BuscaTmdbResponse>(
    `/api/v1/programacao/filmes/busca/?q=${encodeURIComponent(termo)}`,
    comSessao(sessionKey),
  );
}

/** Importa um filme do TMDb. `201` criou, `200` já existia — nunca erro (FR-012). */
export function postImportarFilme(
  sessionKey: string | undefined,
  tmdbId: number,
): Promise<ApiResultComStatus<FilmeDoPainel>> {
  return postJson<FilmeDoPainel>(
    "/api/v1/programacao/filmes/",
    { tmdb_id: tmdbId },
    comSessao(sessionKey),
  );
}

export function fetchSalas(
  sessionKey: string | undefined,
): Promise<ApiResultComStatus<ListaDeSalas>> {
  return getJson<ListaDeSalas>("/api/v1/programacao/salas/", comSessao(sessionKey));
}

export function postSala(
  sessionKey: string | undefined,
  corpo: { nome: string; capacidade: number },
): Promise<ApiResultComStatus<SalaDoPainel>> {
  return postJson<SalaDoPainel>("/api/v1/programacao/salas/", corpo, comSessao(sessionKey));
}

/**
 * Renomeia ou troca a capacidade.
 *
 * O `409` da sala com ocupação viva vem daqui inteiro, com a frase que diz
 * quantos lugares estão ocupados — a interface não a reescreve.
 */
export function patchSala(
  sessionKey: string | undefined,
  id: number,
  corpo: { nome?: string; capacidade?: number },
): Promise<ApiResultComStatus<SalaDoPainel>> {
  return patchJson<SalaDoPainel>(
    `/api/v1/programacao/salas/${id}/`,
    corpo,
    comSessao(sessionKey),
  );
}

export function postSessao(
  sessionKey: string | undefined,
  corpo: NovaSessao,
): Promise<ApiResultComStatus<SessaoDaGrade>> {
  return postJson<SessaoDaGrade>(
    "/api/v1/programacao/sessoes/",
    corpo,
    comSessao(sessionKey),
  );
}

/** Só rascunho. Publicada ou cancelada volta `409` com a frase do servidor. */
export function patchSessao(
  sessionKey: string | undefined,
  id: number,
  corpo: Partial<Omit<NovaSessao, "publicar">>,
): Promise<ApiResultComStatus<SessaoDaGrade>> {
  return patchJson<SessaoDaGrade>(
    `/api/v1/programacao/sessoes/${id}/`,
    corpo,
    comSessao(sessionKey),
  );
}

/**
 * Publicar e cancelar são AÇÕES, não `PATCH status`.
 *
 * Cada uma carrega pré-condições próprias — horário futuro e sala com lugares;
 * estado não terminal — que um campo de status esconderia dentro de validação
 * de campo (R8).
 */
export function postAcaoDeSessao(
  sessionKey: string | undefined,
  id: number,
  acao: "publicar" | "cancelar",
): Promise<ApiResultComStatus<SessaoDaGrade>> {
  return postJson<SessaoDaGrade>(
    `/api/v1/programacao/sessoes/${id}/${acao}/`,
    {},
    comSessao(sessionKey),
  );
}
