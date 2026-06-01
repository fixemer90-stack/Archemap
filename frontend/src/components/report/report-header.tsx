import type { ReportViewModel } from "@/lib/report/view-model";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function ReportHeader({
  profile,
}: {
  profile: ReportViewModel["profile"];
}) {
  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader>
        <CardDescription>Self-report · понятное чтение карты</CardDescription>
        <CardTitle className="text-3xl">{profile.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <dl className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Дата рождения</dt>
            <dd className="font-medium">{profile.birth_date}</dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Время</dt>
            <dd className="font-medium">
              {profile.birth_time || "Не указано"} · {profile.quality_label}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Место</dt>
            <dd className="font-medium">{profile.birth_place}</dd>
          </div>
        </dl>
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm leading-6">
          {profile.quality_notice}
        </div>
      </CardContent>
    </Card>
  );
}
