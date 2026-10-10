"use client";

import { useState } from "react";
import { GlossaryModal } from "@/components/glossary/glossary-modal";
import {
  REPORT_GLOSSARY,
  type ReportGlossaryTerm,
} from "@/lib/glossary/report-glossary";

interface TermHelpProps {
  term: ReportGlossaryTerm;
  variant?: "default" | "v2";
}

export function TermHelp({ term, variant = "default" }: TermHelpProps) {
  const [isOpen, setIsOpen] = useState(false);
  const entry = REPORT_GLOSSARY[term];
  const isV2 = variant === "v2";

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className={
          isV2
            ? "group relative inline-flex min-h-6 items-center gap-1 border-b border-dotted border-border-default/80 text-warning underline-offset-4 transition hover:text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-focus-ring/55"
            : "group relative inline-flex min-h-7 items-center gap-1 border-b border-dotted border-primary/70 text-primary underline-offset-4 hover:text-primary/80"
        }
        aria-label={`Пояснить термин: ${term}`}
        data-glossary-term={term}
      >
        {term}
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border text-[10px] leading-none">
          ?
        </span>
        <span
          className={
            isV2
              ? "pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-[min(340px,80vw)] -translate-x-1/2 rounded-[16px] border border-border-default/30 bg-surface-subtle p-4 text-left text-[12px] leading-[1.5] text-text-secondary shadow-elevated group-hover:block group-focus-visible:block"
              : "pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-[min(340px,80vw)] -translate-x-1/2 rounded-lg border bg-background p-4 text-left text-xs leading-5 text-foreground shadow-lg group-hover:block group-focus-visible:block"
          }
          role="tooltip"
        >
          <strong className={isV2 ? "block text-warning" : "block"}>
            {entry.title}
          </strong>
          <span className="mt-1 block">{entry.definition}</span>
          <span
            className={
              isV2
                ? "mt-2 block text-text-muted"
                : "mt-2 block text-muted-foreground"
            }
          >
            {entry.reportMeaning}
          </span>
        </span>
      </button>
      {isOpen && (
        <GlossaryModal
          term={term}
          entry={entry}
          onClose={() => setIsOpen(false)}
        />
      )}
    </>
  );
}
