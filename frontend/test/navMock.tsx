import { useSyncExternalStore, type AnchorHTMLAttributes, type ReactNode } from "react";

let url = "/";
const listeners = new Set<() => void>();
const notify = () => listeners.forEach((l) => l());
export const nav = {
  get url() {
    return url;
  },
  push(u: string) {
    url = u;
    notify();
  },
  reset(u = "/") {
    url = u;
    notify();
  },
};
const subscribe = (cb: () => void) => {
  listeners.add(cb);
  return () => listeners.delete(cb);
};
const useUrl = () => useSyncExternalStore(subscribe, () => url, () => url);
export const usePathname = () => useUrl().split("?")[0];
export const useSearchParams = () => new URLSearchParams(useUrl().split("?")[1] ?? "");
export const useParams = () => {
  const m = /^\/alerts\/([^/]+)$/.exec(usePathname());
  return m ? { id: m[1] } : {};
};
export const useRouter = () => ({ push: nav.push, replace: nav.push, back() {}, prefetch() {} });

export default function Link({ href, children, ...rest }: { href: string; children: ReactNode } & AnchorHTMLAttributes<HTMLAnchorElement>) {
  return (
    <a
      href={href}
      {...rest}
      onClick={(e) => {
        e.preventDefault();
        nav.push(href);
      }}
    >
      {children}
    </a>
  );
}
