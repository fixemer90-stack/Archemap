import type { NarrativeEvidenceNote } from "@/lib/report/view-model";

interface EvidenceNotesProps {
  notes: NarrativeEvidenceNote[];
  fallbackFactIds?: string[];
  className?: string;
}

export function EvidenceNotes({
  notes,
  fallbackFactIds = [],
  className,
}: EvidenceNotesProps) {
  if (notes.length === 0 && fallbackFactIds.length === 0) {
    return null;
  }

  if (notes.length === 0) {
    return (
      <div className={className ?? "mt-4 text-xs text-muted-foreground"}>
        Основания: {fallbackFactIds.join(", ")}
      </div>
    );
  }

  return (
    <details
      className={`${className ?? "mt-4"} rounded-xl border border-border/60 bg-muted/30 p-4 text-sm text-muted-foreground`}
    >
      <summary className="cursor-pointer font-medium text-foreground">
        Почему так видно
      </summary>
      <div className="mt-3 space-y-3">
        {notes.map((note, index) => (
          <div key={`${note.claim}-${index}`} className="space-y-1">
            <p className="leading-6">{note.claim}</p>
            {note.interpretation && (
              <p className="leading-6">{note.interpretation}</p>
            )}
            <p className="text-xs">Основания: {note.fact_ids.join(", ")}</p>
            {note.limitation && (
              <p className="text-xs">
                <span className="font-medium text-foreground">
                  Ограничение:
                </span>{" "}
                {note.limitation}
                {note.limitation_fact_ids.length > 0 && (
                  <span> — {note.limitation_fact_ids.join(", ")}</span>
                )}
              </p>
            )}
          </div>
        ))}
      </div>
    </details>
  );
}
