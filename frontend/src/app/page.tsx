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
            Archemap
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
            Archemap — это не гадалка и не предсказание судьбы. Это{" "}
            <span className="text-[#F6F1E8]">
              премиальная система самопознания
            </span>
            , которая строит вашу натальную карту, вычисляет соционический тип и
            показывает{" "}
            <span className="text-[#8DA8FF]">основания каждого вывода</span>.
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
                12 планет, 12 домов, аспекты с орбами. Вычисляется по Swiss
                Ephemeris с точностью ±0.01°. Каждая позиция — факт, не
                интерпретация.
              </p>
            </div>

            {/* Соционика */}
            <div className="glass p-6 space-y-3">
              <div className="text-[#5B3FD6] text-2xl">◆</div>
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Соционический тип
              </h3>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                Model A: 8 функций, 16 типов. Top-3 с score и confidence. Радар
                функционального профиля — Se, Si, Ne, Ni, Fe, Fi, Te, Ti.
              </p>
            </div>

            {/* Архетипы */}
            <div className="glass p-6 space-y-3">
              <div className="text-[#8DA8FF] text-2xl">⬡</div>
              <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                Архетипический профиль
              </h3>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                8 архетипов: Стратег, Творец, Исследователь, Опора, Дипломат,
                Катализатор, Наставник, Строитель. Каждый — с evidence trail.
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
                  Дата, время, место. Если время неизвестно — система это укажет
                  и снизит confidence.
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
                  Swiss Ephemeris строит карту. Нормализованные признаки
                  извлекаются автоматически: стихии, модальности, дома, аспекты.
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
                  Rule-based движок оценивает архетипы. Каждый вывод — score,
                  confidence, evidence, counter-evidence. Никакого AI в
                  рантайме.
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
              "Натальную карту с позициями 12 планет",
              "Соционический тип с Model A (8 функций)",
              "Архетипический профиль (8 архетипов)",
              "Score и confidence для каждого вывода",
              "Evidence trail: факты → правила → выводы",
              "Версию движка и правил для воспроизводимости",
            ].map((item) => (
              <div key={item} className="flex items-start gap-3">
                <span className="text-[#D8B45A] mt-0.5">✦</span>
                <span className="text-sm text-[#D8DCE8]">{item}</span>
              </div>
            ))}
          </div>
        </section>

        <Divider />

        {/* Позиционирование */}
        <section className="container mx-auto px-4 pb-20">
          <div className="glass p-8 max-w-2xl mx-auto text-center space-y-4">
            <p className="text-[#D8DCE8] text-sm leading-relaxed">
              Archemap — это{" "}
              <span className="text-[#F6F1E8]">не эзотерическая гадалка</span>.
              Это премиальная карта самопознания: астрологическая символика,
              психологическая структура, объяснимые выводы и спокойный
              навигационный интерфейс.
            </p>
            <p className="text-[rgba(216,220,232,0.50)] text-xs">
              Мы не предсказываем судьбу. Мы показываем гипотезы, веса и
              основания.
            </p>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="relative z-10 border-t border-[rgba(216,220,232,0.08)] py-8">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <span className="font-[family-name:var(--font-cormorant)] text-sm text-[rgba(216,220,232,0.40)]">
            Archemap
          </span>
          <span className="text-xs text-[rgba(216,220,232,0.30)]">
            © {new Date().getFullYear()}
          </span>
        </div>
      </footer>
    </div>
  );
}
