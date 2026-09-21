import { vi } from "vitest";

vi.mock("next/navigation", async () => await import("./navMock"));
vi.mock("next/link", async () => ({ default: (await import("./navMock")).default }));
