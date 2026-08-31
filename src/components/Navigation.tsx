import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { Search, User, Menu, X, LogOut } from "lucide-react";
import { cn } from "../utils/cn";
import { getUser, isAuthenticated, removeToken } from "../lib/auth";

const LINKS = [
  { label: "Research", to: "/research" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "Chat", to: "/chat" },
  { label: "Methodology", to: "/methodology" },
];

export default function Navigation() {
  const location = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const user = getUser();
  const loggedIn = isAuthenticated();

  function handleLogout() {
    removeToken();
    navigate("/");
  }

  return (
    <header className="sticky top-0 z-50 border-b border-ink/15 bg-paper/95 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-[1440px] items-center justify-between px-4 sm:px-6 lg:px-10">
        <Link to="/" className="flex items-center gap-2 font-serif text-2xl font-semibold tracking-tight text-ink">
          <span className="inline-block h-3 w-3 bg-highlight" aria-hidden />
          Finora
        </Link>

        <nav className="hidden items-center gap-8 lg:flex">
          {LINKS.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={cn(
                "font-mono text-xs font-semibold tracking-[0.15em] uppercase text-ink-2 transition-colors hover:text-ink",
                location.pathname.startsWith(link.to) && "text-ink border-b-2 border-highlight pb-1"
              )}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <div className="hidden items-center gap-4 lg:flex">
          <button aria-label="Search" className="text-ink-2 transition-colors hover:text-ink">
            <Search size={18} />
          </button>
          {loggedIn ? (
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-semibold text-ink-2">
                {user?.name || user?.email}
              </span>
              <button
                onClick={handleLogout}
                aria-label="Sign out"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-ink/50 text-ink-2 transition-colors hover:border-ink hover:text-ink"
              >
                <LogOut size={15} />
              </button>
            </div>
          ) : (
            <Link
              to="/auth"
              aria-label="Account"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-ink/50 text-ink-2 transition-colors hover:border-ink hover:text-ink"
            >
              <User size={15} />
            </Link>
          )}
        </div>

        <button className="text-ink lg:hidden" onClick={() => setOpen(!open)} aria-label="Toggle menu">
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {open && (
        <div className="border-t border-ink/15 bg-paper px-4 py-4 lg:hidden">
          <nav className="flex flex-col gap-4">
            {LINKS.map((link) => (
              <Link
                key={link.to}
                to={link.to}
                onClick={() => setOpen(false)}
                className="font-mono text-sm font-semibold tracking-[0.1em] uppercase text-ink-2"
              >
                {link.label}
              </Link>
            ))}
            {loggedIn ? (
              <>
                <span className="font-mono text-sm font-semibold tracking-[0.1em] uppercase text-ink-2">
                  {user?.name || user?.email}
                </span>
                <button
                  onClick={() => { handleLogout(); setOpen(false); }}
                  className="text-left font-mono text-sm font-semibold tracking-[0.1em] uppercase text-ink-2"
                >
                  Sign Out
                </button>
              </>
            ) : (
              <Link to="/auth" onClick={() => setOpen(false)} className="font-mono text-sm font-semibold tracking-[0.1em] uppercase text-ink-2">
                Account
              </Link>
            )}
          </nav>
        </div>
      )}
    </header>
  );
}
