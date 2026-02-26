import { UserProfile } from "@clerk/nextjs";

export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Settings</h1>
      <UserProfile />
    </div>
  );
}
