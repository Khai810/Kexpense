import { Camera, Receipt, TrendingUp, Sparkles, CheckCircle2 } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen px-4 pt-6 pb-24">
      {/* Header */}
      <header className="flex items-center justify-between pb-4 border-b border-slate-100 dark:border-zinc-800">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-blue-600" />
            Kexpense
          </h1>
          <p className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5">
            Smart Expense OCR v1.0
          </p>
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 text-xs font-medium">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>Hệ thống sẵn sàng</span>
        </div>
      </header>

      {/* Hero Quick Scan Section */}
      <section className="mt-6 p-6 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 text-white shadow-md text-center">
        <h2 className="text-lg font-semibold">Chụp Hóa Đơn Tự Động</h2>
        <p className="text-xs text-blue-100 mt-1 max-w-xs mx-auto">
          Ứng dụng kiến trúc Hybrid Vision & Gemini Flash để bóc tách 100% dòng sản phẩm và chi tiêu.
        </p>

        <div className="mt-6 flex justify-center">
          <button
            type="button"
            className="flex items-center gap-2 bg-white text-blue-600 font-semibold px-6 py-3 rounded-full shadow-lg hover:bg-blue-50 active:scale-95 transition-all text-sm"
          >
            <Camera className="w-5 h-5" />
            <span>Quét Hóa Đơn Ngay</span>
          </button>
        </div>
      </section>

      {/* Feature Highlights */}
      <section className="mt-8 space-y-3">
        <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-zinc-500 px-1">
          Tính năng cốt lõi
        </h3>

        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
            <div className="p-2 w-fit rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-600 mb-2">
              <Receipt className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-zinc-200">
              Bóc Tách Từng Món
            </h4>
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5">
              Tách đơn giá, số lượng và cân đối toán học.
            </p>
          </div>

          <div className="p-4 rounded-xl border border-slate-200 dark:border-zinc-800 bg-white dark:bg-zinc-900">
            <div className="p-2 w-fit rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 mb-2">
              <TrendingUp className="w-4 h-4" />
            </div>
            <h4 className="text-sm font-semibold text-slate-800 dark:text-zinc-200">
              Phân Tích Chi Tiêu
            </h4>
            <p className="text-xs text-slate-500 dark:text-zinc-400 mt-0.5">
              Gán danh mục tự động và trực quan hóa tức thì.
            </p>
          </div>
        </div>
      </section>

      {/* System Status info */}
      <section className="mt-auto pt-6 text-center text-xs text-slate-400 dark:text-zinc-500">
        <p>Kiến trúc Hybrid OCR • Next.js 15 PWA • FastAPI</p>
      </section>
    </div>
  );
}
