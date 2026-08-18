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
            ? "group relative inline-flex min-h-6 items-center gap-1 border-b border-dotted border-[#D9B86F]/80 text-[#FFE2A1] underline-offset-4 transition hover:text-[#fff2d6] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#D9B86F]/55"
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
              ? "pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-[min(340px,80vw)] -translate-x-1/2 rounded-[16px] border border-[#D9B86F]/30 bg-[#0d1420] p-4 text-left text-[12px] leading-[1.5] text-[#DCE4F3] shadow-[0_18px_55px_rgba(0,0,0,0.45)] group-hover:block group-focus-visible:block"
              : "pointer-events-none absolute left-1/2 top-full z-40 mt-2 hidden w-[min(340px,80vw)] -translate-x-1/2 rounded-lg border bg-background p-4 text-left text-xs leading-5 text-foreground shadow-lg group-hover:block group-focus-visible:block"
          }
          role="tooltip"
        >
          <strong className={isV2 ? "block text-[#FFE2A1]" : "block"}>
            {entry.title}
          </strong>
          <span className="mt-1 block">{entry.definition}</span>
          <span
            className={
              isV2
                ? "mt-2 block text-[#9FB0CC]"
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
