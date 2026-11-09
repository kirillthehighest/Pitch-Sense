import { describe, expect, it } from "vitest";
import { revealFrames, wavyCircle } from "./reveal";

function points(polygon: string): [number, number][] {
  return polygon
    .slice("polygon(".length, -1)
    .split(", ")
    .map((point) => point.split(" ").map((value) => parseFloat(value)) as [number, number]);
}

describe("the wavy reveal of a league", () => {
  it("draws a circle when the waves are flat, a wavy one otherwise", () => {
    const flat = points(wavyCircle(10, 20, 100, 0, 0));
    expect(flat).toHaveLength(120);
    for (const [x, y] of flat) expect(Math.hypot(x - 10, y - 20)).toBeCloseTo(100, 0);
    const wavy = points(wavyCircle(0, 0, 100, 18, 0)).map(([x, y]) => Math.hypot(x, y));
    expect(Math.max(...wavy)).toBeGreaterThan(110);
    expect(Math.min(...wavy)).toBeLessThan(90);
  });

  it("grows from nothing to past the far corner, with the same points in every frame", () => {
    const frames = revealFrames(1440, 900);
    const first = points(frames[0].clipPath as string);
    const last = points(frames[frames.length - 1].clipPath as string);
    expect(first.every(([x, y]) => x === 0 && y === 0)).toBe(true);
    const nearest = Math.min(...last.map(([x, y]) => Math.hypot(x, y)));
    expect(nearest).toBeGreaterThan(Math.hypot(1440, 900)); // the whole window is uncovered
    expect(new Set(frames.map((frame) => points(frame.clipPath as string).length))).toEqual(new Set([120]));
  });
});
