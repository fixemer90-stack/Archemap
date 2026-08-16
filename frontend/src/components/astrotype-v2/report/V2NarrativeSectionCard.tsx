import type { V2NarrativeSectionViewModel } from "@/lib/astrotype-v2/report-view-model";

interface V2NarrativeSectionCardProps {
  section: V2NarrativeSectionViewModel;
}

export function V2NarrativeSectionCard({
  section,
}: V2NarrativeSectionCardProps) {
  return (
    <article
      data-v2-reader-block="narrative-section"
      data-v2-section-id={section.id}
      className="rounded-[1.75rem] border border-white/10 bg-[#111827] p-6 text-[#F5E9D0] shadow-xl shadow-black/20 md:p-8"
    >
      <div className="mb-6 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-3">
          <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#D8B45A]">
            {section.eyebrow}
          </div>
          <h2 className="text-2xl font-semibold md:text-4xl">
            {section.title}
          </h2>
        </div>
        <div className="rounded-full border border-[#D8B45A]/30 px-4 py-2 text-xs uppercase tracking-[0.18em] text-[#D8B45A]">
          {section.subtitle}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="space-y-5 text-base leading-8 text-[#D8DCE8] md:text-lg md:leading-9">
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph}>{paragraph}</p>
          ))}
        </div>
        <aside className="h-fit rounded-2xl border border-[#D8B45A]/20 bg-[#D8B45A]/10 p-5">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-[0.18em] text-[#D8B45A]">
            {section.asideTitle}
          </h3>
          <ul className="space-y-2 text-sm leading-6 text-[#E6D9B8]">
            {section.asideBullets.map((bullet) => (
              <li key={bullet} className="flex gap-2">
                <span aria-hidden="true">·</span>
                <span>{bullet}</span>
              </li>
            ))}
          </ul>
        </aside>
      </div>
    </article>
  );
}
