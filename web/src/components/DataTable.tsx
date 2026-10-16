// A table whose columns are measured once for all its rows (the team asked for tables with even,
// measured columns after Phase 21): a CSS grid with one width per column, the first column for
// names, the others for numbers, right-aligned in figures of equal width.
import type { ReactNode } from "react";

export interface Column {
  label: string;
  width: string; // a CSS grid track: "minmax(160px, 1fr)", "96px"...
  align?: "left" | "right" | "center";
}

interface Props {
  columns: Column[];
  rows: ReactNode[][];
  highlight?: (index: number) => boolean; // the league on screen, the best model...
  caption?: string;
}

export function DataTable({ columns, rows, highlight, caption }: Props) {
  const template = columns.map((column) => column.width).join(" ");
  const align = (index: number) => columns[index].align ?? (index === 0 ? "left" : "right");
  return (
    <div className="data-table" role="table" aria-label={caption}>
      <div className="data-row head" role="row" style={{ gridTemplateColumns: template }}>
        {columns.map((column, index) => (
          <span key={column.label} role="columnheader" style={{ textAlign: align(index) }}>
            {column.label}
          </span>
        ))}
      </div>
      {rows.map((cells, row) => (
        <div
          key={row}
          role="row"
          className={`data-row${highlight?.(row) ? " highlighted" : ""}`}
          style={{ gridTemplateColumns: template }}
        >
          {cells.map((cell, index) => (
            <span key={index} role="cell" style={{ textAlign: align(index) }}>
              {cell}
            </span>
          ))}
        </div>
      ))}
    </div>
  );
}
