import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Kexpense - Quản lý Chi tiêu Thông minh",
  description: "Tự động hóa ghi chép chi tiêu từ hóa đơn bằng AI Hybrid OCR",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "Kexpense",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
  themeColor: "#2563eb",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen flex flex-col bg-slate-50 dark:bg-zinc-950">
        <main className="flex-1 max-w-md mx-auto w-full pb-20 shadow-sm bg-white dark:bg-zinc-900 min-h-screen">
          {children}
        </main>
      </body>
    </html>
  );
}
