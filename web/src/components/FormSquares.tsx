// A team's last results as squares, oldest first: V (win), E (draw), Î (loss), each in the
// colour validated for colour-blind readers, the letter carrying the result as well.
export function FormSquares({ results }: { results: string[] }) {
  const letters: Record<string, string> = { W: "V", D: "E", L: "Î" };
  return (
    <div className="form">
      {results.map((result, index) => (
        <span key={index} className={`form-square ${result}`}>
          {letters[result]}
        </span>
      ))}
    </div>
  );
}
