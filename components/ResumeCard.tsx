// «Продолжить» on the cover (Vraja Lila msg 5316 p. 6, plan «Закладки» B2):
// where the reader stopped (lib/readingPlace.ts), drawn by an inline script
// BEFORE first paint (like READER_PREFS_SCRIPT) — the cover is sized for it
// from the start (html[data-home-resume], lib/homeCards.ts) and never jumps.
// The chapter / subsection line comes from this language's contents at show
// time (only the anchor is stored). The line wraps (2–3 lines for the longest
// titles, never «…»), the arrow › sits in the bottom-right corner (Vraja Lila
// msg 5430); the script measures the drawn card and reserves exactly its
// height (--home-resume-h) before first paint. First visit: no card. A tap opens the
// place (components/ResumeCardLink.tsx: the app's router; same language ->
// also the exact block). Server component.
import { getToc } from "@/lib/content";
import { READING_PLACE_KEY } from "@/lib/homeCards";
import { LANGUAGES, liveLang } from "@/lib/i18n";
import { BASE_PATH } from "@/lib/basePath";
import { DEFAULT_LANG } from "@/lib/i18n";
import ResumeCardLink from "@/components/ResumeCardLink";

function label(num: string | null, title: string) {
  return num ? `${num}. ${title}` : title;
}

export default function ResumeCard({ lang, title }: { lang: string; title: string }) {
  const toc = getToc(lang);
  // {section: [line, {anchor: line}]} — only what the card can show.
  const map: Record<string, [string, Record<string, string>]> = {};
  for (const s of toc) {
    const subs: Record<string, string> = {};
    for (const u of s.subsections) subs[u.id] = label(u.num, u.title);
    map[s.id] = [label(s.num, s.title), subs];
  }
  const prefix = `${BASE_PATH}${lang === DEFAULT_LANG ? "" : `/${lang}`}/`;
  const live = liveLang(lang);
  // a retired language stored with the place -> its replacement (lib/languages.json replacedBy)
  const retired = Object.fromEntries(LANGUAGES.filter((l) => l.replacedBy).map((l) => [l.code, l.replacedBy]));
  const script = `(function(){try{var d=document.documentElement,el=document.getElementById("home-resume");if(!el||!d.hasAttribute("data-home-resume"))return;var p=JSON.parse(localStorage.getItem(${JSON.stringify(
    READING_PLACE_KEY,
  )})||"null"),r=${JSON.stringify(retired)},m=${JSON.stringify(map)},s=p&&m[p.section];if(!s){d.removeAttribute("data-home-resume");d.style.removeProperty("--home-resume-h");return}var line=(p.anchor&&s[1][p.anchor])||s[0],a=document.createElement("a");a.className="home-resume";a.href=${JSON.stringify(
    prefix,
  )}+p.section+"/"+(p.anchor?"#"+p.anchor:"");a.setAttribute("data-section",p.section);if(p.anchor)a.setAttribute("data-anchor",p.anchor);if((r[p.lang]||p.lang)===${JSON.stringify(
    live,
  )})a.setAttribute("data-same-lang","");var t=document.createElement("span");t.className="home-resume-title";t.textContent=${JSON.stringify(
    title,
  )};var l=document.createElement("span");l.className="home-resume-line";l.textContent=line;a.appendChild(t);a.appendChild(l);var g=document.createElement("span");g.className="home-resume-arrow";g.setAttribute("aria-hidden","true");g.textContent="\u203A";a.appendChild(g);el.appendChild(a);d.style.setProperty("--home-resume-h",Math.ceil(el.getBoundingClientRect().height)+"px")}catch(e){try{document.documentElement.removeAttribute("data-home-resume");document.documentElement.style.removeProperty("--home-resume-h")}catch(_){}}})();`;
  return (
    <>
      {/* Filled by the script below before first paint; React leaves its inside alone. */}
      <div id="home-resume" className="home-resume-slot" dangerouslySetInnerHTML={{ __html: "" }} suppressHydrationWarning />
      <script dangerouslySetInnerHTML={{ __html: script }} />
      <ResumeCardLink script={script} />
    </>
  );
}
