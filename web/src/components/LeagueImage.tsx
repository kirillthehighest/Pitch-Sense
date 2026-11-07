// A card lit by the league's image: the image on the right at the screen's resolution, its strip
// starting at ``top`` (a share of its height, above the highest head), its left edge running into a
// fill made of its own edge colour mixed with the league's deep colour, so the seam disappears.
// Since Phase 26 the change of league is this image sliding in, not a repainted interface.
import { type ReactNode, useEffect, useRef, useState } from "react";
import { imageUrl } from "../api";

function mix(first: [number, number, number], second: string, share: number): string {
  const value = parseInt(second.slice(1), 16);
  const other = [(value >> 16) & 255, (value >> 8) & 255, value & 255];
  const channel = (index: number) => Math.round(first[index] + (other[index] - first[index]) * share);
  return `rgb(${channel(0)}, ${channel(1)}, ${channel(2)})`;
}

/** The average colour of the image's left edge over the strip shown, deepened towards the night. */
function edgeColour(image: HTMLImageElement, top: number): [number, number, number] | null {
  const canvas = document.createElement("canvas");
  const width = Math.max(1, Math.round(image.naturalWidth / 33));
  const strip = image.naturalWidth / 3.7;
  const y = Math.min(image.naturalHeight * top, image.naturalHeight - strip);
  canvas.width = 1;
  canvas.height = 1;
  const context = canvas.getContext("2d");
  if (!context) return null;
  try {
    context.drawImage(image, 0, y, width, strip, 0, 0, 1, 1);
    const [r, g, b] = context.getImageData(0, 0, 1, 1).data;
    return [r * 0.7 + 10 * 0.3, g * 0.7 + 10 * 0.3, b * 0.7 + 12 * 0.3];
  } catch {
    return null; // the image could not be read (another origin without permission)
  }
}

interface Props {
  code: string;
  top: number;
  credit: string | null;
  brand: string;
  share?: number; // the part of the card's width the image takes
  maxWidth?: number;
  className?: string;
  children: ReactNode;
}

export function LeagueImageCard({ code, top, credit, brand, share = 0.58, maxWidth = 760, className, children }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [fill, setFill] = useState(brand);
  const [frame, setFrame] = useState({ width: 0, height: 0 });
  const [natural, setNatural] = useState({ width: 1920, height: 1080 });
  const card = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    imageUrl(`/api/images/league/${code}`).then((found) => live && setUrl(found));
    setFill(brand);
    return () => {
      live = false;
    };
  }, [code, brand]);

  useEffect(() => {
    const element = card.current;
    if (!element) return;
    // The padding box, which the image fills: an observer's content box leaves the card's padding out
    const observer = new ResizeObserver(() =>
      setFrame({ width: element.clientWidth, height: element.clientHeight }),
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  const width = Math.min(frame.width * share, maxWidth);
  const scale = Math.max(width / natural.width, frame.height / natural.height);
  const shownHeight = natural.height * scale;
  const offset = Math.min(natural.height * top * scale, shownHeight - frame.height);

  return (
    <div ref={card} className={`image-card ${className ?? ""}`} style={{ background: fill }}>
      {url && (
        <div className="image-box" key={code} style={{ width }}>
          <img
            src={url}
            alt=""
            crossOrigin="anonymous"
            style={{ width: natural.width * scale, height: shownHeight, top: -offset }}
            onLoad={(event) => {
              const image = event.currentTarget;
              setNatural({ width: image.naturalWidth, height: image.naturalHeight });
              const edge = edgeColour(image, top);
              if (edge) setFill(mix(edge, brand, 0.5));
            }}
          />
          <div className="image-fade" style={{ background: `linear-gradient(90deg, ${fill} 0%, transparent 50%)` }} />
        </div>
      )}
      <div className="image-shade" />
      <div className="image-content">{children}</div>
      {credit && <span className="credit">{credit}</span>}
    </div>
  );
}
