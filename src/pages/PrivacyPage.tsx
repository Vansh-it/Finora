import LegalPage from "./LegalPage";

const ARTICLES = [
  {
    id: "overview",
    title: "Overview",
    body: [
      "This Privacy Policy explains how Finora Labs collects, uses, and safeguards information when you use the Finora research platform.",
    ],
  },
  {
    id: "information",
    title: "Information We Collect",
    body: [
      "Account information such as name and email address, research activity such as companies you research or chat queries you submit, and standard device/usage analytics.",
    ],
  },
  {
    id: "use",
    title: "How We Use Information",
    body: [
      "We use collected information to operate and improve the research platform, personalize your dashboard, maintain security, and communicate important product updates.",
      "We do not sell your personal information to third parties.",
    ],
  },
  {
    id: "retention",
    title: "Data Retention",
    body: ["Research files and chat history are retained for as long as your account remains active, or as required by law."],
  },
];

export default function PrivacyPage() {
  return <LegalPage title="Privacy Policy" updated="February 2026" articles={ARTICLES} />;
}
