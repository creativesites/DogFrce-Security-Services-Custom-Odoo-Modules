import React from "react";
import ReactDOM from "react-dom/client";
import { Toolbar } from "./shell/Toolbar";
import { SessionProviderRoot } from "./session/SessionContext";
import "./styles/ds.css";
import "./styles/dgs.css";
import "./styles/shell.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <SessionProviderRoot>
      <Toolbar />
    </SessionProviderRoot>
  </React.StrictMode>,
);
