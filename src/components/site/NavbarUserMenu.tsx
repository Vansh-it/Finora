import { useState } from 'react';
import { useAuth } from '../../lib/auth';

export default function NavbarUserMenu() {
  const { user, signOut } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  if (!user) {
    return (
      <div className="flex items-center gap-2">
        <a
          href="/signin"
          className="inline-flex h-7 items-center rounded-sm px-3 text-button-md text-body transition-colors hover:text-ink"
        >
          Sign in
        </a>
        <a
          href="/signup"
          className="inline-flex h-7 items-center rounded-sm bg-ink px-3 text-button-md text-canvas transition-opacity hover:opacity-90"
        >
          Sign up
        </a>
      </div>
    );
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setMenuOpen(!menuOpen)}
        className="inline-flex h-7 items-center gap-1.5 rounded-sm bg-canvas-soft-2 px-3 text-button-md text-ink transition-colors hover:bg-canvas-soft"
      >
        <span className="h-4 w-4 rounded-full bg-accent text-[10px] font-bold text-canvas flex items-center justify-center">
          {user.name?.charAt(0)?.toUpperCase() || user.email.charAt(0).toUpperCase()}
        </span>
        {user.name || user.email.split('@')[0]}
      </button>

      {menuOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setMenuOpen(false)}
          />
          <div className="absolute right-0 top-full z-50 mt-1 w-56 rounded-lg border border-hairline bg-canvas p-2 shadow-l4">
            <div className="px-3 py-2 border-b border-hairline mb-1">
              <p className="text-body-sm-strong text-ink truncate">{user.name || 'User'}</p>
              <p className="text-caption text-mute truncate">{user.email}</p>
            </div>
            <a
              href="/chat"
              className="block rounded-md px-3 py-2 text-body-sm text-body transition-colors hover:bg-canvas-soft-2 hover:text-ink"
              onClick={() => setMenuOpen(false)}
            >
              Open Chat
            </a>
            <div className="border-t border-hairline mt-1 pt-1">
              <button
                type="button"
                onClick={async () => {
                  setMenuOpen(false);
                  await signOut();
                  window.location.href = '/';
                }}
                className="w-full rounded-md px-3 py-2 text-left text-body-sm text-body transition-colors hover:bg-canvas-soft-2 hover:text-ink"
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
