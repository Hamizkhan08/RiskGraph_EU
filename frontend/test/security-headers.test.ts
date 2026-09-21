import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("security headers (next.config.ts)", () => {
  it("sets a restrictive CSP and standard headers on every route", async () => {
    const cfg = (await import("../next.config")).default;
    const rules = await cfg.headers!();
    expect(rules[0].source).toBe("/:path*");
    const h = Object.fromEntries(rules[0].headers.map((x) => [x.key, x.value]));
    expect(h["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
    expect(h["Content-Security-Policy"]).toContain("object-src 'none'");
    expect(h["Content-Security-Policy"]).toContain("connect-src 'self'");
    expect(h["X-Content-Type-Options"]).toBe("nosniff");
    expect(h["X-Frame-Options"]).toBe("DENY");
    expect(h["Referrer-Policy"]).toBeTruthy();
    expect(cfg.poweredByHeader).toBe(false);
  });

  it("allows exactly the configured API origin in connect-src and nothing broader", async () => {
    vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.example.org/");
    vi.resetModules();
    const { csp } = await import("../next.config");
    expect(csp).toContain("connect-src 'self' https://api.example.org;");
    expect(csp).not.toContain("*");
  });
});
