import Link from "next/link";
import { Briefcase, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function CareerProductPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
          Astrotype Career
        </h1>
        <p className="text-sm text-[#D8DCE8] mt-1">
          Карьерные сценарии: роли, рабочая среда, сильные профессиональные
          стороны.
        </p>
      </div>

      <div className="glass p-8 text-center space-y-6 max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-[rgba(194,138,46,0.15)] flex items-center justify-center mx-auto">
          <Briefcase className="h-8 w-8 text-[#C28A2E]" />
        </div>

        <div className="space-y-2">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Скоро
          </h2>
          <p className="text-sm text-[#D8DCE8] leading-relaxed">
            Astrotype Career покажет, какие профессиональные роли вам подходят,
            в какой среде вы раскрываетесь сильнее, и какие зоны роста стоит
            развивать.
          </p>
        </div>

        <div className="space-y-3 text-left">
          <h3 className="text-sm font-medium text-[#F6F1E8]">
            Что будет в отчёте:
          </h3>
          <ul className="space-y-2">
            {[
              "Карьерные роли: топ-5 подходящих позиций",
              "Рабочая среда: где вы раскрываетесь сильнее",
              "Стиль принятия решений",
              "Anti-patterns: что мешает развитию",
              "Карта роста: сильные стороны и зоны развития",
            ].map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-sm text-[#D8DCE8]"
              >
                <span className="text-[#C28A2E] mt-0.5">✦</span>
                {item}
              </li>
            ))}
          </ul>
        </div>

        <Button variant="outline" asChild>
          <Link href="/dashboard">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Назад
          </Link>
        </Button>
      </div>
    </div>
  );
}
