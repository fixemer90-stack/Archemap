import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface ReportPdfActionsProps {
  isDownloading: boolean;
  onDownload: () => void | Promise<void>;
}

export function ReportPdfActions({
  isDownloading,
  onDownload,
}: ReportPdfActionsProps) {
  return (
    <Card className="border-primary/20 bg-primary/5">
      <CardHeader>
        <CardTitle>Сохранить этот разбор</CardTitle>
        <CardDescription>
          PDF-версия пригодится, если хотите вернуться к отчёту позже или
          спокойно перечитать его вне сервиса.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm leading-6 text-muted-foreground">
          Скачивание не уводит со страницы: файл собирается на лету из текущего
          отчёта.
        </p>
        <Button onClick={onDownload} disabled={isDownloading}>
          {isDownloading ? "Собираем PDF..." : "Сохранить PDF"}
        </Button>
      </CardContent>
    </Card>
  );
}
