import type { V2NarrativeSectionViewModel } from "@/lib/astrotype-v2/report-view-model";
import { V2GlossaryText } from "./V2GlossaryText";

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
      className="rounded-[22px] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.055),rgba(255,255,255,0.025))] p-5 text-[#F4EADB] shadow-[0_20px_70px_rgba(0,0,0,0.3)] md:p-6"
    >
      <div className="mb-[14px] flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <div className="text-[13px] font-semibold uppercase tracking-[0.08em] text-[#D9B86F]">
            {section.eyebrow}
          </div>
          <h2 className="text-[21px] leading-tight font-semibold text-[#F4EADB] md:text-[28px]">
            {section.title}
          </h2>
        </div>
        <div className="rounded-full border border-white/10 bg-[#101622] px-3 py-1 text-[12px] uppercase tracking-[0.08em] text-[#AEB6C7]">
          {section.subtitle}
        </div>
      </div>

      <div className="grid gap-[18px] lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
        <div className="space-y-4 text-[15px] leading-[1.6] text-[#DCE4F3] md:text-[16px]">
          {section.paragraphs.map((paragraph) => (
            <p key={paragraph}>
              <V2GlossaryText text={paragraph} />
            </p>
          ))}
        </div>
        <aside className="h-fit rounded-[16px] border border-[#263046] bg-[#101622] p-4">
          <h3 className="mb-3 text-[13px] font-semibold uppercase tracking-[0.08em] text-[#D9B86F]">
            {section.asideTitle}
          </h3>
          <ul className="space-y-2 text-[13px] leading-[1.5] text-[#DCE4F3]">
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
