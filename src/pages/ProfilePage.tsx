import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import EditorialHeading from "../components/EditorialHeading";
import HighlightText from "../components/HighlightText";
import PaperTexture from "../components/PaperTexture";
import { getToken, removeToken } from "../lib/auth";

interface ProfileData {
  user: {
    user_id: string;
    email: string;
    name: string;
    research_runs_used: number;
    research_runs_limit: number;
  };
  completed_researches: number;
  usage: {
    used: number;
    limit: number;
    remaining: number;
  };
}

interface ResearchEntry {
  session_id: string;
  company: string;
  ticker: string;
  period: string;
  created_at: string;
  headline: string;
  status: string;
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [researches, setResearches] = useState<ResearchEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [nameValue, setNameValue] = useState("");
  const [companyValue, setCompanyValue] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      navigate("/auth", { state: { from: "/profile" } });
      return;
    }

    fetch("/api/auth/profile", { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => {
        if (res.status === 401 || res.status === 403) {
          removeToken();
          navigate("/auth", { state: { from: "/profile" } });
          return null;
        }
        return res.json();
      })
      .then((profileData) => {
        if (!profileData) return;
        setProfile(profileData);
        setNameValue(profileData.user?.name || "");
        setCompanyValue((profileData.user as Record<string, unknown>)?.company as string || "");

        // Fetch history separately
        return fetch("/api/research/history", { headers: { Authorization: `Bearer ${token}` } })
          .then((r) => (r.ok ? r.json() : { researches: [] }))
          .then((historyData) => {
            setResearches((historyData.researches || []).slice(0, 3));
            setLoading(false);
          });
      })
      .catch(() => setLoading(false));
  }, [navigate]);

  async function handleSave() {
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      await fetch("/api/auth/update-profile", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ name: nameValue, company: companyValue }),
      });
      if (profile) {
        setProfile({
          ...profile,
          user: { ...profile.user, name: nameValue },
        });
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  function handleSignOut() {
    const token = getToken();
    if (token) {
      fetch("/api/auth/signout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {});
    }
    removeToken();
    navigate("/");
  }

  function formatDate(iso: string): string {
    try {
      return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
    } catch {
      return "";
    }
  }

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[60vh] max-w-3xl items-center justify-center px-4">
        <div className="text-center">
          <div className="inline-block h-6 w-6 animate-spin border-2 border-ink border-t-transparent" />
          <p className="mt-4 font-mono text-sm text-ink-3">Loading profile...</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-20 text-center">
        <p className="text-ink-2">Please sign in to view your profile.</p>
        <Link to="/auth" className="mt-4 inline-block border-2 border-ink bg-paper px-6 py-3 font-mono text-xs font-bold tracking-wider uppercase">
          Sign In
        </Link>
      </div>
    );
  }

  const user = profile.user;
  const usage = profile.usage;
  const usagePct = usage.limit > 0 ? (usage.used / usage.limit) * 100 : 0;

  return (
    <div>
      <section className="relative border-b border-ink/15">
        <PaperTexture />
        <div className="mx-auto max-w-3xl px-4 py-20 sm:px-6 lg:px-0">
          <p className="mb-4 font-mono text-xs font-semibold tracking-[0.3em] text-ink-3 uppercase">Profile</p>
          <EditorialHeading size="md">
            Your
            <br />
            <HighlightText>account.</HighlightText>
          </EditorialHeading>
        </div>
      </section>

      <section className="mx-auto max-w-3xl px-4 py-12 sm:px-6 lg:px-0">
        {/* Profile Info */}
        <div className="border border-ink/20 bg-paper p-6 sm:p-8">
          <div className="flex items-start justify-between">
            <h3 className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Profile</h3>
            {!editing && (
              <button
                onClick={() => setEditing(true)}
                className="font-mono text-xs font-semibold tracking-wider text-annotate-blue uppercase hover:text-ink"
              >
                Edit
              </button>
            )}
          </div>

          {editing ? (
            <div className="mt-6 space-y-4">
              <div>
                <label className="mb-1 block font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">Name</label>
                <input
                  value={nameValue}
                  onChange={(e) => setNameValue(e.target.value)}
                  className="w-full border border-ink/25 bg-paper px-4 py-3 font-mono text-sm text-ink focus:border-ink focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block font-mono text-[10px] font-semibold tracking-widest text-ink-3 uppercase">Company / Organization</label>
                <input
                  value={companyValue}
                  onChange={(e) => setCompanyValue(e.target.value)}
                  className="w-full border border-ink/25 bg-paper px-4 py-3 font-mono text-sm text-ink focus:border-ink focus:outline-none"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="border-2 border-ink bg-ink px-6 py-2 font-mono text-xs font-bold tracking-wider text-paper uppercase transition-colors hover:bg-ink-2 disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  onClick={() => setEditing(false)}
                  className="border-2 border-ink bg-paper px-6 py-2 font-mono text-xs font-bold tracking-wider text-ink uppercase transition-colors hover:bg-paper-2"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="mt-6 space-y-3 font-mono text-sm">
              <div className="flex justify-between border-b border-ink/10 py-2">
                <span className="text-ink-3">Name</span>
                <span className="font-semibold text-ink">{user.name || "—"}</span>
              </div>
              <div className="flex justify-between border-b border-ink/10 py-2">
                <span className="text-ink-3">Email</span>
                <span className="text-ink">{user.email}</span>
              </div>
              <div className="flex justify-between py-2">
                <span className="text-ink-3">Company</span>
                <span className="text-ink">{(user as Record<string, unknown>).company as string || "—"}</span>
              </div>
            </div>
          )}
        </div>

        {/* Research Usage */}
        <div className="mt-8 border border-ink/20 bg-paper p-6 sm:p-8">
          <h3 className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Research Usage</h3>
          <div className="mt-6">
            <div className="flex items-baseline justify-between">
              <span className="font-mono text-3xl font-bold text-ink">{usage.used}</span>
              <span className="font-mono text-sm text-ink-3">of {usage.limit} researches</span>
            </div>
            <div className="mt-3 h-1.5 bg-ink/10">
              <div className="h-full bg-ink transition-all duration-500" style={{ width: `${usagePct}%` }} />
            </div>
            <p className="mt-2 font-mono text-xs text-ink-3">{usage.remaining} remaining</p>
          </div>
        </div>

        {/* Recent Research */}
        {researches.length > 0 && (
          <div className="mt-8 border border-ink/20 bg-paper p-6 sm:p-8">
            <h3 className="font-mono text-xs font-semibold tracking-[0.2em] text-ink-3 uppercase">Recent Research</h3>
            <div className="mt-6 space-y-4">
              {researches.map((r) => (
                <button
                  key={r.session_id}
                  onClick={() => navigate(`/dashboard?session_id=${r.session_id}`)}
                  className="group flex w-full items-center justify-between border-b border-ink/10 py-3 text-left last:border-0"
                >
                  <div>
                    <span className="font-serif text-sm font-semibold text-ink">{r.company}</span>
                    {r.ticker && <span className="ml-2 font-mono text-xs text-ink-3">{r.ticker}</span>}
                    <p className="mt-0.5 font-mono text-[10px] text-ink-3">
                      {r.period && <>{r.period} · </>}
                      {formatDate(r.created_at)}
                    </p>
                  </div>
                  <ArrowRight size={14} className="text-ink-3 transition-colors group-hover:text-ink" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Sign Out */}
        <div className="mt-8">
          <button
            onClick={handleSignOut}
            className="w-full border-2 border-ink/25 bg-paper py-3 font-mono text-xs font-bold tracking-wider text-ink uppercase transition-colors hover:border-ink hover:bg-paper-2"
          >
            Sign Out
          </button>
        </div>
      </section>
    </div>
  );
}
