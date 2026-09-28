import React from "react";
import ReactDOM from "react-dom/client";
import { getVersion } from "@tauri-apps/api/app";
import { AppShell } from "./app/AppShell";
import { ViewModeProvider } from "./app/viewMode";
import { SessionProviderRoot } from "./session/SessionContext";
import { ConnectivityProvider } from "./lib/connectivity";
import { setDiagnosticsAppVersion } from "./lib/errorCollector";
import "./styles/ds.css";
import "./styles/dgs.css";
import "./styles/shell.css";
import "./styles/components.css";

getVersion().then(setDiagnosticsAppVersion).catch(() => {});

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <SessionProviderRoot>
      <ConnectivityProvider>
        <ViewModeProvider>
          <AppShell />
        </ViewModeProvider>
      </ConnectivityProvider>
    </SessionProviderRoot>
  </React.StrictMode>,
);
