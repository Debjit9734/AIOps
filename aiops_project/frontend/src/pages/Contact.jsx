import React from "react";

function Contact() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_15%_15%,rgba(14,165,233,0.22),transparent_28%),linear-gradient(180deg,#eaf6ff,#e2ebf4_66%,#f1f5f9)] px-5 pb-20 pt-32">
      <div className="mx-auto grid max-w-6xl items-center gap-8 lg:grid-cols-[0.9fr_1.1fr]">
        <section>
          <p className="text-sm font-semibold text-blue-600">Contact</p>
          <h1 className="mt-3 text-5xl font-semibold tracking-tight text-zinc-950 sm:text-6xl">
            Let’s shape your deployment flow.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-zinc-600">
            Share what you are building and where you want to deploy. We typically respond within
            1-2 business days.
          </p>
          <a href="mailto:support@aiops.com" className="mt-8 inline-flex rounded-full bg-zinc-950 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-zinc-950/20 transition duration-300 hover:-translate-y-0.5">
            support@aiops.com
          </a>
        </section>

        <form className="rounded-[2rem] border border-sky-100/80 bg-sky-50/72 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur-2xl sm:p-8">
          <div className="grid gap-5">
          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-700">Name</label>
            <input type="text" className="w-full rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100" placeholder="Your name" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-700">Email</label>
            <input type="email" className="w-full rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100" placeholder="you@example.com" />
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium text-zinc-700">Message</label>
            <textarea className="h-32 w-full resize-y rounded-2xl border border-zinc-200 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100" placeholder="How can we help?"></textarea>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <button type="submit" className="rounded-full bg-zinc-950 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-zinc-950/20 transition duration-300 hover:-translate-y-0.5 hover:bg-black">Send Message</button>
            <span className="text-sm text-zinc-500">We keep replies focused and practical.</span>
          </div>
          </div>
        </form>
      </div>
    </main>
  );
}

export default Contact;
