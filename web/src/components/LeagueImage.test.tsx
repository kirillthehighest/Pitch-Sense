import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LeagueImageCard } from "./LeagueImage";

vi.mock("../api", () => ({ imageUrl: async () => "league.jpg" }));

// The match of the day: 248 px tall with 46 px of vertical and 56 px of horizontal padding
const CARD = { width: 700, height: 248, paddingX: 56, paddingY: 46 };

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function measuredCard(width: number) {
  vi.spyOn(HTMLElement.prototype, "clientWidth", "get").mockReturnValue(width);
  vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(CARD.height);
  vi.stubGlobal(
    "ResizeObserver",
    class {
      constructor(private report: ResizeObserverCallback) {}
      observe(target: Element) {
        // A real observer reports the content box, without the card's padding
        const contentRect = { width: width - CARD.paddingX, height: CARD.height - CARD.paddingY };
        this.report([{ target, contentRect } as ResizeObserverEntry], this as unknown as ResizeObserver);
      }
      disconnect() {}
    },
  );
}

async function shownImage(width: number): Promise<HTMLImageElement> {
  measuredCard(width);
  const { container } = render(
    <LeagueImageCard code="SP1" top={0.1} credit={null} brand="#6E140E">
      conținut
    </LeagueImageCard>,
  );
  await waitFor(() => expect(container.querySelector("img")).not.toBeNull());
  return container.querySelector("img") as HTMLImageElement;
}

describe("the league's image on a card", () => {
  it.each([560, 700, 900, 1400])("reaches the bottom of a %i px wide card", async (width) => {
    const image = await shownImage(width);
    const top = parseFloat(image.style.top);
    expect(parseFloat(image.style.height) + top).toBeGreaterThanOrEqual(CARD.height);
  });
});
