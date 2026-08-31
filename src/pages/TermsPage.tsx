import LegalPage from "./LegalPage";

const ARTICLES = [
  {
    id: "acceptance",
    title: "Acceptance of Terms",
    body: [
      "By accessing Finora, you agree to these Terms of Service. Finora is a research tool designed to help you understand publicly available financial information — it is not a licensed broker-dealer or investment adviser.",
      "If you do not agree with any part of these terms, please discontinue use of the platform.",
    ],
  },
  {
    id: "not-advice",
    title: "Not Investment Advice",
    body: [
      "All content produced by Finora — including metrics, charts, executive analysis, and AI-generated explanations — is provided for informational and educational purposes only.",
      "Nothing on Finora constitutes investment, legal, tax, or financial advice, and should not be relied upon as the sole basis for any investment decision.",
    ],
  },
  {
    id: "data-sources",
    title: "Data Sources & Accuracy",
    body: [
      "Finora derives figures from SEC EDGAR filings, official company disclosures, and third-party market data providers. While Finora cross-verifies figures where possible, errors, delays, or omissions in underlying source data may occur.",
      "Finora clearly labels any figure that could not be reliably verified as 'Data Unavailable' rather than presenting an estimate as fact.",
    ],
  },
  {
    id: "accounts",
    title: "Accounts & Usage",
    body: [
      "You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account.",
      "You agree not to misuse the platform, including attempting to reverse-engineer Finora's verification pipeline or redistribute research files without attribution.",
    ],
  },
  {
    id: "changes",
    title: "Changes to These Terms",
    body: ["Finora may update these Terms from time to time. Material changes will be communicated within the product."],
  },
];

export default function TermsPage() {
  return <LegalPage title="Terms of Service" updated="February 2026" articles={ARTICLES} />;
}
