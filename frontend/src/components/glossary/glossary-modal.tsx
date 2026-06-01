"use client";

import type {
  ReportGlossaryEntry,
  ReportGlossaryTerm,
} from "@/lib/glossary/report-glossary";

interface GlossaryModalProps {
  term: ReportGlossaryTerm;
  entry: ReportGlossaryEntry;
  onClose: () => void;
}

export function GlossaryModal({ term, entry, onClose }: GlossaryModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-end bg-black/50 p-0 sm:items-center sm:justify-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby={`glossary-${term}`}
    >
      <div className="w-full rounded-t-2xl border bg-background p-6 shadow-lg sm:max-w-lg sm:rounded-2xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-muted-foreground">
              Термин отчёта
            </p>
            <h2 id={`glossary-${term}`} className="mt-1 text-xl font-semibold">
              {entry.title}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="min-h-10 rounded-md border px-3 py-2 text-sm hover:bg-muted"
          >
            Закрыть
          </button>
        </div>

        <div className="mt-5 grid gap-4 text-sm leading-6">
          <section>
            <h3 className="font-medium">Что это</h3>
            <p className="mt-1 text-muted-foreground">{entry.definition}</p>
          </section>
          <section>
            <h3 className="font-medium">Зачем это в отчёте</h3>
            <p className="mt-1 text-muted-foreground">{entry.reportMeaning}</p>
          </section>
          <section className="rounded-lg bg-muted p-4">
            <h3 className="font-medium">Пример</h3>
            <p className="mt-1 text-muted-foreground">{entry.example}</p>
          </section>
        </div>
      </div>
    </div>
  );
}
