import "@testing-library/jest-dom/vitest";

import { vi } from "vitest";

// jsdom não implementa matchMedia, e o carrossel consulta prefers-reduced-motion
// para decidir se rotaciona sozinho (FR-011).
type OuvinteDeMedia = (evento: MediaQueryListEvent) => void;

const ouvintes = new Map<string, Set<OuvinteDeMedia>>();
let consultasQueCasam = new Set<string>();

export function definirMediaQuery(consulta: string, casa: boolean) {
  if (casa) consultasQueCasam.add(consulta);
  else consultasQueCasam.delete(consulta);

  ouvintes.get(consulta)?.forEach((ouvinte) => {
    ouvinte({ matches: casa, media: consulta } as MediaQueryListEvent);
  });
}

export function limparMediaQueries() {
  consultasQueCasam = new Set();
  ouvintes.clear();
}

Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (consulta: string): MediaQueryList =>
    ({
      media: consulta,
      get matches() {
        return consultasQueCasam.has(consulta);
      },
      onchange: null,
      // A assinatura real de addEventListener é sobrecarregada e aceita
      // EventListenerObject; o mock só precisa da forma de função.
      addEventListener: (_evento: string, ouvinte: unknown) => {
        if (!ouvintes.has(consulta)) ouvintes.set(consulta, new Set());
        ouvintes.get(consulta)!.add(ouvinte as OuvinteDeMedia);
      },
      removeEventListener: (_evento: string, ouvinte: unknown) => {
        ouvintes.get(consulta)?.delete(ouvinte as OuvinteDeMedia);
      },
      addListener: () => {},
      removeListener: () => {},
      dispatchEvent: () => false,
    }) as unknown as MediaQueryList,
});

// jsdom não faz layout, então não implementa rolagem programática. As setas da
// trilha chamam scrollBy, e sem isto o clique estoura um erro não tratado que a
// suíte reporta separado dos testes — verde com "Errors 1" no rodapé. O que o
// teste afirma é a navegação por teclado e a existência das setas; a rolagem em
// si é comportamento do navegador, coberta no e2e.
if (!Element.prototype.scrollBy) {
  Element.prototype.scrollBy = () => {};
}

// next/image exige o runtime do Next; nos testes basta um <img>.
vi.mock("next/image", () => ({
  default: ({ src, alt, ...resto }: { src: string; alt: string; [k: string]: unknown }) => {
    const { fill: _fill, priority: _priority, sizes: _sizes, ...limpo } = resto;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...limpo} />;
  },
}));

// O App Router não existe fora do runtime do Next. A busca navega por
// router.push; nos testes registramos o destino e o e2e cobre a navegação real.
// A fábrica do vi.mock é avaliada na primeira importação de next/navigation,
// já com este módulo carregado — a closure abaixo é segura.
export const rotasVisitadas: string[] = [];

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: (href: string) => {
      rotasVisitadas.push(href);
    },
    replace: () => {},
    prefetch: () => {},
    back: () => {},
    forward: () => {},
    refresh: () => {},
  }),
  usePathname: () => "/",
  useSearchParams: () => new URLSearchParams(),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...resto }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...resto}>
      {children}
    </a>
  ),
}));
