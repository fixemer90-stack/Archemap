import type { Metadata } from "next";
import Link from "next/link";
import { Check, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export const metadata: Metadata = {
  title: "Оплата",
};

const freeFeatures = [
  "Расчёт натальной карты",
  "Базовый тип и архетип",
  "Краткое описание личности",
  "3 сильные стороны",
  "1–2 зоны риска",
  "Teaser платного отчёта",
];

const plusFeatures = [
  "Полный личностный отчёт",
  "Сила функций и архетипов",
  "Слабые зоны и точки роста",
  "Профессиональный профиль",
  "Отношения и стиль привязанности",
  "Совместимость с другими людьми",
  "10–30 персональных AI-вопросов в месяц",
  "Сохранение нескольких профилей",
  "Обновление отчёта после ответов на вопросы",
];

function FeatureList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li
          key={item}
          className="flex gap-3 text-sm leading-relaxed text-[#D8DCE8]"
        >
          <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#D8B45A]" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export default function BillingPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-8">
      <section className="space-y-4">
        <div className="inline-flex items-center gap-2 rounded-full border border-[rgba(216,180,90,0.35)] bg-[rgba(216,180,90,0.08)] px-4 py-2 text-sm text-[#D8B45A]">
          <Sparkles className="h-4 w-4" />
          Тарифы Astrotype
        </div>
        <div className="max-w-3xl space-y-3">
          <h1 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold tracking-tight text-[#F6F1E8] md:text-5xl">
            Бесплатный вход и один понятный Plus
          </h1>
          <p className="text-lg leading-relaxed text-[#D8DCE8]">
            Free показывает, что сервис не рандомный и уже понял что-то важное
            про вас. Plus открывает полный доступ к персональной карте,
            уточнениям и обновлению отчёта.
          </p>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
        <Card className="relative overflow-hidden">
          <CardHeader className="space-y-4">
            <div className="flex items-start justify-between gap-4">
              <div className="space-y-2">
                <p className="text-sm font-medium uppercase tracking-[0.24em] text-[#8DA8FF]">
                  Free
                </p>
                <CardTitle className="text-3xl">Бесплатный вход</CardTitle>
                <CardDescription className="max-w-md leading-relaxed">
                  Для первого знакомства: построить карту, увидеть базовый тип и
                  понять, насколько описание похоже на вас.
                </CardDescription>
              </div>
              <div className="rounded-full border border-[rgba(141,168,255,0.30)] px-4 py-2 text-sm text-[#8DA8FF]">
                0 ₽
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <FeatureList items={freeFeatures} />
            <div className="rounded-2xl border border-[rgba(216,220,232,0.10)] bg-[rgba(255,255,255,0.04)] p-4 text-sm leading-relaxed text-[#D8DCE8]">
              Цель Free — дать честный первый сигнал: “Astrotype видит во мне не
              случайный текст, а узнаваемый паттерн”.
            </div>
          </CardContent>
          <CardFooter>
            <Button asChild variant="outline" className="w-full">
              <Link href="/register">Начать бесплатно</Link>
            </Button>
          </CardFooter>
        </Card>

        <Card
          id="plus"
          className="relative overflow-hidden border-[rgba(216,180,90,0.45)] bg-gradient-to-br from-[rgba(91,63,214,0.20)] via-[rgba(255,255,255,0.06)] to-[rgba(216,180,90,0.12)]"
        >
          <div className="absolute right-6 top-6 rounded-full bg-[#D8B45A] px-3 py-1 text-xs font-semibold text-[#17142A]">
            Лучший старт
          </div>
          <CardHeader className="space-y-4 pr-28">
            <div className="space-y-2">
              <p className="text-sm font-medium uppercase tracking-[0.24em] text-[#D8B45A]">
                Plus
              </p>
              <CardTitle className="text-3xl">
                Полная персональная карта
              </CardTitle>
              <CardDescription className="max-w-xl leading-relaxed">
                Не “подписка на гороскоп”, а доступ к своей карте, её
                объяснению, уточнению и обновлению по вашим ответам.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-end gap-3">
              <div className="text-4xl font-semibold text-[#F6F1E8]">
                699–999 ₽
              </div>
              <div className="pb-1 text-sm text-[#D8DCE8]">в месяц</div>
              <div className="pb-1 text-sm text-[#8DA8FF]">или €7.99–€9.99</div>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <FeatureList items={plusFeatures} />
            <div className="rounded-2xl border border-[rgba(216,180,90,0.22)] bg-[rgba(216,180,90,0.08)] p-4 text-sm leading-relaxed text-[#F6F1E8]">
              Plus — это полный доступ к персональному отчёту Self/Career,
              вопросам для уточнения профиля и сохранению нескольких карт.
            </div>
          </CardContent>
          <CardFooter className="flex-col items-stretch gap-3 sm:flex-row">
            <Button asChild className="flex-1">
              <a href="#plus" aria-disabled="true">
                Оформить Plus
              </a>
            </Button>
            <p className="flex-1 text-xs leading-relaxed text-[#D8DCE8]">
              Frontend подготовлен. Подключение реальной оплаты и checkout будет
              отдельным backend/frontend шагом.
            </p>
          </CardFooter>
        </Card>
      </section>

      <section className="rounded-[24px] border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] p-6">
        <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
          Почему такая модель проще для запуска
        </h2>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          {[
            [
              "Понятный вход",
              "Free не продаёт сразу: он показывает точность и создаёт доверие.",
            ],
            [
              "Один платный выбор",
              "Plus не дробит ценность на мелкие пакеты и не заставляет сравнивать лишнее.",
            ],
            [
              "Ценность в уточнении",
              "Пользователь платит не за разовый текст, а за живую карту, которую можно дополнять.",
            ],
          ].map(([title, description]) => (
            <div key={title} className="space-y-2">
              <h3 className="font-medium text-[#F6F1E8]">{title}</h3>
              <p className="text-sm leading-relaxed text-[#D8DCE8]">
                {description}
              </p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
