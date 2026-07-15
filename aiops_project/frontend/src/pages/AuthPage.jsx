import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginUser, registerUser } from "../api";

function AuthPage({ mode }) {
  const isRegister = mode === "register";
  const navigate = useNavigate();
  const [form, setForm] = useState({
    username: "",
    email: "",
    password: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const onChange = (event) => {
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      if (isRegister) {
        await registerUser(form);
      } else {
        await loginUser(form);
      }
      navigate("/deployment-guide");
    } catch (err) {
      setError(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_16%_18%,rgba(14,165,233,0.22),transparent_30%),radial-gradient(circle_at_82%_12%,rgba(99,102,241,0.13),transparent_28%),linear-gradient(180deg,#eaf6ff,#e2ebf4_66%,#f1f5f9)] px-5 pb-20 pt-32">
      <section className="mx-auto grid max-w-6xl items-center gap-8 lg:grid-cols-[0.95fr_1.05fr]">
        <div>
          <p className="text-sm font-semibold text-blue-600">Account</p>
          <h1 className="mt-3 max-w-xl text-5xl font-semibold tracking-tight text-zinc-950 sm:text-6xl">
            {isRegister ? "Create your AIOps account." : "Welcome back to AIOps."}
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-8 text-zinc-600">
            Sign in to track your repository analyses. Regular users get 3 analyses per day,
            while admins can analyze without limits.
          </p>
        </div>

        <form
          onSubmit={onSubmit}
          className="rounded-[2rem] border border-sky-100/80 bg-sky-50/72 p-6 shadow-[0_24px_80px_rgba(15,23,42,0.12)] backdrop-blur-2xl sm:p-8"
        >
          <div className="mb-7">
            <h2 className="text-3xl font-semibold tracking-tight text-zinc-950">
              {isRegister ? "Register" : "Login"}
            </h2>
            <p className="mt-2 text-sm text-zinc-500">
              {isRegister ? "Choose a username and password." : "Use your registered username."}
            </p>
          </div>

          <div className="grid gap-5">
            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-700">Username</label>
              <input
                name="username"
                value={form.username}
                onChange={onChange}
                className="w-full rounded-2xl border border-sky-100 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                placeholder="debjit"
                autoComplete="username"
              />
            </div>

            {isRegister && (
              <div>
                <label className="mb-2 block text-sm font-medium text-zinc-700">Email</label>
                <input
                  name="email"
                  type="email"
                  value={form.email}
                  onChange={onChange}
                  className="w-full rounded-2xl border border-sky-100 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                  placeholder="you@example.com"
                  autoComplete="email"
                />
              </div>
            )}

            <div>
              <label className="mb-2 block text-sm font-medium text-zinc-700">Password</label>
              <input
                name="password"
                type="password"
                value={form.password}
                onChange={onChange}
                className="w-full rounded-2xl border border-sky-100 bg-white/80 px-4 py-3 text-zinc-950 outline-none transition duration-300 focus:border-blue-400 focus:ring-4 focus:ring-blue-100"
                placeholder="At least 8 characters"
                autoComplete={isRegister ? "new-password" : "current-password"}
              />
            </div>

            {error && (
              <p className="rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="rounded-full bg-zinc-950 px-6 py-3 text-sm font-semibold text-white shadow-xl shadow-zinc-950/20 transition duration-300 hover:-translate-y-0.5 hover:bg-black disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Please wait..." : isRegister ? "Create Account" : "Login"}
            </button>

            <p className="text-center text-sm text-zinc-500">
              {isRegister ? "Already registered?" : "New here?"}{" "}
              <Link
                to={isRegister ? "/login" : "/register"}
                className="font-semibold text-blue-600 hover:text-blue-700"
              >
                {isRegister ? "Login" : "Create an account"}
              </Link>
            </p>
          </div>
        </form>
      </section>
    </main>
  );
}

export default AuthPage;
