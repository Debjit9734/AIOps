import React from "react";

function Services() {
  const services = [
    {
      title: "Repository intelligence",
      text: "Stack detection, dependency signals, and actionable readiness checks before deployment.",
    },
    {
      title: "Cloud route planning",
      text: "AWS, GCP, and Azure deployment recommendations tuned for beginner-friendly execution.",
    },
    {
      title: "Runbook generation",
      text: "Step-by-step commands, required files, and resource sizing packaged for delivery.",
    },
  ];

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_50%_0%,rgba(14,165,233,0.18),transparent_28%),linear-gradient(180deg,#eaf6ff,#e2ebf4_62%,#f1f5f9)] px-5 pb-20 pt-32">
      <section className="mx-auto max-w-6xl">
        <div className="mx-auto max-w-3xl text-center">
          <p className="text-sm font-semibold text-blue-600">Services</p>
          <h1 className="mt-3 text-5xl font-semibold tracking-tight text-zinc-950 sm:text-6xl">
            A quieter way to move from code to cloud.
          </h1>
          <p className="mt-5 text-lg leading-8 text-zinc-600">
            Every service is designed around clarity, motion, and confident next steps.
          </p>
        </div>

        <div className="mt-14 grid gap-5 md:grid-cols-3">
          {services.map((service, index) => (
            <article key={service.title} className="group rounded-[2rem] border border-sky-100/80 bg-sky-50/70 p-7 shadow-sm backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:shadow-2xl hover:shadow-sky-200/45">
              <div className="mb-12 grid h-12 w-12 place-items-center rounded-2xl bg-zinc-950 text-sm font-semibold text-white">
                0{index + 1}
              </div>
              <h2 className="text-2xl font-semibold tracking-tight text-zinc-950">{service.title}</h2>
              <p className="mt-4 leading-7 text-zinc-600">{service.text}</p>
              <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-zinc-100">
                <div className="h-full w-2/3 rounded-full bg-gradient-to-r from-blue-500 to-emerald-400 transition-all duration-500 group-hover:w-full" />
              </div>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

export default Services;
