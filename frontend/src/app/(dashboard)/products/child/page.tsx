import Link from "next/link";
import { Baby, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ChildProductPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
          Archemap Child
        </h1>
        <p className="text-sm text-[#D8DCE8] mt-1">
          Профиль ребёнка: темперамент, сильные стороны, рекомендации по
          воспитанию.
        </p>
      </div>

      <div className="glass p-8 text-center space-y-6 max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-[rgba(107,175,189,0.15)] flex items-center justify-center mx-auto">
          <Baby className="h-8 w-8 text-[#6BAFBD]" />
        </div>

        <div className="space-y-2">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Скоро
          </h2>
          <p className="text-sm text-[#D8DCE8] leading-relaxed">
            Archemap Child поможет родителям понять темперамент и сильные
            стороны ребёнка через призму натальной карты. Не диагноз — а
            бережные гипотезы и поддерживающие практики.
          </p>
        </div>

        <div className="space-y-3 text-left">
          <h3 className="text-sm font-medium text-[#F6F1E8]">
            Что будет в отчёте:
          </h3>
          <ul className="space-y-2">
            {[
              "Темперамент: ритм регуляции, чувствительность, стиль успокоения",
              "Сильные стороны и зоны роста",
              "Рекомендации по рутине и переходам",
              "Стиль социализации",
              "Бережные советы по воспитанию",
            ].map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-sm text-[#D8DCE8]"
              >
                <span className="text-[#6BAFBD] mt-0.5">✦</span>
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
