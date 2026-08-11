import { HighlightsSkeleton } from "@/components/highlights/HighlightsSkeleton";
import { MovieRowSkeleton } from "@/components/rows/MovieRowSkeleton";

export default function Loading() {
  return (
    <main>
      <HighlightsSkeleton />
      <MovieRowSkeleton />
      <MovieRowSkeleton />
    </main>
  );
}
