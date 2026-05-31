"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { User, Heart, Baby, Briefcase, ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

interface Profile {
  id: string;
  name: string;
  birth_date: string;
  birth_place: string;
}

const products = [
  {
    id: "self",
    title: "Archemap Self",
    description:
      "Натальная карта, соционический тип, архетипический профиль с evidence trail.",
    icon: User,
    color: "#5B3FD6",
    accent: "#D8B45A",
    status: "available",
    href: "/products/self",
  },
  {
    id: "love",
    title: "Archemap Love",
    description:
      "Совместимость двух людей: синастрия, паттерны отношений, точки притяжения и напряжения.",
    icon: Heart,
    color: "#B84A6B",
    accent: "#E57A7A",
    status: "coming_soon",
    href: "/products/love",
  },
  {
    id: "child",
    title: "Archemap Child",
    description:
      "Профиль ребёнка: темперамент, сильные стороны, рекомендации по воспитанию.",
    icon: Baby,
    color: "#6BAFBD",
    accent: "#8DA8FF",
    status: "coming_soon",
    href: "/products/child",
  },
  {
    id: "career",
    title: "Archemap Career",
    description:
      "Карьерные сценарии: роли, рабочая среда, сильные профессиональные стороны.",
    icon: Briefcase,
    color: "#C28A2E",
    accent: "#D8B45A",
    status: "coming_soon",
    href: "/products/career",
  },
];

export default function DashboardPage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const token = useAuthStore((s) => s.token);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProfiles() {
      if (!token) return;
      try {
        const res = await fetch("/api/v1/profiles", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setProfiles(data.items || []);
        }
      } catch {
        // Silently fail
      } finally {
        setLoading(false);
      }
    }
    fetchProfiles();
  }, [token]);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
          {user?.email ? `Добро пожаловать` : "Добро пожаловать"}
        </h1>
        <p className="text-sm text-[#D8DCE8] mt-1">
          Выберите продукт или откройте существующий отчёт.
        </p>
      </div>

      {/* My Reports */}
      {profiles.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Мои отчёты
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {profiles.map((profile) => (
              <Link
                key={profile.id}
                href={`/report/${profile.id}`}
                className="glass p-5 space-y-2 hover:border-[rgba(91,63,214,0.40)] transition-all group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[#F6F1E8]">
                    {profile.name || "Без имени"}
                  </span>
                  <ArrowRight className="h-4 w-4 text-[rgba(216,220,232,0.30)] group-hover:text-[#D8B45A] transition-colors" />
                </div>
                <p className="text-xs text-[rgba(216,220,232,0.50)]">
                  {profile.birth_date} · {profile.birth_place}
                </p>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Products */}
      <div className="space-y-4">
        <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
          Продукты
        </h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {products.map((product) => (
            <div
              key={product.id}
              className={`glass p-6 space-y-3 transition-all ${
                product.status === "coming_soon"
                  ? "opacity-60"
                  : "hover:border-[rgba(91,63,214,0.40)]"
              }`}
            >
              <div className="flex items-center gap-3">
                <div
                  className="w-10 h-10 rounded-xl flex items-center justify-center"
                  style={{ background: `${product.color}20` }}
                >
                  <product.icon
                    className="h-5 w-5"
                    style={{ color: product.color }}
                  />
                </div>
                <div>
                  <h3 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
                    {product.title}
                  </h3>
                  {product.status === "coming_soon" && (
                    <span className="text-[10px] text-[rgba(216,220,232,0.40)] px-2 py-0.5 rounded-full border border-[rgba(216,220,232,0.15)]">
                      скоро
                    </span>
                  )}
                </div>
              </div>
              <p className="text-sm text-[#D8DCE8] leading-relaxed">
                {product.description}
              </p>
              {product.status === "available" ? (
                <Button asChild size="sm" className="mt-2">
                  <Link href={product.href}>
                    Открыть
                    <ArrowRight className="h-3 w-3 ml-1" />
                  </Link>
                </Button>
              ) : (
                <Button size="sm" variant="outline" disabled className="mt-2">
                  Скоро
                </Button>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Empty state */}
      {!loading && profiles.length === 0 && (
        <div className="glass p-8 text-center space-y-4">
          <p className="text-[#D8DCE8]">
            У вас пока нет отчётов. Начните с продукта Self — постройте свою
            натальную карту.
          </p>
          <Button asChild>
            <Link href="/products/self">
              Построить карту
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
