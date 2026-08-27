import { useState } from 'react';

const suggestions = ['Microsoft', 'Nvidia', 'Apple', 'Tesla', 'Amazon', 'Alphabet'];

export default function ResearchForm() {
  const [company, setCompany] = useState('Microsoft');
  const [from, setFrom] = useState('2024');
  const [to, setTo] = useState('2025');
  const [objective, setObjective] = useState('Calculate key financial metrics and summarize performance.');

  const submit = () => {
    const params = new URLSearchParams({
      company: company.trim() || 'Microsoft',
      from,
      to,
      objective: objective.trim(),
    });
    window.location.href = `/permission?${params.toString()}`;
  };

  return (
    <form
      className="rounded-lg bg-canvas p-8 shadow-l3 md:p-10"
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <div className="space-y-6">
        <div>
          <label htmlFor="company" className="text-body-sm-strong text-ink">
            Company
          </label>
          <input
            id="company"
            name="company"
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Microsoft"
            autoComplete="off"
            spellCheck={false}
            className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink placeholder:text-mute focus:border-hairline-strong"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setCompany(s)}
                className={
                  'rounded-full border px-3 py-1 text-caption transition-colors ' +
                  (company === s
                    ? 'border-ink bg-ink text-canvas'
                    : 'border-hairline bg-canvas text-body hover:border-hairline-strong hover:text-ink')
                }
              >
                {s}
              </button>
            ))}
          </div>
        </div>

        <div className="grid gap-6 sm:grid-cols-2">
          <div>
            <label htmlFor="from" className="text-body-sm-strong text-ink">
              From fiscal year
            </label>
            <select
              id="from"
              name="from"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink focus:border-hairline-strong"
            >
              {['2020', '2021', '2022', '2023', '2024', '2025'].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="to" className="text-body-sm-strong text-ink">
              To fiscal year
            </label>
            <select
              id="to"
              name="to"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="mt-2 h-11 w-full rounded-sm border border-hairline bg-canvas px-3 text-body-md text-ink focus:border-hairline-strong"
            >
              {['2021', '2022', '2023', '2024', '2025'].map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="objective" className="text-body-sm-strong text-ink">
            Research objective
          </label>
          <textarea
            id="objective"
            name="objective"
            rows={4}
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            className="mt-2 w-full resize-none rounded-sm border border-hairline bg-canvas p-3 text-body-md text-ink placeholder:text-mute focus:border-hairline-strong"
          />
          <p className="mt-2 text-caption text-mute">
            Describe what you want to know — metrics, period, or focus areas. Dummy interaction for this phase.
          </p>
        </div>

        <button
          type="submit"
          className="h-12 w-full rounded-pill bg-ink text-button-lg text-canvas transition-opacity hover:opacity-90"
        >
          Analyze Company
        </button>
      </div>
    </form>
  );
}
