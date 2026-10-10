import Link from "next/link";
import { Baby, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function ChildProductPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
          Astrotype Child
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Профиль ребёнка: темперамент, сильные стороны, рекомендации по
          воспитанию.
        </p>
      </div>

      <div className="glass p-8 text-center space-y-6 max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-product-child/15 flex items-center justify-center mx-auto">
          <Baby className="h-8 w-8 text-product-child" />
        </div>

        <div className="space-y-2">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-text-primary">
            Скоро
          </h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            Astrotype Child поможет родителям понять темперамент и сильные
            стороны ребёнка через призму натальной карты. Не диагноз — а
            бережные гипотезы и поддерживающие практики.
          </p>
        </div>

        <div className="space-y-3 text-left">
          <h3 className="text-sm font-medium text-text-primary">
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
                className="flex items-start gap-2 text-sm text-text-secondary"
              >
                <span className="text-product-child mt-0.5">✦</span>
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
