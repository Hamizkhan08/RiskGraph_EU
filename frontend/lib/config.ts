/** NEXT_PUBLIC_* values are visible to the browser by design; never put secrets here. */
export const API_URL: string = (process.env.NEXT_PUBLIC_API_URL ?? "").replace(/\/$/, "");
export const LIVE_AVAILABLE: boolean = API_URL.length > 0;
export const DISCLOSURE =
  "RiskGraph EU is a research prototype for financial-risk and financial-crime alert prioritisation using public/synthetic data. It is not a replacement for AML investigators, compliance systems, law enforcement, or regulatory validation.";
