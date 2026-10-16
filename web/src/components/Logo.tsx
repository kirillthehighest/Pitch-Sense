// The PitchSense mark (Phase 21): PS in Kanit's black italic, cut by a rising slash, white above
// the cut and the league's accent below; beside it the wordmark PITCH white, SENSE in the accent.

const CUT = { left: 60, right: 44, gap: 9 }; // where the slash crosses the letters, in the viewBox

export function Mark({ height = 36 }: { height?: number }) {
  const above = `0,0 150,0 150,${CUT.right - CUT.gap / 2} 0,${CUT.left - CUT.gap / 2}`;
  const below = `0,${CUT.left + CUT.gap / 2} 150,${CUT.right + CUT.gap / 2} 150,110 0,110`;
  const letters = (
    <text x="2" y="91" fontFamily="Kanit" fontStyle="italic" fontWeight="900" fontSize="112" letterSpacing="-6">
      PS
    </text>
  );
  return (
    <svg height={height} viewBox="0 0 150 110" aria-label="PitchSense" role="img">
      <defs>
        <clipPath id="mark-above">
          <polygon points={above} />
        </clipPath>
        <clipPath id="mark-below">
          <polygon points={below} />
        </clipPath>
      </defs>
      <g clipPath="url(#mark-above)" fill="#FFFFFF">
        {letters}
      </g>
      <g clipPath="url(#mark-below)" fill="var(--accent)">
        {letters}
      </g>
    </svg>
  );
}

export function Lockup() {
  return (
    <div className="lockup">
      <Mark height={34} />
      <span className="wordmark">
        PITCH<span>SENSE</span>
      </span>
    </div>
  );
}
