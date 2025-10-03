import { ApiClient } from "./api.js";
import { Router } from "./router.js";
import { renderNav } from "./components/Nav.js";
import { renderListView } from "./components/ListView.js";
import { renderFormView } from "./components/FormView.js";

/**
 * Application state singleton. Holds config, router, and api client.
 */
export const AppState = {
  config: null,
  apiClient: null,
  router: null,
  resourcesByName: new Map(),
};

function setStatus(message) {
  const statusEl = document.getElementById("status");
  if (statusEl) statusEl.textContent = message;
}

async function loadConfig() {
  const response = await fetch("./config.json", { cache: "no-store" });
  if (!response.ok) throw new Error(`Failed to load config.json: ${response.status}`);
  /** @type {import('./types').RuntimeConfig} */
  const config = await response.json();
  return config;
}

function setupAuthControls(config, apiClient) {
  const container = document.getElementById("auth-controls");
  if (!container) return;

  container.innerHTML = "";

  if (!config.auth || config.auth.type !== "bearer") return;

  const label = document.createElement("label");
  label.textContent = "Bearer Token";
  label.setAttribute("for", "token-input");
  label.style.marginRight = "8px";

  const input = document.createElement("input");
  input.id = "token-input";
  input.className = "token-input";
  input.type = "text";
  input.placeholder = "Paste token…";
  input.value = localStorage.getItem(config.auth.localStorageKey || "data_admin_token") || "";

  const saveBtn = document.createElement("button");
  saveBtn.className = "btn";
  saveBtn.textContent = "Save";

  const clearBtn = document.createElement("button");
  clearBtn.className = "btn danger";
  clearBtn.textContent = "Clear";

  saveBtn.addEventListener("click", () => {
    const key = config.auth.localStorageKey || "data_admin_token";
    localStorage.setItem(key, input.value.trim());
    apiClient.setBearerToken(input.value.trim());
    setStatus("Token saved");
  });

  clearBtn.addEventListener("click", () => {
    const key = config.auth.localStorageKey || "data_admin_token";
    localStorage.removeItem(key);
    input.value = "";
    apiClient.setBearerToken("");
    setStatus("Token cleared");
  });

  container.append(label, input, saveBtn, clearBtn);
}

function mountApp() {
  const app = document.getElementById("app");
  if (!app) throw new Error("Missing #app container");
}

function indexResources(config) {
  AppState.resourcesByName.clear();
  for (const resource of config.resources) {
    AppState.resourcesByName.set(resource.name, resource);
  }
}

function getDefaultResourceName() {
  const first = AppState.config?.resources?.[0]?.name;
  return first || null;
}

async function main() {
  try {
    setStatus("Loading config…");
    const config = await loadConfig();
    AppState.config = config;
    indexResources(config);

    const apiClient = new ApiClient({ baseUrl: config.baseUrl, auth: config.auth, queryParams: config.queryParams });
    const storedToken = localStorage.getItem(config?.auth?.localStorageKey || "data_admin_token");
    if (storedToken && config?.auth?.type === "bearer") apiClient.setBearerToken(storedToken);
    AppState.apiClient = apiClient;

    setupAuthControls(config, apiClient);

    const navEl = document.getElementById("nav");
    const detectedBase = new URL('.', import.meta.url).pathname.replace(/\/$/, '');
    const basePath = (config.spaBasePath !== undefined && config.spaBasePath !== null)
      ? (config.spaBasePath || '')
      : detectedBase;
    const router = new Router({ basePath });
    AppState.router = router;
    renderNav(navEl, config.resources);

    

    router.addRoute("/", () => {
      const defaultRes = getDefaultResourceName();
      if (defaultRes) {
        router.replace(`/r/${encodeURIComponent(defaultRes)}`);
      }
    });

    router.addRoute("/r/:resource", async ({ params, query }) => {
      const resource = AppState.resourcesByName.get(params.resource);
      if (!resource) return setStatus(`Unknown resource: ${params.resource}`);
      const mount = document.getElementById("app");
      await renderListView({ mount, resource, apiClient, config, query });
    });

    router.addRoute("/r/:resource/new", async ({ params }) => {
      const resource = AppState.resourcesByName.get(params.resource);
      if (!resource) return setStatus(`Unknown resource: ${params.resource}`);
      const mount = document.getElementById("app");
      await renderFormView({ mount, resource, apiClient, mode: "create" });
    });

    router.addRoute("/r/:resource/:id/edit", async ({ params }) => {
      const resource = AppState.resourcesByName.get(params.resource);
      if (!resource) return setStatus(`Unknown resource: ${params.resource}`);
      const mount = document.getElementById("app");
      await renderFormView({ mount, resource, apiClient, mode: "edit", id: params.id });
    });

    router.start();

    setStatus("Ready");
  } catch (err) {
    console.error(err);
    setStatus(`Error: ${err.message}`);
  }
}

mountApp();
main();

