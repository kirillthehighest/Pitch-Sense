import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { askUntilAnswered } from "./api";

describe("asking a server that is still starting", () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  function failing(times: number, answer: string) {
    let calls = 0;
    return () => {
      calls += 1;
      return calls <= times ? Promise.reject(new Error("Failed to fetch")) : Promise.resolve(answer);
    };
  }

  it("asks again quietly while it starts", async () => {
    const silent = vi.fn();
    const answer = askUntilAnswered(failing(2, "leagues"), silent, () => false, 1000, 3);

    await vi.advanceTimersByTimeAsync(2000);

    await expect(answer).resolves.toBe("leagues");
    expect(silent).not.toHaveBeenCalled();
  });

  it("says why once it stays silent, and goes on asking", async () => {
    const silent = vi.fn();
    const answer = askUntilAnswered(failing(4, "leagues"), silent, () => false, 1000, 3);

    await vi.advanceTimersByTimeAsync(4000);

    await expect(answer).resolves.toBe("leagues");
    expect(silent).toHaveBeenCalledTimes(2); // after the third and the fourth failure
    expect(silent).toHaveBeenLastCalledWith("Failed to fetch");
  });

  it("stops when the screen is gone", async () => {
    let gone = false;
    const answer = askUntilAnswered(failing(10, "leagues"), () => undefined, () => gone, 1000, 3);

    gone = true;
    await vi.advanceTimersByTimeAsync(1000);

    await expect(answer).resolves.toBeUndefined();
  });
});
