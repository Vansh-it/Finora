import { useState } from 'react';
import { useAuth } from '../../lib/auth';

export default function SignInForm() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setError('');
    setLoading(true);
    try {
      await signIn(email.trim(), password);
      window.location.href = '/';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign in failed');
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      {error && (
        <div className="rounded-sm border border-error/20 bg-error-soft p-4">
          <p className="text-body-sm text-error">{error}</p>
        </div>
      )}

      <div>
        <label htmlFor="signin-email" className="text-body-sm-strong text-ink">
          Email
        </label>
        <input
          id="signin-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          required
          autoComplete="email"
          className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink placeholder:text-mute focus:border-hairline-strong"
        />
      </div>

      <div>
        <label htmlFor="signin-password" className="text-body-sm-strong text-ink">
          Password
        </label>
        <input
          id="signin-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Your password"
          required
          autoComplete="current-password"
          className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink placeholder:text-mute focus:border-hairline-strong"
        />
      </div>

      <button
        type="submit"
        disabled={loading || !email.trim() || !password}
        className="h-12 w-full rounded-pill bg-ink text-button-lg text-canvas transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? 'Signing in…' : 'Sign In'}
      </button>
    </form>
  );
}
