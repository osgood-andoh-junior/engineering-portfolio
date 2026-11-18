import { notFound } from "next/navigation";
import { cookies } from "next/headers";
import { Dashboard } from "../../components/dashboard";
import { sessionValid } from "../../lib/admin-session";
import { sections, type Section } from "../../lib/types";

export default async function Page({ params, searchParams }: {
  params: Promise<{ section?: string[] }>; searchParams: Promise<{ auth?: string }>;
}) {
  const { section = [] } = await params;
  const current = section[0] || "overview";
  if (section.length > 1 || !sections.some(([key]) => key === current)) notFound();
  const jar = await cookies();
  const signedIn = Boolean(jar.get("cloudrescue_identity")?.value) ||
    sessionValid(jar.get("cloudrescue_admin")?.value);
  return <Dashboard section={current as Section} signedIn={signedIn}
    invalidLogin={current === "simulation" && (await searchParams).auth === "invalid"} />;
}
