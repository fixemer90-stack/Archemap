import Link from "next/link";
import { Button } from "@/components/ui/button";

// ── Compass Logo ───────────────────────────────────────────────────
function CompassLogo({ size = 72 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      fill="none"
      className="mx-auto"
    >
      <circle
        cx="28"
        cy="28"
        r="26"
        stroke="#D8DCE8"
        strokeWidth="0.5"
        opacity="0.3"
      />
      <circle
        cx="28"
        cy="28"
        r="18"
        stroke="#D8DCE8"
        strokeWidth="0.5"
        opacity="0.2"
      />
      <path d="M28 4 L31 24 L28 28 L25 24 Z" fill="#5B3FD6" opacity="0.9" />
      <path d="M52 28 L32 31 L28 28 L32 25 Z" fill="#D8B45A" opacity="0.7" />
      <path d="M28 52 L25 32 L28 28 L31 32 Z" fill="#5B3FD6" opacity="0.6" />
      <path d="M4 28 L24 25 L28 28 L24 31 Z" fill="#D8B45A" opacity="0.5" />
      <circle cx="28" cy="28" r="2.5" fill="#D8B45A" />
      <circle cx="28" cy="6" r="1.5" fill="#D8DCE8" opacity="0.6" />
      <circle cx="50" cy="28" r="1.5" fill="#D8DCE8" opacity="0.6" />
      <circle cx="28" cy="50" r="1.5" fill="#D8DCE8" opacity="0.6" />
      <circle cx="6" cy="28" r="1.5" fill="#D8DCE8" opacity="0.6" />
    </svg>
  );
}

// ── Star Grid Background ──────────────────────────────────────────
function StarGrid() {
  return (
    <div
      className="pointer-events-none fixed inset-0 opacity-[0.04]"
      style={{
        backgroundImage:
          "radial-gradient(circle, #D8DCE8 1px, transparent 1px)",
        backgroundSize: "48px 48px",
      }}
    />
  );
}

// ── Section Divider ───────────────────────────────────────────────
function Divider() {
  return (
    <div className="flex items-center justify-center gap-4 py-12">
      <div className="h-px w-16 bg-gradient-to-r from-transparent to-[rgba(216,220,232,0.20)]" />
      <div className="h-1.5 w-1.5 rounded-full bg-[#D8B45A] opacity-60" />
      <div className="h-px w-16 bg-gradient-to-l from-transparent to-[rgba(216,220,232,0.20)]" />
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="relative min-h-screen">
      <StarGrid />

      {/* Header */}
      <header className="relative z-10 border-b border-[rgba(216,220,232,0.08)]">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <span className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Astrotype
          </span>
          <nav className="flex items-center gap-3">
            <Button
              variant="ghost"
              asChild
              className="text-[#D8DCE8] hover:text-[#F6F1E8]"
            >
              <Link href="/login">Войти</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Регистрация</Link>
            </Button>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <main className="relative z-10">
        <section className="container mx-auto flex flex-col items-center justify-center gap-8 px-4 pt-20 pb-16 text-center md:pt-28">
          <CompassLogo />
          <h1 className="font-[family-name:var(--font-cormorant)] text-4xl font-semibold tracking-tight text-[#F6F1E8] sm:text-5xl md:text-6xl">
            Карта внутренних архетипов
          </h1>
          <p className="max-w-2xl text-lg text-[#D8DCE8] leading-relaxed">
            Введите дату, время и место рождения — Astrotype построит натальную
            карту, выделит ключевые факты и соберёт V2 natal-only отчёт.{" "}
            <span className="text-[#F6F1E8]">
              Каждый вывод — с числовым показателем, уровнем уверенности и
              цепочкой оснований.
            </span>
          </p>
          <div className="flex gap-3">
            <Button asChild>
              <Link href="/register">Построить карту</Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/login">У меня есть аккаунт</Link>
            </Button>
          </div>
        </section>

        <Divider />

        {/* Что внутри */}
        <section className="container mx-auto px-4 pb-16">
          <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-center text-[#F6F1E8] mb-10">
            Что внутри
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            {/* Натальная карта */}
            <div className="glass p-6 space-y-3">
              <div className="text-[#D8B45A] text-2xl">☉</div>
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Натальная карта
              </h3>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                12 планет в знаках и домах, аспекты между ними. Вы увидите, где
                стоит ваше Солнце, как расположен Меркурий, какие планеты
                ретроградны. Считается по Swiss Ephemeris — тому же движку, что
                используют профессиональные астрологи.
              </p>
            </div>

            {/* Синтез */}
            <div className="glass p-6 space-y-3">
              <div className="text-[#5B3FD6] text-2xl">◆</div>
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Синтез карты
              </h3>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                Система собирает положения, аспекты, балансы и акценты домов в
                связную смысловую структуру: темы, напряжения и вектор развития.
              </p>
            </div>

            {/* Архетипы */}
            <div className="glass p-6 space-y-3">
              <div className="text-[#8DA8FF] text-2xl">⬡</div>
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Evidence-first отчёт
              </h3>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                Каждый раздел опирается на конкретные факты карты: сначала
                расчётный слой, затем синтез, затем narrative без типологий.
              </p>
            </div>
          </div>
        </section>

        <Divider />

        {/* Принцип */}
        <section className="container mx-auto px-4 pb-16">
          <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-center text-[#F6F1E8] mb-10">
            Принцип работы
          </h2>
          <div className="max-w-2xl mx-auto space-y-6">
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#5B3FD6] to-[#D8B45A] flex items-center justify-center text-xs font-medium text-[#F6F1E8]">
                1
              </div>
              <div>
                <h3 className="text-sm font-medium text-[#F6F1E8]">
                  Данные рождения
                </h3>
                <p className="text-sm text-[#D8DCE8]">
                  Дата, время и место рождения. Если время неизвестно — можно
                  указать «не знаю», система предупредит о снижении точности.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#5B3FD6] to-[#D8B45A] flex items-center justify-center text-xs font-medium text-[#F6F1E8]">
                2
              </div>
              <div>
                <h3 className="text-sm font-medium text-[#F6F1E8]">
                  Вычисление
                </h3>
                <p className="text-sm text-[#D8DCE8]">
                  Система вычисляет позиции планет, домов и аспектов. Затем
                  извлекает признаки: доли стихий (огонь, земля, воздух, вода),
                  модальности, акценты домов.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-[#5B3FD6] to-[#D8B45A] flex items-center justify-center text-xs font-medium text-[#F6F1E8]">
                3
              </div>
              <div>
                <h3 className="text-sm font-medium text-[#F6F1E8]">
                  Интерпретация
                </h3>
                <p className="text-sm text-[#D8DCE8]">
                  Движок собирает факты карты в синтез, строит outline и
                  генерирует разделы V2 отчёта. Каждый вывод связан с
                  конкретными основаниями.
                </p>
              </div>
            </div>
          </div>
        </section>

        <Divider />

        {/* Что вы получаете */}
        <section className="container mx-auto px-4 pb-16">
          <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-center text-[#F6F1E8] mb-10">
            Что вы получаете
          </h2>
          <div className="grid gap-4 md:grid-cols-2 max-w-2xl mx-auto">
            {[
              "Натальную карту: 12 планет в знаках и домах, аспекты",
              "Факты карты: положения, аспекты, дома и балансы",
              "Синтез: ключевые темы и напряжения",
              "Outline: структура будущего отчёта",
              "Сегменты: narrative-разделы с проверкой качества",
              "Основания: какие факты карты поддерживают вывод",
            ].map((item) => (
              <div key={item} className="flex items-start gap-3">
                <span className="text-[#D8B45A] mt-0.5">✦</span>
                <span className="text-sm text-[#D8DCE8]">{item}</span>
              </div>
            ))}
          </div>
        </section>

        <Divider />

        {/* Для кого */}
        <section className="container mx-auto px-4 pb-20">
          <h2 className="font-[family-name:var(--font-cormorant)] text-2xl font-semibold text-center text-[#F6F1E8] mb-10">
            Для кого
          </h2>
          <div className="grid gap-4 md:grid-cols-3 max-w-3xl mx-auto">
            <div className="text-center space-y-2">
              <p className="text-sm text-[#F6F1E8]">
                Хотите понять свои сильные стороны
              </p>
              <p className="text-xs text-[rgba(216,220,232,0.50)]">
                Не через онлайн-тест, а через систему с объяснимой логикой
              </p>
            </div>
            <div className="text-center space-y-2">
              <p className="text-sm text-[#F6F1E8]">
                Интересуетесь астрологией серьёзно
              </p>
              <p className="text-xs text-[rgba(216,220,232,0.50)]">
                Не гороскоп на день, а натальная карта с конкретными позициями
              </p>
            </div>
            <div className="text-center space-y-2">
              <p className="text-sm text-[#F6F1E8]">
                Важно видеть основания, а не только вывод
              </p>
              <p className="text-xs text-[rgba(216,220,232,0.50)]">
                Каждый результат — с показателем, уверенностью и цепочкой фактов
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[rgba(216,220,232,0.08)] py-8">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <span className="font-[family-name:var(--font-cormorant)] text-sm text-[rgba(216,220,232,0.40)]">
            Astrotype
          </span>
          <span className="text-xs text-[rgba(216,220,232,0.30)]">
            © {new Date().getFullYear()}
          </span>
        </div>
      </footer>
    </div>
  );
}
