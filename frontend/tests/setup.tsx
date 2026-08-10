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

// next/image exige o runtime do Next; nos testes basta um <img>.
vi.mock("next/image", () => ({
  default: ({ src, alt, ...resto }: { src: string; alt: string; [k: string]: unknown }) => {
    const { fill: _fill, priority: _priority, sizes: _sizes, ...limpo } = resto;
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...limpo} />;
  },
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...resto }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...resto}>
      {children}
    </a>
  ),
}));
