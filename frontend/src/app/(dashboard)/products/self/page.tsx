"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useAuthStore } from "@/stores/auth-store";

interface Profile {
  id: string;
  name: string;
  birth_date: string;
  birth_place: string;
}

export default function SelfProductPage() {
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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-[family-name:var(--font-cormorant)] text-3xl font-semibold text-[#F6F1E8]">
            Archemap Self
          </h1>
          <p className="text-sm text-[#D8DCE8] mt-1">
            Натальная карта, соционический тип, архетипический профиль.
          </p>
        </div>
        <Button asChild>
          <Link href="/register">
            <Plus className="h-4 w-4 mr-1" />
            Новый отчёт
          </Link>
        </Button>
      </div>

      {/* What you get */}
      <div className="glass p-6 space-y-4">
        <h2 className="font-[family-name:var(--font-cormorant)] text-lg font-semibold text-[#F6F1E8]">
          Что входит в отчёт
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            "Натальная карта: 12 планет в знаках и домах, аспекты",
            "Соционический тип: 16 типов, 8 функций, радар профиля",
            "Архетипический профиль: 8 архетипов с score и confidence",
            "Evidence trail: факты → правила → выводы для каждого claim",
          ].map((item) => (
            <div key={item} className="flex items-start gap-2">
              <span className="text-[#D8B45A] mt-0.5 text-xs">✦</span>
              <span className="text-sm text-[#D8DCE8]">{item}</span>
            </div>
          ))}
        </div>
      </div>

      {/* My reports */}
      {profiles.length > 0 && (
        <div className="space-y-4">
          <h2 className="font-[family-name:var(--font-cormorant)] text-xl font-semibold text-[#F6F1E8]">
            Мои отчёты Self
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

      {/* Empty state */}
      {!loading && profiles.length === 0 && (
        <div className="glass p-8 text-center space-y-4">
          <p className="text-[#D8DCE8]">
            У вас пока нет отчётов Self. Введите данные рождения и получите свою
            карту.
          </p>
          <Button asChild>
            <Link href="/register">
              Построить карту
              <ArrowRight className="h-4 w-4 ml-1" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  );
}
