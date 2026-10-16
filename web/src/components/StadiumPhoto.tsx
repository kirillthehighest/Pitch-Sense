// The photo of a club's stadium (Wikipedia, collected by tools/stadiums.py), behind the head of a
// club or of a match; a club without one keeps its league's colour.
import { useEffect, useState } from "react";
import { imageUrl } from "../api";

export function StadiumPhoto({ team, className }: { team: string; className: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [shown, setShown] = useState(false);
  useEffect(() => {
    let live = true;
    setShown(false);
    imageUrl(`/api/images/stadium/${encodeURIComponent(team)}`).then((found) => live && setUrl(found));
    return () => {
      live = false;
    };
  }, [team]);
  if (!url) return null;
  return (
    <img
      className={`stadium-photo ${className}${shown ? " shown" : ""}`}
      src={url}
      alt=""
      onLoad={() => setShown(true)}
      onError={() => setUrl(null)}
    />
  );
}
