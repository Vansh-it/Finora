import { useState } from "react";
import { Link } from "react-router-dom";
import Annotation from "../components/Annotation";
import DocumentCard from "../components/DocumentCard";
import HighlightText from "../components/HighlightText";
import PaperTexture from "../components/PaperTexture";

export default function AuthPage() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");

  return (
    <div className="grid min-h-[85vh] grid-cols-1 lg:grid-cols-2">
      {/* LEFT */}
      <div className="relative hidden overflow-hidden border-r border-ink/15 bg-paper-2 lg:block">
        <PaperTexture />
        <div className="relative flex h-full flex-col justify-between p-12">
          <Link to="/" className="flex items-center gap-2 font-serif text-2xl font-semibold tracking-tight text-ink">
            <span className="inline-block h-3 w-3 bg-highlight" />
            Finora.
          </Link>

          <div>
            <h1 className="font-serif text-5xl leading-[1.05] font-medium text-ink">
              Research the company.
              <br />
              <HighlightText>Verify the numbers.</HighlightText>
            </h1>
            <p className="mt-6 max-w-sm text-sm leading-relaxed text-ink-2">
              Every metric in Finora traces back to an SEC filing, a company disclosure, or a corroborating market
              source.
            </p>
          </div>

          <div className="relative h-40">
            <DocumentCard rotate={-3} className="absolute bottom-0 left-0 w-52">
              <Annotation label="Form 10-K" value="Annual Report" />
              <div className="mt-2 font-mono text-xs text-ink">Net income $93.7B</div>
            </DocumentCard>
            <DocumentCard rotate={2} className="absolute right-0 bottom-4 w-40">
              <Annotation label="Verified" tone="blue" />
              <div className="mt-2 font-mono text-xs text-ink">9 sources</div>
            </DocumentCard>
          </div>
        </div>
      </div>

      {/* RIGHT */}
      <div className="flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex gap-6 border-b border-ink/15">
            <button
              onClick={() => setMode("signin")}
              className={`pb-3 font-mono text-xs font-bold tracking-widest uppercase ${mode === "signin" ? "border-b-2 border-highlight text-ink" : "text-ink-3"}`}
            >
              Sign In
            </button>
            <button
              onClick={() => setMode("signup")}
              className={`pb-3 font-mono text-xs font-bold tracking-widest uppercase ${mode === "signup" ? "border-b-2 border-highlight text-ink" : "text-ink-3"}`}
            >
              Sign Up
            </button>
          </div>

          <h2 className="font-serif text-3xl font-semibold text-ink">
            {mode === "signin" ? "Welcome back." : "Create your account."}
          </h2>
          <p className="mt-2 text-sm text-ink-2">
            {mode === "signin" ? "Continue your research where you left off." : "Start building traceable research files."}
          </p>

          <form className="mt-8 space-y-5" onSubmit={(e) => e.preventDefault()}>
            {mode === "signup" && (
              <Field label="Full Name" type="text" placeholder="Jane Analyst" />
            )}
            <Field label="Email" type="email" placeholder="jane@firm.com" />
            <Field label="Password" type="password" placeholder="••••••••" />

            <button
              type="submit"
              className="w-full bg-ink py-3.5 font-mono text-xs font-bold tracking-widest text-paper uppercase transition-colors hover:bg-ink-2"
            >
              {mode === "signin" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <p className="mt-6 text-center text-xs text-ink-3">
            By continuing you agree to Finora's{" "}
            <Link to="/terms" className="underline underline-offset-2 hover:text-ink">Terms</Link> &{" "}
            <Link to="/privacy" className="underline underline-offset-2 hover:text-ink">Privacy Policy</Link>.
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, type, placeholder }: { label: string; type: string; placeholder: string }) {
  return (
    <label className="block">
      <span className="font-mono text-[10px] font-bold tracking-widest text-ink-3 uppercase">{label}</span>
      <input
        type={type}
        placeholder={placeholder}
        className="mt-2 w-full border border-ink/30 bg-paper px-4 py-3 text-sm text-ink placeholder:text-ink-3 focus:border-ink focus:outline-none"
      />
    </label>
  );
}
