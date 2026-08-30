import { useState } from 'react';
import { useAuth } from '../../lib/auth';

interface AuthFormProps {
  mode: 'signin' | 'signup';
}

export default function AuthForm({ mode: initialMode }: AuthFormProps) {
  const [mode, setMode] = useState(initialMode);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signUp, signIn } = useAuth();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'signup') {
        await signUp(email, password, name);
      } else {
        await signIn(email, password);
      }
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message || 'Something went wrong');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-[85vh] grid-cols-1 lg:grid-cols-2">
      {/* LEFT — editorial brand panel */}
      <div className="relative hidden overflow-hidden border-r border-ink/15 bg-paper-2 lg:block">
        <div aria-hidden className="pointer-events-none absolute inset-0 opacity-[0.05] mix-blend-multiply" style={{ backgroundImage: 'url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'160\' height=\'160\'%3E%3Cfilter id=\'n\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.85\' numOctaves=\'2\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23n)\'/%3E%3C/svg%3E")' }} />
        <div className="relative flex h-full flex-col justify-between p-12">
          <a href="/" className="flex items-center gap-2 font-serif text-2xl font-semibold tracking-tight text-ink">
            <span className="inline-block h-3 w-3 bg-highlight" />
            Finora.
          </a>

          <div>
            <h1 className="font-serif text-5xl leading-[1.05] font-medium text-ink">
              Research the company.
              <br />
              <span className="mark-highlight">Verify the numbers.</span>
            </h1>
            <p className="mt-6 max-w-sm text-sm leading-relaxed text-ink-2">
              Every metric in Finora traces back to an SEC filing, a company disclosure, or a corroborating market source.
            </p>
          </div>

          <div className="relative h-40">
            <div className="absolute bottom-0 left-0 w-52 border border-ink/25 bg-paper p-4 shadow-[3px_3px_0_0_rgba(17,17,17,0.15)]" style={{ transform: 'rotate(-3deg)' }}>
              <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                <div className="font-semibold text-ink-2">Form 10-K</div>
                <div className="mt-0.5 text-ink-3">Annual Report</div>
              </div>
              <div className="mt-2 font-mono text-xs text-ink">Net income $93.7B</div>
            </div>
            <div className="absolute right-0 bottom-4 w-40 border border-ink/25 bg-paper p-4 shadow-[3px_3px_0_0_rgba(17,17,17,0.15)]" style={{ transform: 'rotate(2deg)' }}>
              <div className="font-mono text-[10px] leading-tight tracking-[0.18em] uppercase">
                <div className="font-semibold text-annotate-blue">Verified</div>
              </div>
              <div className="mt-2 font-mono text-xs text-ink">9 sources</div>
            </div>
          </div>
        </div>
      </div>

      {/* RIGHT — form */}
      <div className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex gap-6 border-b border-ink/15">
            <button
              onClick={() => { setMode('signin'); setError(''); }}
              className={`pb-3 font-mono text-xs font-bold tracking-widest uppercase transition-colors ${mode === 'signin' ? 'border-b-2 border-highlight text-ink' : 'text-ink-3 hover:text-ink'}`}
            >
              Sign In
            </button>
            <button
              onClick={() => { setMode('signup'); setError(''); }}
              className={`pb-3 font-mono text-xs font-bold tracking-widest uppercase transition-colors ${mode === 'signup' ? 'border-b-2 border-highlight text-ink' : 'text-ink-3 hover:text-ink'}`}
            >
              Sign Up
            </button>
          </div>

          <h2 className="font-serif text-3xl font-semibold text-ink">
            {mode === 'signin' ? 'Welcome back.' : 'Create your account.'}
          </h2>
          <p className="mt-2 text-sm text-ink-2">
            {mode === 'signin' ? 'Continue your research where you left off.' : 'Start building traceable research files.'}
          </p>

          {error && (
            <div className="mt-4 border border-annotate-red/20 bg-annotate-red/5 px-4 py-3">
              <p className="text-sm text-annotate-red">{error}</p>
            </div>
          )}

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            {mode === 'signup' && (
              <label className="block">
                <span className="font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">Full Name</span>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Jane Analyst"
                  className="mt-2 w-full border border-ink/30 bg-paper px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
                />
              </label>
            )}
            <label className="block">
              <span className="font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">Email</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane@firm.com"
                className="mt-2 w-full border border-ink/30 bg-paper px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
              />
            </label>
            <label className="block">
              <span className="font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">Password</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mt-2 w-full border border-ink/30 bg-paper px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
              />
              <span className="mt-1 block font-mono text-[10px] text-ink-3">Must be at least 8 characters</span>
            </label>

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-ink py-3.5 font-mono text-xs font-bold tracking-widest text-paper uppercase transition-colors hover:bg-ink-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? 'Please wait...' : mode === 'signin' ? 'Sign In' : 'Create Account'}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-ink-3">
            By continuing you agree to Finora's{' '}
            <a href="/terms" className="underline underline-offset-2 hover:text-ink">Terms</a> &{' '}
            <a href="/privacy" className="underline underline-offset-2 hover:text-ink">Privacy Policy</a>.
          </p>
        </div>
      </div>
    </div>
  );
}
