import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Settings",
};

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and preferences.
        </p>
      </div>

      <div className="space-y-4">
        {[
          { title: "Profile", description: "Update your personal information" },
          { title: "Notifications", description: "Configure alert preferences" },
          { title: "Security", description: "Password and two-factor authentication" },
          { title: "Appearance", description: "Theme and display settings" },
        ].map((section) => (
          <div
            key={section.title}
            className="flex items-center justify-between rounded-lg border bg-card p-4 shadow-sm"
          >
            <div>
              <h3 className="font-medium">{section.title}</h3>
              <p className="text-sm text-muted-foreground">
                {section.description}
              </p>
            </div>
            <button className="inline-flex h-9 items-center rounded-md border px-3 text-sm font-medium hover:bg-accent transition-colors">
              Configure
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
