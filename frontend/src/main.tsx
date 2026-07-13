import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import { applyTheme, currentTheme } from "./themes";
import "./styles.css";

applyTheme(currentTheme());

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
