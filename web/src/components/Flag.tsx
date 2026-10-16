// The round flags of the leagues' countries (docs/brand.md, 2.4).
const FLAGS: Record<string, { kind: "cross" | "spain" | "vertical" | "horizontal"; colours: string[] }> = {
  E0: { kind: "cross", colours: ["#FFFFFF", "#CE1124"] },
  SP1: { kind: "spain", colours: ["#AA151B", "#F1BF00"] },
  I1: { kind: "vertical", colours: ["#009246", "#F1F2F1", "#CE2B37"] },
  D1: { kind: "horizontal", colours: ["#000000", "#DD0000", "#FFCE00"] },
  F1: { kind: "vertical", colours: ["#0055A4", "#F1F2F1", "#EF4135"] },
};

export function Flag({ code, size = 24 }: { code: string; size?: number }) {
  const flag = FLAGS[code];
  const id = `flag-${code}`;
  if (!flag) return <span style={{ width: size, height: size }} />;
  const { kind, colours } = flag;
  const step = 100 / colours.length;
  return (
    <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden>
      <defs>
        <clipPath id={id}>
          <circle cx="50" cy="50" r="50" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id})`}>
        {kind === "cross" && (
          <>
            <rect width="100" height="100" fill={colours[0]} />
            <rect y="39" width="100" height="22" fill={colours[1]} />
            <rect x="39" width="22" height="100" fill={colours[1]} />
          </>
        )}
        {kind === "spain" && (
          <>
            <rect width="100" height="100" fill={colours[0]} />
            <rect y="25" width="100" height="50" fill={colours[1]} />
          </>
        )}
        {(kind === "vertical" || kind === "horizontal") &&
          colours.map((colour, index) =>
            kind === "vertical" ? (
              <rect key={colour + index} x={index * step} width={step + 0.5} height="100" fill={colour} />
            ) : (
              <rect key={colour + index} y={index * step} width="100" height={step + 0.5} fill={colour} />
            ),
          )}
      </g>
      <circle cx="50" cy="50" r="49" fill="none" stroke="rgba(255,255,255,0.24)" strokeWidth="2" />
    </svg>
  );
}
