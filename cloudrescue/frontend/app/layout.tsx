import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CloudRescue | Operations Dashboard",
  description: "Local cloud outage detection and recovery simulator",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
