import React from "react";

function HomePage() {
  const highlights = [
    { value: "3", label: "cloud targets" },
    { value: "5", label: "guided stages" },
    { value: "1", label: "deployable bundle" },
  ];

  return (
    <main className="relative min-h-screen overflow-hidden pt-28">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_15%,rgba(14,165,233,0.24),transparent_30%),radial-gradient(circle_at_85%_25%,rgba(99,102,241,0.13),transparent_28%),linear-gradient(180deg,#eaf6ff_0%,#e2ebf4_64%,#f1f5f9_100%)]" />
      <section className="relative mx-auto grid min-h-[calc(100vh-7rem)] max-w-6xl items-center gap-10 px-5 pb-16 lg:grid-cols-[1.08fr_0.92fr]">
        <div className="max-w-3xl">
          <p className="mb-5 inline-flex rounded-full border border-white/80 bg-white/70 px-4 py-2 text-sm font-medium text-zinc-600 shadow-sm backdrop-blur-xl">
            Intelligent deployment planning for beginners
          </p>
          <h1 className="max-w-4xl text-5xl font-semibold tracking-tight text-zinc-950 sm:text-6xl lg:text-7xl">
            Deploy smarter with detailed guidelines that feels effortless.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-zinc-600">
            Analyze repositories, understand the stack, and generate a cloud deployment path with a calm,
            polished interface built for focus.
          </p>
          <div className="mt-9 flex flex-wrap gap-3">
            <a href="/deployment-guide" className="rounded-full bg-zinc-950 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-zinc-950/20 transition duration-300 hover:-translate-y-0.5 hover:bg-black">
              Open Deployment Studio
            </a>
            <a href="/services" className="rounded-full border border-sky-100 bg-sky-50/75 px-6 py-3 text-sm font-semibold text-zinc-800 shadow-sm backdrop-blur-xl transition duration-300 hover:-translate-y-0.5 hover:bg-white">
              Explore Services
            </a>
          </div>
          <div className="mt-12 grid max-w-xl grid-cols-3 gap-3">
            {highlights.map((item) => (
              <div key={item.label} className="rounded-3xl border border-sky-100/80 bg-sky-50/65 p-5 shadow-sm backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:shadow-xl hover:shadow-sky-200/40">
                <strong className="block text-3xl font-semibold tracking-tight text-zinc-950">{item.value}</strong>
                <span className="mt-1 block text-sm text-zinc-500">{item.label}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-md">
          <div className="absolute -inset-6 rounded-[3rem] bg-gradient-to-br from-sky-400/25 via-slate-200 to-cyan-300/20 blur-2xl" />
          <div className="relative rounded-[2.2rem] border border-sky-100/80 bg-sky-50/75 p-4 shadow-[0_30px_90px_rgba(15,23,42,0.18)] backdrop-blur-2xl">
            <div className="rounded-[1.7rem] bg-zinc-950 p-5 text-white">
              <div className="mb-8 flex items-center justify-between">
                <span className="text-sm text-white/60">AIOps Runtime</span>
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_22px_rgba(52,211,153,0.9)]" />
              </div>
              <div className="space-y-4">
                {["Analyze repository", "Detect stack", "Generate runbook"].map((label, index) => (
                  <div key={label} className="flex items-center justify-between rounded-2xl bg-white/[0.08] p-4">
                    <span className="text-sm font-medium">{label}</span>
                    <span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-zinc-950">
                      {index === 2 ? "Ready" : "Done"}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-5 rounded-2xl bg-gradient-to-br from-blue-500 to-cyan-300 p-5 text-zinc-950">
                <p className="text-sm font-medium opacity-70">Recommended path</p>
                <h2 className="mt-2 text-2xl font-semibold tracking-tight">EC2 + Docker</h2>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

export default HomePage;
