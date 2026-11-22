import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ToastProvider } from "./components/ui";
import { AppProvider } from "./state/app";
import { ThemeProvider } from "./state/theme";
import { Overview } from "./pages/Overview";
import { Projects } from "./pages/Projects";
import { DependencyGraph } from "./pages/DependencyGraph";
import { Explorer } from "./pages/Explorer";
import { Security } from "./pages/Security";
import { Updates } from "./pages/Updates";
import { Licenses } from "./pages/Licenses";
import { Usage } from "./pages/Usage";
import { Impact } from "./pages/Impact";
import { Decisions } from "./pages/Decisions";
import { Reports } from "./pages/Reports";
import { ScanHistory } from "./pages/ScanHistory";
import { Settings } from "./pages/Settings";

export function App() {
  return (
    <ThemeProvider>
      <ToastProvider>
        <AppProvider>
          <BrowserRouter>
            <Routes>
              <Route element={<Layout />}>
                <Route index element={<Overview />} />
                <Route path="projects" element={<Projects />} />
                <Route path="graph" element={<DependencyGraph />} />
                <Route path="explorer" element={<Explorer />} />
                <Route path="security" element={<Security />} />
                <Route path="updates" element={<Updates />} />
                <Route path="licenses" element={<Licenses />} />
                <Route path="usage" element={<Usage />} />
                <Route path="impact" element={<Impact />} />
                <Route path="decisions" element={<Decisions />} />
                <Route path="reports" element={<Reports />} />
                <Route path="history" element={<ScanHistory />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AppProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}
