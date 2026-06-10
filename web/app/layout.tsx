import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Allocator Memo Builder",
  description: "Messy fund universe → defendable IC memo",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
