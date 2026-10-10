import Link from "next/link";
import { Heart, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LoveProductPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-text-primary">
          Astrotype Love
        </h1>
        <p className="text-sm text-text-secondary mt-1">
          Совместимость двух людей: синастрия, паттерны отношений, точки
          притяжения и напряжения.
        </p>
      </div>

      <div className="glass p-8 text-center space-y-6 max-w-lg mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-product-love/15 flex items-center justify-center mx-auto">
          <Heart className="h-8 w-8 text-product-love" />
        </div>

        <div className="space-y-2">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-text-primary">
            Скоро
          </h2>
          <p className="text-sm text-text-secondary leading-relaxed">
            Astrotype Love позволит сравнить две натальные карты и получить
            детальный отчёт о совместимости: стиль коммуникации, точки
            притяжения и напряжения, рекомендации по взаимодействию.
          </p>
        </div>

        <div className="space-y-3 text-left">
          <h3 className="text-sm font-medium text-text-primary">
            Что будет в отчёте:
          </h3>
          <ul className="space-y-2">
            {[
              "Синастрический анализ двух карт",
              "Паттерны отношений: коммуникация, близость, конфликты",
              "Точки притяжения и напряжения",
              "Рекомендации по взаимодействию",
              "Показатель совместимости по каждой оси",
            ].map((item) => (
              <li
                key={item}
                className="flex items-start gap-2 text-sm text-text-secondary"
              >
                <span className="text-product-love mt-0.5">✦</span>
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
