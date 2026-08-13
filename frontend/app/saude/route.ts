/**
 * Sonda de vida do front-end. Não fala com o Django: se o health check
 * dependesse da API, os dois serviços nunca subiriam juntos na primeira vez.
 */
export const dynamic = "force-dynamic";

export function GET() {
  return new Response("ok", { status: 200, headers: { "content-type": "text/plain" } });
}
