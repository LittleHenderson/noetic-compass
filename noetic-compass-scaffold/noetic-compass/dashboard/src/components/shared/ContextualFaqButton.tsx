import { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  clearFaqReturnPoint,
  findFaqTopic,
  matchFaqTopic,
  popFaqScrollRestore,
  queueFaqScrollRestore,
  readFaqReturnPoint,
  writeFaqReturnPoint,
  type FaqReturnPoint,
} from '../../lib/contextualFaq';

const MAIN_SCROLL_ID = 'app-main-scroll';

function currentScrollTop(): number {
  return document.getElementById(MAIN_SCROLL_ID)?.scrollTop ?? window.scrollY ?? 0;
}

function pathWithHash(pathname: string, search: string, hash: string): string {
  return `${pathname}${search}${hash}`;
}

export function ContextualFaqButton() {
  const location = useLocation();
  const navigate = useNavigate();
  const [isPinned, setIsPinned] = useState(false);
  const [isHovering, setIsHovering] = useState(false);
  const [returnPoint, setReturnPoint] = useState<FaqReturnPoint | null>(() => readFaqReturnPoint());

  const isFaqPage = location.pathname === '/faq';
  const topic = useMemo(() => {
    if (isFaqPage) {
      return findFaqTopic(decodeURIComponent(location.hash.replace(/^#/, ''))) ?? matchFaqTopic(location.pathname);
    }
    return matchFaqTopic(location.pathname);
  }, [isFaqPage, location.hash, location.pathname]);

  useEffect(() => {
    const restoreTop = popFaqScrollRestore();
    if (restoreTop === null) return;

    window.setTimeout(() => {
      const main = document.getElementById(MAIN_SCROLL_ID);
      if (main) {
        main.scrollTo({ top: restoreTop });
      } else {
        window.scrollTo({ top: restoreTop });
      }
    }, 60);
  }, [location.pathname, location.search]);

  useEffect(() => {
    setReturnPoint(readFaqReturnPoint());
  }, [location.pathname, location.search, location.hash]);

  function openFaq() {
    writeFaqReturnPoint({
      path: pathWithHash(location.pathname, location.search, location.hash),
      scrollTop: currentScrollTop(),
      topicId: topic.id,
      topicLabel: topic.label,
    });
    setIsPinned(false);
    navigate(`/faq#${topic.id}`);
  }

  function goBackToSource() {
    if (!returnPoint) return;
    queueFaqScrollRestore(returnPoint.scrollTop);
    clearFaqReturnPoint();
    setReturnPoint(null);
    setIsPinned(false);
    navigate(returnPoint.path);
  }

  const showPanel = isPinned || isHovering;

  if (isFaqPage && returnPoint) {
    return (
      <button
        type="button"
        onClick={goBackToSource}
        className="fixed bottom-4 right-4 z-50 max-w-[calc(100vw-2rem)] rounded-full border border-accent-teal/35 bg-dark-800/95 px-4 py-3 text-left text-xs font-semibold text-accent-teal shadow-2xl shadow-accent-teal/10 backdrop-blur-xl transition hover:border-accent-teal/70 hover:bg-dark-700/95 sm:right-6"
        title="Return to the exact screen that opened this FAQ"
      >
        Back to where you clicked
        <span className="ml-2 text-slate-400">({returnPoint.topicLabel})</span>
      </button>
    );
  }

  return (
    <div
      className="fixed bottom-4 right-4 z-50 flex max-w-[calc(100vw-2rem)] flex-col items-end gap-3 sm:right-6"
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      onFocus={() => setIsHovering(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) {
          setIsHovering(false);
        }
      }}
    >
      {showPanel ? (
        <div className="w-[min(22rem,calc(100vw-2rem))] rounded-2xl border border-white/[0.08] bg-dark-800/95 p-4 text-sm text-slate-300 shadow-2xl shadow-black/40 backdrop-blur-xl">
          <div className="mb-2 flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-accent-teal">AI help</p>
              <p className="mt-1 text-base font-semibold text-slate-100">{topic.label}</p>
            </div>
            <button
              type="button"
              onClick={() => setIsPinned(false)}
              className="rounded-full px-2 py-1 text-slate-500 transition hover:bg-white/[0.06] hover:text-slate-200"
              aria-label="Close help summary"
            >
              x
            </button>
          </div>
          <p className="leading-relaxed text-slate-300">{topic.summary}</p>
          <div className="mt-4 flex items-center justify-between gap-3">
            <p className="text-[0.7rem] text-slate-500">Full FAQ returns you here.</p>
            <button
              type="button"
              onClick={openFaq}
              className="shrink-0 rounded-full border border-accent-teal/35 bg-accent-teal/10 px-3 py-2 text-xs font-semibold text-accent-teal transition hover:border-accent-teal/70 hover:bg-accent-teal/15"
            >
              Full FAQ
            </button>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        onClick={() => {
          if (isPinned) {
            openFaq();
          } else {
            setIsPinned(true);
          }
        }}
        onDoubleClick={openFaq}
        className="group flex min-h-[44px] items-center gap-2 rounded-full border border-accent-teal/35 bg-dark-800/90 px-4 py-3 text-sm font-semibold text-slate-100 shadow-xl shadow-accent-teal/10 backdrop-blur-xl transition hover:border-accent-teal/70 hover:bg-dark-700/95"
        aria-label="Open contextual FAQ help"
        title="Hover for summary. Click once for help, click again for full FAQ."
      >
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-accent-teal/15 text-accent-teal ring-1 ring-accent-teal/30 transition group-hover:bg-accent-teal/20">
          ?
        </span>
        <span>AI Help</span>
      </button>
    </div>
  );
}
