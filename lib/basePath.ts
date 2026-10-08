/**
 * Where the app is served (Next `basePath`), without a trailing slash.
 * Production: "/arcana-paddhati". Staging build (workflow, branch `staging`):
 * "/arcana-paddhati/staging" via the env var NEXT_PUBLIC_BASE_PATH at build
 * time (next.config.ts reads the same variable and inlines it).
 * Use it for every URL Next does not prefix itself (plain <a>, <img>, fetch,
 * metadata icons, service worker registration).
 */
export const BASE_PATH: string = process.env.NEXT_PUBLIC_BASE_PATH || "/arcana-paddhati";

/** "/arcana-paddhati/ru-iast/x/" -> "/ru-iast/x/" (unchanged if not under BASE_PATH). */
export function stripBasePath(pathname: string): string {
  if (pathname === BASE_PATH) return "";
  return pathname.startsWith(BASE_PATH + "/") ? pathname.slice(BASE_PATH.length) : pathname;
}
