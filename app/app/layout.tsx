import type { Metadata } from "next";
import { Plus_Jakarta_Sans, Geist_Mono, Michroma } from "next/font/google";
import "./globals.css";

const plusJakartaSans = Plus_Jakarta_Sans({
  variable: "--font-plus-jakarta",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
});

const michroma = Michroma({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-michroma",
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Varve - AI Risk & Decision Intelligence Platform",
  description: "Catch silent, undocumented ML pipeline debt before it becomes an incident — ranked by empirical precedent, honestly labeled by evidence tier, and ledgered.",
  icons: {
    icon: "/varve_logo.png",
    shortcut: "/varve_logo.png",
    apple: "/varve_logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${plusJakartaSans.variable} ${michroma.variable} ${geistMono.variable} h-full antialiased font-sans`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
