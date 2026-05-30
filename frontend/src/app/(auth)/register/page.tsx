"use client";

import { Suspense, useState, useCallback, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuthStore } from "@/stores/auth-store";

// ── Types ──────────────────────────────────────────────────────────
interface GeocodeResult {
  display_name: string;
  latitude: number;
  longitude: number;
  city: string;
  country: string;
}

interface RegisterData {
  email: string;
  password: string;
  birth_date: string;
  birth_time: string;
  birth_time_accuracy: "exact" | "approximate" | "unknown";
  birth_place: string;
  latitude: number;
  longitude: number;
  timezone: string;
}

// ── Steps ──────────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: "Аккаунт" },
  { id: 2, label: "Данные рождения" },
  { id: 3, label: "Подтверждение" },
];

export default function RegisterPage() {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <RegisterForm />
    </Suspense>
  );
}

function RegisterForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);

  const [step, setStep] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Step 1: Credentials
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");

  // Step 2: Birth data
  const [birthDate, setBirthDate] = useState("");
  const [birthTime, setBirthTime] = useState("");
  const [birthTimeAccuracy, setBirthTimeAccuracy] = useState<
    "exact" | "approximate" | "unknown"
  >("unknown");
  const [birthPlace, setBirthPlace] = useState("");
  const [latitude, setLatitude] = useState(0);
  const [longitude, setLongitude] = useState(0);
  const [timezone, setTimezone] = useState("");

  // Geocoding
  const [placeQuery, setPlaceQuery] = useState("");
  const [placeResults, setPlaceResults] = useState<GeocodeResult[]>([]);
  const [placeLoading, setPlaceLoading] = useState(false);
  const [showPlaceDropdown, setShowPlaceDropdown] = useState(false);
  const placeDebounceRef = useRef<NodeJS.Timeout>(undefined);

  // Pre-fill from OAuth callback
  useEffect(() => {
    const oauthBirthDate = searchParams.get("birth_date");
    if (oauthBirthDate) {
      setBirthDate(oauthBirthDate);
      setStep(2); // Jump to birth data step
    }
  }, [searchParams]);

  // ── Geocoding search ──────────────────────────────────────────────
  const searchPlace = useCallback(async (query: string) => {
    if (query.length < 2) {
      setPlaceResults([]);
      return;
    }

    setPlaceLoading(true);
    try {
      const res = await fetch(
        `/api/v1/profiles/geocode?q=${encodeURIComponent(query)}`,
      );
      if (res.ok) {
        const data = await res.json();
        setPlaceResults(data.items || []);
        setShowPlaceDropdown(true);
      }
    } catch {
      // Silently fail
    } finally {
      setPlaceLoading(false);
    }
  }, []);

  const handlePlaceChange = (value: string) => {
    setPlaceQuery(value);
    setBirthPlace("");

    if (placeDebounceRef.current) {
      clearTimeout(placeDebounceRef.current);
    }

    placeDebounceRef.current = setTimeout(() => {
      searchPlace(value);
    }, 300);
  };

  const selectPlace = (result: GeocodeResult) => {
    setPlaceQuery(result.display_name);
    setBirthPlace(result.display_name);
    setLatitude(result.latitude);
    setLongitude(result.longitude);
    setShowPlaceDropdown(false);
    // Timezone will be determined by backend
    setTimezone("Europe/Moscow"); // Default, backend will correct
  };

  // ── Validation ────────────────────────────────────────────────────
  const validateStep1 = () => {
    if (!email || !password || !passwordConfirm) {
      setError("Заполните все поля");
      return false;
    }
    if (password.length < 8) {
      setError("Пароль должен быть не менее 8 символов");
      return false;
    }
    if (password !== passwordConfirm) {
      setError("Пароли не совпадают");
      return false;
    }
    return true;
  };

  const validateStep2 = () => {
    if (!birthDate) {
      setError("Укажите дату рождения");
      return false;
    }
    if (!birthPlace) {
      setError("Укажите место рождения");
      return false;
    }
    if (birthTimeAccuracy !== "unknown" && !birthTime) {
      setError("Укажите время рождения");
      return false;
    }
    return true;
  };

  // ── Navigation ────────────────────────────────────────────────────
  const nextStep = () => {
    setError("");
    if (step === 1 && validateStep1()) {
      setStep(2);
    } else if (step === 2 && validateStep2()) {
      setStep(3);
    }
  };

  const prevStep = () => {
    setError("");
    if (step > 1) setStep(step - 1);
  };

  // ── Submit ────────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setError("");
    setLoading(true);

    try {
      const body: RegisterData = {
        email,
        password,
        birth_date: birthDate,
        birth_time: birthTimeAccuracy === "unknown" ? "12:00" : birthTime,
        birth_time_accuracy: birthTimeAccuracy,
        birth_place: birthPlace,
        latitude,
        longitude,
        timezone,
      };

      const res = await fetch("/api/v1/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || "Registration failed");
      }

      const result = await res.json();

      // Store tokens and user
      setTokens(result.access_token, result.refresh_token);
      setUser({
        id: result.user_id,
        email: result.email,
        is_active: true,
      });

      // Redirect to report page with chart data
      router.push(`/report/${result.profile_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  // ── Step 1: Credentials ───────────────────────────────────────────
  const renderStep1 = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="email" className="text-sm font-medium">
          Email
        </label>
        <Input
          id="email"
          type="email"
          placeholder="you@example.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="password" className="text-sm font-medium">
          Пароль
        </label>
        <Input
          id="password"
          type="password"
          placeholder="Минимум 8 символов"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
        />
      </div>

      <div className="space-y-2">
        <label htmlFor="passwordConfirm" className="text-sm font-medium">
          Подтвердите пароль
        </label>
        <Input
          id="passwordConfirm"
          type="password"
          placeholder="Повторите пароль"
          value={passwordConfirm}
          onChange={(e) => setPasswordConfirm(e.target.value)}
          required
        />
      </div>

      <Button onClick={nextStep} className="w-full">
        Далее
      </Button>
    </div>
  );

  // ── Step 2: Birth Data ────────────────────────────────────────────
  const renderStep2 = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <label htmlFor="birthDate" className="text-sm font-medium">
          Дата рождения
        </label>
        <Input
          id="birthDate"
          type="date"
          value={birthDate}
          onChange={(e) => setBirthDate(e.target.value)}
          max={new Date().toISOString().split("T")[0]}
          min="1900-01-01"
          required
        />
      </div>

      <div className="space-y-2">
        <label className="text-sm font-medium">Время рождения</label>
        <div className="flex flex-col gap-2">
          {(["exact", "approximate", "unknown"] as const).map((accuracy) => (
            <label
              key={accuracy}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="radio"
                name="birthTimeAccuracy"
                value={accuracy}
                checked={birthTimeAccuracy === accuracy}
                onChange={() => setBirthTimeAccuracy(accuracy)}
                className="h-4 w-4"
              />
              <span className="text-sm">
                {accuracy === "exact" && "Точно знаю время"}
                {accuracy === "approximate" && "Примерно знаю"}
                {accuracy === "unknown" && "Не знаю время"}
              </span>
            </label>
          ))}
        </div>

        {birthTimeAccuracy !== "unknown" && (
          <Input
            type="time"
            value={birthTime}
            onChange={(e) => setBirthTime(e.target.value)}
            required
          />
        )}

        {birthTimeAccuracy === "unknown" && (
          <p className="text-xs text-muted-foreground">
            Будет использовано 12:00 как приблизительное время
          </p>
        )}
      </div>

      <div className="space-y-2 relative">
        <label htmlFor="birthPlace" className="text-sm font-medium">
          Место рождения
        </label>
        <Input
          id="birthPlace"
          type="text"
          placeholder="Начните вводить город..."
          value={placeQuery}
          onChange={(e) => handlePlaceChange(e.target.value)}
          onFocus={() => placeResults.length > 0 && setShowPlaceDropdown(true)}
          onBlur={() => setTimeout(() => setShowPlaceDropdown(false), 200)}
          required
        />
        {placeLoading && (
          <p className="text-xs text-muted-foreground">Поиск...</p>
        )}
        {showPlaceDropdown && placeResults.length > 0 && (
          <div className="absolute z-10 w-full mt-1 bg-background border rounded-md shadow-lg max-h-60 overflow-auto">
            {placeResults.map((result, i) => (
              <button
                key={i}
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-muted cursor-pointer"
                onMouseDown={() => selectPlace(result)}
              >
                <div className="font-medium">{result.city}</div>
                <div className="text-xs text-muted-foreground">
                  {result.country}
                </div>
              </button>
            ))}
          </div>
        )}
        {birthPlace && (
          <p className="text-xs text-muted-foreground">Выбрано: {birthPlace}</p>
        )}
      </div>

      <div className="flex gap-2">
        <Button variant="outline" onClick={prevStep} className="flex-1">
          Назад
        </Button>
        <Button onClick={nextStep} className="flex-1">
          Далее
        </Button>
      </div>
    </div>
  );

  // ── Step 3: Confirmation ──────────────────────────────────────────
  const renderStep3 = () => (
    <div className="space-y-4">
      <div className="rounded-lg border p-4 space-y-3">
        <h3 className="font-medium">Проверьте данные</h3>

        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="text-muted-foreground">Email:</div>
          <div>{email}</div>

          <div className="text-muted-foreground">Дата рождения:</div>
          <div>{birthDate}</div>

          <div className="text-muted-foreground">Время:</div>
          <div>
            {birthTimeAccuracy === "unknown"
              ? "Неизвестно (12:00)"
              : `${birthTime} (${birthTimeAccuracy === "exact" ? "точное" : "приблизительное"})`}
          </div>

          <div className="text-muted-foreground">Место:</div>
          <div>{birthPlace}</div>

          <div className="text-muted-foreground">Координаты:</div>
          <div>
            {latitude.toFixed(4)}, {longitude.toFixed(4)}
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        После регистрации сразу будет рассчитана ваша натальная карта и
        соционический тип.
      </p>

      <div className="flex gap-2">
        <Button variant="outline" onClick={prevStep} className="flex-1">
          Назад
        </Button>
        <Button onClick={handleSubmit} className="flex-1" disabled={loading}>
          {loading ? "Регистрация..." : "Зарегистрироваться"}
        </Button>
      </div>
    </div>
  );

  return (
    <div className="w-full max-w-sm space-y-6">
      <div className="text-center">
        <h1 className="text-2xl font-bold">Создать аккаунт</h1>
        <p className="text-sm text-muted-foreground">
          {step === 1 && "Введите email и пароль"}
          {step === 2 && "Укажите данные рождения"}
          {step === 3 && "Проверьте и подтвердите"}
        </p>
      </div>

      {/* Progress */}
      <div className="flex justify-between">
        {STEPS.map((s) => (
          <div
            key={s.id}
            className={`flex items-center gap-2 ${
              step >= s.id ? "text-primary" : "text-muted-foreground"
            }`}
          >
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                step >= s.id ? "bg-primary text-primary-foreground" : "bg-muted"
              }`}
            >
              {s.id}
            </div>
            <span className="text-xs hidden sm:block">{s.label}</span>
          </div>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Steps */}
      {step === 1 && renderStep1()}
      {step === 2 && renderStep2()}
      {step === 3 && renderStep3()}

      {/* OAuth */}
      {step === 1 && (
        <>
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Или
              </span>
            </div>
          </div>

          <Button
            variant="outline"
            className="w-full"
            onClick={() =>
              (window.location.href = "/api/v1/auth/oauth/yandex/start")
            }
          >
            <svg
              className="mr-2 h-4 w-4"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <path d="M22.42 0H1.58C.71 0 0 .71 0 1.58v20.84C0 23.29.71 24 1.58 24h20.84c.87 0 1.58-.71 1.58-1.58V1.58C24 .71 23.29 0 22.42 0z" />
              <path
                d="M17.15 19.24h-2.73c-1.96 0-2.97-1.1-2.97-2.73 0-1.4.66-2.34 1.73-3.1.78-.56 1.27-.95 1.27-1.76 0-.72-.52-1.16-1.38-1.16-.97 0-1.63.54-2.08 1.32l-1.48-.95C10.35 9.7 11.35 9 12.8 9c1.82 0 3.06 1.05 3.06 2.76 0 1.52-.82 2.5-1.78 3.18-.8.57-1.14.96-1.14 1.65 0 .66.54 1.12 1.35 1.12h1.74v1.53h.12z"
                fill="white"
              />
            </svg>
            Войти через Яндекс
          </Button>
        </>
      )}

      {/* Login link */}
      <p className="text-center text-sm text-muted-foreground">
        Уже есть аккаунт?{" "}
        <Link href="/login" className="text-primary hover:underline">
          Войти
        </Link>
      </p>
    </div>
  );
}
