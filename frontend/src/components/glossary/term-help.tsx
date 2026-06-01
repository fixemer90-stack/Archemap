"use client";

import { useState } from "react";
import { GlossaryModal } from "@/components/glossary/glossary-modal";
import {
  REPORT_GLOSSARY,
  type ReportGlossaryTerm,
} from "@/lib/glossary/report-glossary";

export function TermHelp({ term }: { term: ReportGlossaryTerm }) {
  const [isOpen, setIsOpen] = useState(false);
  const entry = REPORT_GLOSSARY[term];

  return (
    <>
      <button
        type="button"
        onClick={() => setIsOpen(true)}
        className="inline-flex min-h-7 items-center gap-1 border-b border-dotted border-primary/70 text-primary underline-offset-4 hover:text-primary/80"
        aria-label={`Пояснить термин: ${term}`}
        data-glossary-term={term}
      >
        {term}
        <span className="inline-flex h-4 w-4 items-center justify-center rounded-full border text-[10px] leading-none">
          ?
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
