import React from "react";
import { NavLink } from "react-router-dom";
import { getAuthToken, logoutUser } from "../api";

function NavBar(){
    const [isLoggedIn, setIsLoggedIn] = React.useState(Boolean(getAuthToken()));
    const navItems = [
        { label: "Home", path: "/" },
        { label: "Services", path: "/services" },
        { label: "Deployment", path: "/deployment-guide" },
        { label: "Contact", path: "/contact" },
    ];

    const onLogout = async () => {
        await logoutUser();
        setIsLoggedIn(false);
        window.location.href = "/login";
    };

    React.useEffect(() => {
        const syncAuth = () => setIsLoggedIn(Boolean(getAuthToken()));
        window.addEventListener("aiops-auth-changed", syncAuth);
        return () => window.removeEventListener("aiops-auth-changed", syncAuth);
    }, []);

    return (
        <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4">
            <nav className="mx-auto flex max-w-6xl items-center justify-between rounded-full border border-sky-100/80 bg-sky-50/75 px-4 py-3 shadow-[0_18px_60px_rgba(15,23,42,0.12)] backdrop-blur-2xl transition-all duration-300">
                <a href="/" className="group flex items-center gap-3">
                    <span className="grid h-9 w-9 place-items-center rounded-full bg-zinc-950 text-sm font-semibold text-white shadow-lg shadow-zinc-950/20 transition-transform duration-300 group-hover:scale-105">
                        AI
                    </span>
                    <span className="hidden text-sm font-semibold tracking-tight text-zinc-950 sm:block">
                        AIOps
                    </span>
                </a>
            <ul className="flex items-center gap-1 rounded-full bg-slate-200/65 p-1">
                {navItems.map((item) => {
                    return (
                        <li key={item.path}>
                            <NavLink
                                to={item.path}
                                className={({ isActive }) =>
                                    `rounded-full px-3 py-2 text-xs font-medium transition-all duration-300 sm:px-4 sm:text-sm ${
                                        isActive
                                            ? "bg-white/90 text-zinc-950 shadow-sm"
                                            : "text-slate-600 hover:bg-white/70 hover:text-zinc-950"
                                    }`
                                }
                            >
                                {item.label}
                            </NavLink>
                        </li>
                    );
                })}
                <li>
                    {isLoggedIn ? (
                        <button
                            type="button"
                            onClick={onLogout}
                            className="rounded-full px-3 py-2 text-xs font-medium text-slate-600 transition-all duration-300 hover:bg-white/70 hover:text-zinc-950 sm:px-4 sm:text-sm"
                        >
                            Logout
                        </button>
                    ) : (
                        <NavLink
                            to="/login"
                            className={({ isActive }) =>
                                `rounded-full px-3 py-2 text-xs font-medium transition-all duration-300 sm:px-4 sm:text-sm ${
                                    isActive
                                        ? "bg-white/90 text-zinc-950 shadow-sm"
                                        : "text-slate-600 hover:bg-white/70 hover:text-zinc-950"
                                }`
                            }
                        >
                            Login
                        </NavLink>
                    )}
                </li>
            </ul>
            </nav>
        </header>
    );
}

export default NavBar;
