import { createBrowserRouter } from "react-router";
import { Layout } from "./components/layout";
import { UploadPage } from "./components/upload-page";
import { AnalysisResultsPage, SavedReportPage, BatchReportPage } from "./components/results-wrapper";
import { HistoryPage } from "./components/history-page";
import { BatchPage } from "./components/batch-page";
import { ComparePage } from "./components/compare-page";
import { PluginsPage } from "./components/plugins-page";
import { TrainingPage } from "./components/training-page";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: UploadPage },
      { path: "batch", Component: BatchPage },
      { path: "compare", Component: ComparePage },
      { path: "results/:id", Component: AnalysisResultsPage },
      { path: "report/:id", Component: SavedReportPage },
      { path: "batch-report/:batchId", Component: BatchReportPage },
      { path: "history", Component: HistoryPage },
      { path: "plugins", Component: PluginsPage },
      { path: "training", Component: TrainingPage },
    ],
  },
]);
