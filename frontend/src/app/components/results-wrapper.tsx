import { ResultsPage } from "./results-page";
import { BatchDetailPage as BatchDetail } from "./batch-detail-page";

export function AnalysisResultsPage() {
  return <ResultsPage />;
}

export function SavedReportPage() {
  return <ResultsPage saved />;
}

export function BatchReportPage() {
  return <BatchDetail />;
}
