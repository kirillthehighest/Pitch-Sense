import { describe, expect, it } from "vitest";
import { setChosenModel } from "./chosenModel";
import { MODELS } from "./types";

describe("the chosen model", () => {
  it("is one value for the whole app, set by name or from the current one", async () => {
    const { useChosenModel } = await import("./chosenModel");
    expect(typeof useChosenModel).toBe("function");
    setChosenModel("Elo");
    let seen = "";
    setChosenModel((current) => {
      seen = current;
      return MODELS[0];
    });
    expect(seen).toBe("Elo");
  });
});
