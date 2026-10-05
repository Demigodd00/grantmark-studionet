import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GRANTMARK — Make every milestone count",
  description:
    "Evidence-backed grants with locked milestones, independent GenLayer adjudication, and on-chain tranche settlement.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
