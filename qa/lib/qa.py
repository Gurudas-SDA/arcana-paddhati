"""Shared QA helpers: repo paths, device profiles, freshness of out/.

Every suite in qa/suites imports this module (sys.path is set by run_all.py,
or by the suite itself when run directly).
"""
import os
import sys
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

QA_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("QA_REPO") or os.path.dirname(QA_DIR)
OUT = os.path.join(REPO, "out")
DATA = os.path.join(REPO, "data")
PREFIX = "/arcana-paddhati"

IOS_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 "
          "(KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1")
IPAD_UA = IOS_UA.replace("iPhone; CPU iPhone OS", "iPad; CPU OS")
PIXEL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Mobile Safari/537.36")
S23_UA = ("Mozilla/5.0 (Linux; Android 14; SM-S711B) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/130.0.0.0 Mobile Safari/537.36")
MAC_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) "
          "Version/18.0 Safari/605.1.15")

# Canonical device profiles (Правила интерфейса §5, §8: Android + iPhone, iPad
# portrait/landscape (Mini / normal / Pro), Windows + Mac computers, S23 FE).
DEVICES = {
    "pixel7": ("chromium", dict(viewport={"width": 412, "height": 915}, has_touch=True, is_mobile=True, device_scale_factor=2.625, user_agent=PIXEL_UA)),
    "s23fe": ("chromium", dict(viewport={"width": 360, "height": 780}, has_touch=True, is_mobile=True, device_scale_factor=3, user_agent=S23_UA)),
    "iphone14": ("webkit", dict(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True, device_scale_factor=3, user_agent=IOS_UA)),
    "iphone-se": ("webkit", dict(viewport={"width": 375, "height": 667}, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IOS_UA)),
    "ipad-portrait": ("webkit", dict(viewport={"width": 820, "height": 1180}, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IPAD_UA)),
    "ipad-landscape": ("webkit", dict(viewport={"width": 1180, "height": 820}, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IPAD_UA)),
    "ipad-mini": ("webkit", dict(viewport={"width": 744, "height": 1133}, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IPAD_UA)),
    "ipad-pro": ("webkit", dict(viewport={"width": 1024, "height": 1366}, has_touch=True, is_mobile=True, device_scale_factor=2, user_agent=IPAD_UA)),
    "desktop": ("chromium", dict(viewport={"width": 1440, "height": 900})),
    "mac-safari": ("webkit", dict(viewport={"width": 1440, "height": 900}, user_agent=MAC_UA)),
}

# Devices of the fast (pre-push) run: one Android phone (Chromium) and one
# iPhone (WebKit) — the two engines Satkirti reads on.
FAST_DEVICES = ["pixel7", "iphone14"]

TOC_MODE_NAME = "default"


@dataclass(frozen=True)
class TocMode:
    name: str

    @property
    def one(self):
        return self.name == "default"

    def start(self, page, url):
        """Use the app's real query flag, then keep reading URLs comparable.

        The app resolves and remembers ?toc=two once per page load. Removing
        only this setup query adds no history entry and leaves that choice on.
        Default checks use a fresh context without either query or preference.
        """
        if self.one:
            page.goto(url, wait_until="networkidle")
        else:
            parts = urlsplit(url)
            query = dict(parse_qsl(parts.query))
            query["toc"] = "two"
            page.goto(urlunsplit(parts._replace(query=urlencode(query))), wait_until="networkidle")
            page.wait_for_function("localStorage.getItem('ap.tocTap') === 'two'")
            page.evaluate("""() => {
              const url = new URL(location.href); url.searchParams.delete('toc');
              history.replaceState(history.state, '', url.pathname + url.search + url.hash);
            }""")


def run_toc_modes(check_body, on_error=None):
    """Run the same check body with default and legacy expectations.

    The harness schedules each mode separately within its unchanged timeout;
    direct suite execution runs both. QA_TOC_MODE only partitions coverage.
    It never changes the app flag: TocMode.start uses the existing query.
    """
    global TOC_MODE_NAME
    selected = os.environ.get("QA_TOC_MODE")
    if selected and selected not in ("default", "two"):
        raise ValueError(f"Unknown QA_TOC_MODE: {selected}")
    # The two-tap mode was removed from the app (Satkirti 13.10.2026), so only
    # the default mode is run. The legacy branches in the suites stay until
    # each one is rewritten, and are no longer reached.
    for name in ((selected,) if selected else ("default",)):
        TOC_MODE_NAME = name
        try:
            check_body(TocMode(name))
        except Exception as error:
            if on_error is None:
                raise
            on_error(error)

# A chapter route can display the continuous book. Content measurements
# must use its current chapter, rather than the first article in the book.
# Standalone exports retain .app-main as their measurement root.
READING_ROOT_JS = """(() => {
  const main = document.querySelector('.app-main');
  const book = main?.querySelector('[data-continuous-book]');
  if (!book) return main;
  const id = decodeURIComponent(location.pathname.split('/').filter(Boolean).at(-1) || '');
  return book.querySelector(`[data-book-section="${CSS.escape(id)}"]`)
    || book.querySelector('[data-book-section=""]');
})()"""

READING_SELECTOR = ".app-main [data-reader-current], .app-main:not(:has([data-continuous-book]))"


def reading_eval(page, function, arg=None):
    """Run a content probe with the chapter root and an optional argument."""
    return page.evaluate(f"arg => ({function})({READING_ROOT_JS}, arg)", arg)


def reading_locator(page, selector):
    return page.locator(READING_SELECTOR).locator(selector)


def wait_for_book_chapter(page, section_id):
    """Wait for a deep export's continuous-book arrival before leaving it.

    DOMContentLoaded alone precedes the client-side export switch. Starting
    another full navigation then can race that switch, especially in WebKit.
    """
    page.wait_for_function(f"""id => {{
      const root = {READING_ROOT_JS};
      return root?.dataset.bookSection === id && root.hasAttribute('data-reader-current');
    }}""", arg=section_id)


READING_POSITION_JS = """(() => {
  const main = document.querySelector('.app-main');
  const root = __ROOT__;
  const continuous = root !== main;
  const start = continuous ? main.scrollTop + root.getBoundingClientRect().top - main.getBoundingClientRect().top : 0;
  const spacer = root.querySelector('.chapter-end-space')?.offsetHeight || 0;
  const pad = parseFloat(getComputedStyle(main).paddingBottom) || 0;
  const max = continuous ? Math.max(0, root.scrollHeight - main.clientHeight + pad - spacer)
    : Math.max(0, main.scrollHeight - main.clientHeight - spacer);
  return {start, max, top: main.scrollTop - start};
})()""".replace("__ROOT__", READING_ROOT_JS)


def scroll_chapter(page, fraction):
    """Scroll within the chapter, retaining the book's global scroll area."""
    page.evaluate(f"""fraction => {{
      const main = document.querySelector('.app-main');
      const position = {READING_POSITION_JS};
      main.scrollTop = position.start + position.max * fraction;
      main.dispatchEvent(new Event('scroll'));
    }}""", fraction)


def wanted():
    """Device filter from the environment (QA_DEVICES=pixel7,iphone14); None = all."""
    v = os.environ.get("QA_DEVICES", "").strip()
    return [x.strip() for x in v.split(",") if x.strip()] or None


def devices(names):
    """[(name, engine, opts)] for the suite's default device list, filtered by QA_DEVICES."""
    w = wanted()
    out = []
    for n in names:
        if w is not None and n not in w:
            continue
        eng, opts = DEVICES[n]
        out.append((n, eng, dict(opts)))
    return out


def fast():
    return os.environ.get("QA_FAST") == "1"


SRC_DIRS = ["app", "components", "lib", "data", "public", "scripts"]
SRC_FILES = ["next.config.ts", "package.json", "postcss.config.mjs", "tsconfig.json"]
# Generated into public/ by the prebuild step — never a reason to rebuild.
GENERATED = ("search-index",)


def newest_source_mtime():
    best, which = 0.0, None
    for d in SRC_DIRS:
        root = os.path.join(REPO, d)
        for dp, dns, fns in os.walk(root):
            dns[:] = [x for x in dns if x not in ("__pycache__", "cache", "node_modules", "out", ".next")]
            for fn in fns:
                if fn == "desktop.ini" or fn.endswith((".pyc", ".log")) or fn.startswith(GENERATED):
                    continue
                m = os.path.getmtime(os.path.join(dp, fn))
                if m > best:
                    best, which = m, os.path.join(dp, fn)
    for f in SRC_FILES:
        p = os.path.join(REPO, f)
        if os.path.exists(p) and os.path.getmtime(p) > best:
            best, which = os.path.getmtime(p), p
    return best, which


def out_stamp():
    """mtime of the build output (precache manifest is written last by postbuild)."""
    p = os.path.join(OUT, "precache-manifest.json")
    return os.path.getmtime(p) if os.path.exists(p) else 0.0


def out_is_stale():
    src, which = newest_source_mtime()
    return out_stamp() < src, which


if __name__ == "__main__":
    # `python qa/lib/qa.py stale` -> exit 0 if out/ must be rebuilt (used by the pre-push hook)
    if len(sys.argv) > 1 and sys.argv[1] == "stale":
        st, which = out_is_stale()
        print(("STALE (newer: %s)" % which) if st else "FRESH")
        sys.exit(0 if st else 1)


# Short mantra (Reader v7.8, Satkirti 07.10.2026; widened v7.8.2; mirror of lib/book.ts isShortMantra): one line,
# 2–6 words, namaḥ / svāhā / phaṭ last (with or without a bīja) — such a mantra has no «пословно» in the reader.
import unicodedata as _ud
_ENDS = tuple(_ud.normalize("NFC", e) for e in ["namaḥ", "svāhā", "phaṭ", "намах̣", "сва̄ха̄", "пхат̣"])


def is_short_mantra(text):
    s = _ud.normalize("NFC", (text or "").replace("⟦", "").replace("⟧", "").strip())
    if not s or "\n" in s:
        return False
    w = s.split()
    return 2 <= len(w) <= 6 and s.rstrip(".!").endswith(_ENDS)
