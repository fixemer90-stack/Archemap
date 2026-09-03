import Link from "next/link";
import { ArrowRight, CheckCircle2, MoonStar, Sparkles } from "lucide-react";

import {
  ProductSurfaceCard,
  ProductSurfaceHero,
  ProductSurfaceShell,
  SurfaceActionRow,
  SurfaceEyebrow,
} from "@/components/product-surface";
import { Button } from "@/components/ui/button";

const steps = [
  {
    title: "Данные рождения",
    text: "Вы вводите дату, время и место рождения. Если точного времени нет, интерфейс покажет, где точность будет ниже.",
  },
  {
    title: "Расчёт карты",
    text: "Система строит положения планет, домов, аспектов и балансы — сначала фактический слой, потом смысловая сборка.",
  },
  {
    title: "Личный отчёт",
    text: "Вы получаете связный портрет: как устроены ваши реакции, энергия, фокус внимания и зрелый способ опираться на себя.",
  },
];

const inside = [
  "натальная карта с понятными пояснениями",
  "главные напряжения и ресурсы карты",
  "разделы о характере, выборе, отношениях и работе",
  "короткие выводы рядом с развёрнутым текстом",
];

function ReportPreview() {
  return (
    <ProductSurfaceCard
      className="space-y-5 border-[rgba(216,180,90,0.22)] bg-[rgba(10,12,22,0.52)]"
      data-product-surface-preview="illustrative"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-[#8DA8FF]">
            Пример структуры
          </p>
          <h2 className="mt-2 font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
            Как выглядит личный портрет
          </h2>
        </div>
        <MoonStar className="h-8 w-8 text-[#D8B45A]" />
      </div>
      <p className="text-sm leading-6 text-[rgba(216,220,232,0.76)]">
        Это демонстрационный фрагмент интерфейса, а не готовый отчёт конкретного
        человека. Он показывает темп: краткая формула, затем объяснение, затем
        практический вывод.
      </p>
      <div className="rounded-3xl border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] p-5">
        <p className="text-xs uppercase tracking-[0.24em] text-[#D8B45A]">
          Главный мотив
        </p>
        <p className="mt-3 font-[family-name:var(--font-cormorant)] text-2xl leading-tight text-[#F6F1E8]">
          Сначала понять внутренний ритм, потом выбирать форму действия.
        </p>
        <p className="mt-4 text-sm leading-6 text-[#D8DCE8]">
          Отчёт не навешивает ярлык. Он показывает, какие части карты тянут к
          самостоятельности, где нужна опора на других и как это проявляется в
          обычных решениях.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {inside.map((item) => (
          <div
            key={item}
            className="flex items-start gap-3 rounded-2xl border border-[rgba(216,220,232,0.10)] bg-[rgba(216,220,232,0.045)] p-3 text-sm text-[#D8DCE8]"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-[#D8B45A]" />
            <span>{item}</span>
          </div>
        ))}
      </div>
    </ProductSurfaceCard>
  );
}

export default function HomePage() {
  return (
    <ProductSurfaceShell>
      <header className="mb-7 flex items-center justify-between rounded-full border border-[rgba(216,220,232,0.12)] bg-[rgba(255,255,255,0.04)] px-5 py-3 backdrop-blur-xl">
        <Link
          href="/"
          className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]"
        >
          Astrotype
        </Link>
        <nav className="flex items-center gap-2">
          <Button variant="ghost" asChild className="text-[#D8DCE8]">
            <Link href="/login">Войти</Link>
          </Button>
          <Button asChild>
            <Link href="/register">Регистрация</Link>
          </Button>
        </nav>
      </header>

      <div className="space-y-7">
        <ProductSurfaceHero
          eyebrow="Astrotype · натальный портрет"
          title={<>Не гороскоп. Личный отчёт по вашей карте рождения.</>}
          lead={
            <>
              Astrotype соединяет данные рождения, точный расчёт карты и мягкий
              человеческий текст, чтобы показать ваш внутренний ритм без ярлыков
              и мистического тумана.
            </>
          }
          aside={<ReportPreview />}
        >
          <SurfaceActionRow>
            <Button asChild size="lg">
              <Link href="/register">
                Построить свой отчёт
                <ArrowRight className="h-4 w-4" />
              </Link>
            </Button>
            <Button variant="outline" asChild size="lg">
              <Link href="/login">У меня уже есть аккаунт</Link>
            </Button>
          </SurfaceActionRow>
        </ProductSurfaceHero>

        <section className="grid gap-5 lg:grid-cols-3" id="report-structure">
          {steps.map((step, index) => (
            <ProductSurfaceCard key={step.title} className="space-y-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-full bg-[linear-gradient(135deg,#5B3FD6,#D8B45A)] text-sm font-semibold text-[#F6F1E8]">
                {index + 1}
              </div>
              <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-[#F6F1E8]">
                {step.title}
              </h2>
              <p className="text-sm leading-7 text-[rgba(216,220,232,0.76)]">
                {step.text}
              </p>
            </ProductSurfaceCard>
          ))}
        </section>

        <section className="grid gap-5 lg:grid-cols-[0.9fr_1.1fr]">
          <ProductSurfaceCard className="space-y-4">
            <SurfaceEyebrow>Что вы получаете</SurfaceEyebrow>
            <h2 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold text-[#F6F1E8]">
              Отчёт, к которому можно возвращаться
            </h2>
            <p className="text-sm leading-7 text-[#D8DCE8]">
              Это не карточка с одним ответом. Внутри — карта, ключевые темы,
              подробные разделы и спокойные вопросы, которые помогают увидеть
              себя точнее.
            </p>
          </ProductSurfaceCard>
          <ProductSurfaceCard className="grid gap-4 sm:grid-cols-2">
            {[
              "расчётный слой без догадок",
              "смысловая формула карты",
              "развёрнутый портрет личности",
              "практические выводы без давления",
            ].map((item) => (
              <div
                key={item}
                className="rounded-2xl bg-[rgba(255,255,255,0.04)] p-4"
              >
                <Sparkles className="mb-3 h-5 w-5 text-[#D8B45A]" />
                <p className="text-sm leading-6 text-[#D8DCE8]">{item}</p>
              </div>
            ))}
          </ProductSurfaceCard>
        </section>
      </div>
    </ProductSurfaceShell>
  );
}
