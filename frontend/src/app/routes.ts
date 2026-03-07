import { createBrowserRouter } from "react-router";
import { Layout } from "./components/layout";
import { UploadPage } from "./components/upload-page";
import { AnalysisResultsPage, SavedReportPage } from "./components/results-wrapper";
import { HistoryPage } from "./components/history-page";

export const router = createBrowserRouter([
  {
    path: "/",
    Component: Layout,
    children: [
      { index: true, Component: UploadPage },
      { path: "results/:id", Component: AnalysisResultsPage },
      { path: "report/:id", Component: SavedReportPage },
      { path: "history", Component: HistoryPage },
    ],
  },
]);
