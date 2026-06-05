import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import type { CareerCTAViewModel } from "@/lib/report/view-model";

interface CareerCTAProps {
  cta: CareerCTAViewModel;
  profileId: string;
}

export function CareerCTA({ cta, profileId }: CareerCTAProps) {
  return (
    <Card className="border-[#C28A2E]/30">
      <CardHeader>
        <CardDescription>Карьерный отчёт</CardDescription>
        <CardTitle>{cta.title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm leading-6 text-muted-foreground">
        <p>{cta.body}</p>
        {cta.bullets.length > 0 && (
          <ul className="grid grid-cols-1 gap-2 sm:grid-cols-3">
            {cta.bullets.map((bullet) => (
              <li key={bullet} className="rounded-lg bg-muted/50 p-3">
                {bullet}
              </li>
            ))}
          </ul>
        )}
        <Button asChild>
          <Link href={`/dashboard/products/career?profileId=${profileId}`}>
            {cta.button_label}
          </Link>
        </Button>
      </CardContent>
    </Card>
  );
}
