import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import PaperTexture from "../components/PaperTexture";

export default function NotFoundPage() {
  return (
    <div className="relative flex min-h-[80vh] flex-col items-center justify-center px-6 text-center">
      <PaperTexture />
      <p className="font-mono text-8xl font-bold text-ink/10 sm:text-9xl">404</p>
      <h1 className="mt-2 font-serif text-4xl font-semibold text-ink sm:text-5xl">This page didn't file.</h1>
      <p className="mt-4 max-w-sm text-sm text-ink-2">The document you're looking for isn't in the record.</p>
      <Link
        to="/"
        className="mt-8 flex items-center gap-2 border-b-2 border-ink pb-1 font-mono text-xs font-bold tracking-widest text-ink uppercase hover:border-highlight"
      >
        <ArrowLeft size={14} /> Return to Finora
      </Link>
    </div>
  );
}
