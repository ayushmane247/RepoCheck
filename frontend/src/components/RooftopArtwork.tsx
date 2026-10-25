interface ArtworkProps { className?: string; }

import { WebSlingerScene } from "./WebSlingerScene";

export function OpeningArtwork({ className = "" }: ArtworkProps) {
  return <WebSlingerScene className={className} />;
}

export function RooftopArtwork({ className = "" }: ArtworkProps) {
  return <WebSlingerScene className={className} />;
}
