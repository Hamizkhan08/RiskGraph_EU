import type { NextConfig } from "next";

/**
 * Security headers for every route. NEXT_PUBLIC_API_URL (public by design) is the only extra origin the browser may call.
 * script-src needs 'unsafe-inline' because Next.js injects inline hydration scripts; a nonce-based CSP would need
 * dynamic rendering (see docs/SECURITY_REVIEW.md). 'unsafe-eval' is allowed in development only.
 */
const api = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
const isProd = process.env.NODE_ENV === "production";

export const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self' data:",
  `connect-src 'self'${api ? ` ${api}` : ""}`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const nextConfig: NextConfig = {
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
        ],
      },
    ];
  },
};

export default nextConfig;
