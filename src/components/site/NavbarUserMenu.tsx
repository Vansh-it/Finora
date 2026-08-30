import { useState } from 'react';
import { useAuth } from '../../lib/auth';
import { User } from 'lucide-react';

export default function NavbarUserMenu() {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) {
    return (
      <div className="hidden items-center gap-4 lg:flex">
        <a
          href="/signin"
          className="font-mono text-xs font-semibold tracking-[0.15em] uppercase text-ink-2 transition-colors hover:text-ink"
        >
          Sign in
        </a>
        <a
          href="/signup"
          className="inline-flex h-8 items-center justify-center rounded-full border border-ink/50 px-4 font-mono text-xs font-bold tracking-wider text-ink transition-colors hover:border-ink hover:bg-ink hover:text-paper"
        >
          Sign up
        </a>
      </div>
    );
  }

  return (
    <div className="relative hidden lg:block">
      <button
        type="button"
        onClick={() => setMenuOpen(!menuOpen)}
        className="flex h-8 w-8 items-center justify-center rounded-full border border-ink/50 text-ink-2 transition-colors hover:border-ink hover:text-ink"
      >
        <User size={15} />
      </button>

      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setMenuOpen(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-2 w-56 border border-ink bg-paper p-3 shadow-[3px_3px_0_0_rgba(17,17,17,0.15)]">
            <div className="border-b border-ink/15 pb-2 mb-2">
              <p className="font-mono text-xs font-bold tracking-wider text-ink">{user.name || 'User'}</p>
              <p className="font-mono text-[10px] tracking-wider text-ink-3">{user.email}</p>
            </div>
            <a
              href="/chat"
              className="block px-3 py-2 font-mono text-xs font-semibold tracking-wider text-ink-2 transition-colors hover:bg-paper-2 hover:text-ink"
              onClick={() => setMenuOpen(false)}
            >
              Open Chat
            </a>
            <div className="border-t border-ink/15 mt-2 pt-2">
              <button
                type="button"
                onClick={async () => {
                  setMenuOpen(false);
                  await signOut();
                  window.location.href = '/';
                }}
                className="w-full px-3 py-2 text-left font-mono text-xs font-semibold tracking-wider text-ink-2 transition-colors hover:bg-paper-2 hover:text-ink"
              >
                Sign out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
