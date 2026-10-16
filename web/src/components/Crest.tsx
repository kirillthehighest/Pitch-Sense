// A club's crest from the server, or its three letters on a disc when it has none. As in the
// window, a dark crest sits on a light disc, and "your team" gets a ring in the league's accent;
// either way the crest shrinks inside the disc.
import { useEffect, useState } from "react";
import { imageUrl } from "../api";
import { CREST_DISC, isDark } from "../colour";
import { abbreviation } from "../format";

const SAMPLE = 48; // the crest is measured at this size
const darkness = new Map<string, Promise<boolean>>();

function measure(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    const image = new Image();
    image.crossOrigin = "anonymous";
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = canvas.height = SAMPLE;
      const context = canvas.getContext("2d");
      if (!context) return resolve(false);
      context.drawImage(image, 0, 0, SAMPLE, SAMPLE);
      try {
        resolve(isDark(context.getImageData(0, 0, SAMPLE, SAMPLE).data));
      } catch {
        resolve(false); // a canvas the page may not read: keep the crest as it is
      }
    };
    image.onerror = () => resolve(false);
    image.src = url;
  });
}

function isDarkCrest(url: string): Promise<boolean> {
  let found = darkness.get(url);
  if (!found) {
    found = measure(url);
    darkness.set(url, found);
  }
  return found;
}

export function Crest({ team, size = 24, ring = false }: { team: string; size?: number; ring?: boolean }) {
  const [url, setUrl] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let live = true;
    setMissing(false);
    setDark(false);
    imageUrl(`/api/images/crest/${encodeURIComponent(team)}`).then((found) => {
      if (!live) return;
      setUrl(found);
      isDarkCrest(found).then((value) => live && setDark(value));
    });
    return () => {
      live = false;
    };
  }, [team]);
  const ringWidth = Math.max(1.5, size / 20);
  const style = {
    width: size,
    height: size,
    borderRadius: "50%",
    background: dark && !missing ? CREST_DISC : undefined,
    boxShadow: ring ? `inset 0 0 0 ${ringWidth}px var(--accent)` : undefined,
  };
  if (missing || !url) {
    return (
      <span className="crest crest-letters" style={{ ...style, fontSize: size * 0.32 }} title={team}>
        {missing ? abbreviation(team) : ""}
      </span>
    );
  }
  const inner = ring || dark ? Math.round(size * 0.66) : size;
  return (
    <span className="crest" style={style} title={team}>
      <img
        src={url}
        alt=""
        crossOrigin="anonymous"
        width={inner}
        height={inner}
        style={{ objectFit: "contain" }}
        onError={() => setMissing(true)}
      />
    </span>
  );
}
