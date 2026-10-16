// A club's crest from the server, or its three letters on a disc when it has none.
import { useEffect, useState } from "react";
import { imageUrl } from "../api";
import { abbreviation } from "../format";

export function Crest({ team, size = 24, ring = false }: { team: string; size?: number; ring?: boolean }) {
  const [url, setUrl] = useState<string | null>(null);
  const [missing, setMissing] = useState(false);
  useEffect(() => {
    let live = true;
    setMissing(false);
    imageUrl(`/api/images/crest/${encodeURIComponent(team)}`).then((found) => live && setUrl(found));
    return () => {
      live = false;
    };
  }, [team]);
  const style = {
    width: size,
    height: size,
    borderRadius: "50%",
    boxShadow: ring ? "0 0 0 2px var(--accent)" : undefined,
    flex: "none" as const,
  };
  if (missing || !url) {
    return (
      <span
        className="crest-letters"
        style={{ ...style, fontSize: size * 0.32 }}
        title={team}
      >
        {missing ? abbreviation(team) : ""}
      </span>
    );
  }
  return (
    <img
      src={url}
      alt=""
      title={team}
      width={size}
      height={size}
      style={{ ...style, objectFit: "contain", borderRadius: ring ? "50%" : 0 }}
      onError={() => setMissing(true)}
    />
  );
}
