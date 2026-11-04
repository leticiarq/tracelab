import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Lab } from "./types";

const platform = { id: 1, name: "Hack The Box", slug: "hack-the-box", website_url: "https://hackthebox.com", created_at: "2026-11-01T12:00:00Z" };
const category = { id: 1, name: "Web", slug: "web", platform_id: 1 };
const baseLab: Lab = { id: 1, title: "Cache Poisoning", slug: "cache-poisoning", platform_id: 1, category_id: 1, source_url: "https://example.com/lab", difficulty: "médio", status: "in_progress", notes: "GET / HTTP/1.1\nHost: target.local", objective: null, vulnerability_description: null, impact: null, mitigation: null, learnings: null, created_at: "2026-11-02T12:00:00Z", updated_at: "2026-11-03T12:00:00Z", solved_at: null };

function page<T>(items: T[]) { return { items, total: items.length, page: 1, page_size: 100, pages: items.length ? 1 : 0 }; }
function json(body: unknown, status = 200) { return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })); }

function installApi(initialLabs: Lab[] = [baseLab], failLabs = false) {
  const labs = initialLabs.map((lab) => ({ ...lab }));
  const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url);
    const method = init?.method || "GET";
    if (url.pathname === "/api/platforms" && method === "GET") return json(page([platform]));
    if (url.pathname === "/api/categories" && method === "GET") return json(page([category]));
    if (url.pathname === "/api/labs" && method === "GET") {
      if (failLabs) return json({ detail: "Database unavailable" }, 503);
      let filtered = [...labs];
      const search = url.searchParams.get("search")?.toLowerCase();
      const status = url.searchParams.get("status");
      const platformId = url.searchParams.get("platform_id");
      const categoryId = url.searchParams.get("category_id");
      if (search) filtered = filtered.filter((lab) => lab.title.toLowerCase().includes(search));
      if (status) filtered = filtered.filter((lab) => lab.status === status);
      if (platformId) filtered = filtered.filter((lab) => lab.platform_id === Number(platformId));
      if (categoryId) filtered = filtered.filter((lab) => lab.category_id === Number(categoryId));
      return json(page(filtered));
    }
    if (url.pathname === "/api/labs" && method === "POST") {
      const payload = JSON.parse(String(init?.body));
      const lab = { ...baseLab, ...payload, id: labs.length + 1, slug: payload.title.toLowerCase().replaceAll(" ", "-"), notes: "", created_at: new Date().toISOString(), updated_at: new Date().toISOString() };
      labs.unshift(lab); return json(lab, 201);
    }
    const match = url.pathname.match(/^\/api\/labs\/(\d+)$/);
    if (match) {
      const id = Number(match[1]); const index = labs.findIndex((lab) => lab.id === id);
      if (index < 0) return json({ detail: "Lab not found" }, 404);
      if (method === "GET") return json(labs[index]);
      if (method === "PATCH") { labs[index] = { ...labs[index], ...JSON.parse(String(init?.body)), updated_at: new Date().toISOString() }; return json(labs[index]); }
      if (method === "DELETE") { labs.splice(index, 1); return Promise.resolve(new Response(null, { status: 204 })); }
    }
    return json({ detail: "Not found" }, 404);
  });
  vi.stubGlobal("fetch", fetchMock);
  return { labs, fetchMock };
}

beforeEach(() => { window.history.replaceState({}, "", "/"); vi.stubGlobal("scrollTo", vi.fn()); });
afterEach(() => { vi.unstubAllGlobals(); });

describe("TraceLab", () => {
  it("carrega o dashboard com métricas e laboratórios recentes", async () => {
    installApi(); render(<App />);
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(await screen.findByText("Cache Poisoning")).toBeInTheDocument();
    expect(screen.getByText("Total de laboratórios").parentElement).toHaveTextContent("1");
  });

  it("cadastra e edita um laboratório usando a API", async () => {
    const api = installApi([]); window.history.replaceState({}, "", "/labs/new"); render(<App />);
    fireEvent.change(await screen.findByLabelText(/Título/), { target: { value: "JWT attacks" } });
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "in_progress" } });
    fireEvent.click(screen.getByRole("button", { name: "Criar laboratório" }));
    expect(await screen.findByRole("heading", { name: "JWT attacks" })).toBeInTheDocument();
    expect(api.labs).toHaveLength(1);
    fireEvent.click(screen.getByRole("button", { name: "Editar" }));
    const title = await screen.findByLabelText(/Título/);
    fireEvent.change(title, { target: { value: "JWT authentication attacks" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByRole("heading", { name: "JWT authentication attacks" })).toBeInTheDocument();
    expect(api.labs[0].title).toBe("JWT authentication attacks");
  });

  it("lista, busca e filtra laboratórios", async () => {
    installApi([baseLab, { ...baseLab, id: 2, title: "Linux PrivEsc", status: "solved" }]); window.history.replaceState({}, "", "/labs"); render(<App />);
    expect(await screen.findByText("Linux PrivEsc")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar por título"), { target: { value: "cache" } });
    await waitFor(() => expect(screen.queryByText("Linux PrivEsc")).not.toBeInTheDocument());
    expect(screen.getByText("Cache Poisoning")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Buscar por título"), { target: { value: "" } });
    fireEvent.change(screen.getByLabelText("Filtrar por status"), { target: { value: "solved" } });
    expect(await screen.findByText("Linux PrivEsc")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Cache Poisoning")).not.toBeInTheDocument());
  });

  it("exclui após confirmação explícita", async () => {
    const api = installApi(); window.history.replaceState({}, "", "/labs"); render(<App />);
    fireEvent.click(await screen.findByRole("button", { name: "Excluir Cache Poisoning" }));
    expect(screen.getByRole("alertdialog")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Excluir laboratório" }));
    expect(await screen.findByText("Laboratório excluído com sucesso.")).toBeInTheDocument();
    expect(api.labs).toHaveLength(0);
  });

  it("salva e recupera anotações preservando texto livre", async () => {
    const api = installApi(); window.history.replaceState({}, "", "/labs/1"); const view = render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Anotações" }));
    const editor = screen.getByLabelText("Anotações do laboratório");
    const content = "POST /login HTTP/1.1\n\ncurl -i https://target.local\n# observação pessoal";
    fireEvent.change(editor, { target: { value: content } });
    expect(screen.getByText("Alterações não salvas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar anotações" }));
    await waitFor(() => expect(api.labs[0].notes).toBe(content));
    view.unmount(); render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Anotações" }));
    expect(screen.getByLabelText("Anotações do laboratório")).toHaveValue(content);
  });

  it("apresenta estado de erro da API com opção de tentar novamente", async () => {
    installApi([], true); window.history.replaceState({}, "", "/labs"); render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});
