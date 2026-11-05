import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { Evidence, Lab, Report } from "./types";
import { SafeMarkdown } from "./pages/ReportTab";

const platform = { id: 1, name: "Hack The Box", slug: "hack-the-box", website_url: "https://hackthebox.com", created_at: "2026-11-01T12:00:00Z" };
const category = { id: 1, name: "Web", slug: "web", platform_id: 1 };
const baseLab: Lab = { id: 1, title: "Cache Poisoning", slug: "cache-poisoning", platform_id: 1, category_id: 1, source_url: "https://example.com/lab", difficulty: "médio", status: "in_progress", notes: "GET / HTTP/1.1\nHost: target.local", objective: null, vulnerability_description: null, impact: null, mitigation: null, learnings: null, resolution_steps: null, created_at: "2026-11-02T12:00:00Z", updated_at: "2026-11-03T12:00:00Z", solved_at: null };

function page<T>(items: T[]) { return { items, total: items.length, page: 1, page_size: 100, pages: items.length ? 1 : 0 }; }
function json(body: unknown, status = 200) { return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } })); }

function installApi(initialLabs: Lab[] = [baseLab], failLabs = false) {
  const labs = initialLabs.map((lab) => ({ ...lab }));
  const evidences: Evidence[] = [];
  let report: Report | null = null;
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
    const reportRoute = url.pathname.match(/^\/api\/labs\/(\d+)\/report$/);
    if (reportRoute) {
      const labId = Number(reportRoute[1]);
      if (method === "GET") return json(report);
      if (method === "PUT") { const markdown = JSON.parse(String(init?.body)).markdown; report = { ...(report as Report), markdown, revision: (report?.revision || 0) + 1, updated_at: new Date().toISOString() }; return json(report); }
    }
    const generateRoute = url.pathname.match(/^\/api\/labs\/(\d+)\/report\/generate$/);
    if (generateRoute && method === "POST") {
      const labId = Number(generateRoute[1]); const lab = labs.find((item) => item.id === labId)!;
      const markdown = `# ${lab.title}\n\n## 1. Informações gerais\n\n- Plataforma: Hack The Box\n\n${lab.objective ? `## 2. Objetivo\n\n${lab.objective}\n\n` : ""}## 4. Metodologia e resolução\n\n${lab.notes}\n`;
      report = { id: 1, lab_id: labId, markdown, revision: 1, generated_at: new Date().toISOString(), updated_at: new Date().toISOString(), incomplete_fields: [], sensitive_warnings: [] };
      return json(report);
    }
    const evidenceCollection = url.pathname.match(/^\/api\/labs\/(\d+)\/evidences$/);
    if (evidenceCollection) {
      const labId = Number(evidenceCollection[1]);
      if (method === "GET") return json(evidences.filter((item) => item.lab_id === labId).sort((a, b) => a.display_order - b.display_order));
      if (method === "POST") {
        const files = Array.from((init?.body as FormData).getAll("files")) as File[];
        const created = files.map((file, index): Evidence => ({ id: evidences.length + index + 1, lab_id: labId, original_filename: file.name, stored_filename: `${crypto.randomUUID()}.png`, mime_type: file.type || "image/png", file_size: file.size, sha256: "a".repeat(64), description: file.name.replace(/\.[^.]+$/, ""), step_label: null, display_order: evidences.length + index, created_at: new Date().toISOString() }));
        evidences.push(...created); return json(created, 201);
      }
    }
    const evidenceOrder = url.pathname.match(/^\/api\/labs\/(\d+)\/evidences\/order$/);
    if (evidenceOrder && method === "PATCH") {
      const ids = JSON.parse(String(init?.body)).evidence_ids as number[];
      ids.forEach((id, displayOrder) => { const item = evidences.find((evidence) => evidence.id === id); if (item) item.display_order = displayOrder; });
      return json(ids.map((id) => evidences.find((item) => item.id === id)));
    }
    const evidenceItem = url.pathname.match(/^\/api\/labs\/(\d+)\/evidences\/(\d+)$/);
    if (evidenceItem) {
      const id = Number(evidenceItem[2]); const index = evidences.findIndex((item) => item.id === id);
      if (index < 0) return json({ detail: "Evidence not found" }, 404);
      if (method === "PATCH") { evidences[index] = { ...evidences[index], ...JSON.parse(String(init?.body)) }; return json(evidences[index]); }
      if (method === "DELETE") { evidences.splice(index, 1); evidences.forEach((item, order) => { item.display_order = order; }); return Promise.resolve(new Response(null, { status: 204 })); }
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
  return { labs, evidences, fetchMock, get report() { return report; } };
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

  it("envia, descreve, associa, reordena e recupera três screenshots", async () => {
    const mock = installApi(); window.history.replaceState({}, "", "/labs/1"); const view = render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Evidências" }));
    const files = ["login.png", "exploit.png", "proof.png"].map((name) => new File([name], name, { type: "image/png" }));
    fireEvent.change(await screen.findByLabelText("Selecionar evidências"), { target: { files } });
    expect(await screen.findByText("3 evidências enviadas com sucesso.")).toBeInTheDocument();
    expect(mock.evidences).toHaveLength(3);

    fireEvent.change(screen.getByLabelText("Nome descritivo / legenda"), { target: { value: "Tela de autenticação" } });
    fireEvent.change(screen.getByLabelText("Etapa do laboratório"), { target: { value: "01 · Reconhecimento" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(mock.evidences[0].description).toBe("Tela de autenticação"));
    expect(mock.evidences[0].step_label).toBe("01 · Reconhecimento");

    fireEvent.click(screen.getByRole("button", { name: "Mover evidência para baixo" }));
    await waitFor(() => expect(mock.evidences.find((item) => item.description === "Tela de autenticação")?.display_order).toBe(1));
    view.unmount(); render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Evidências" }));
    expect(await screen.findByText("Tela de autenticação")).toBeInTheDocument();
    expect(screen.getByText("3", { selector: ".evidence-heading span" })).toBeInTheDocument();
  });

  it("gera, edita e persiste o Markdown separadamente das anotações", async () => {
    const mock = installApi(); window.history.replaceState({}, "", "/labs/1"); render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Relatório" }));
    expect(await screen.findByText(/Campos incompletos/)).toHaveTextContent("Objetivo");
    fireEvent.change(screen.getByLabelText("Objetivo"), { target: { value: "Documentar o ataque" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar Markdown" }));
    expect(await screen.findByRole("heading", { name: "Cache Poisoning" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Código" }));
    const editor = screen.getByLabelText("Editor Markdown");
    fireEvent.change(editor, { target: { value: `${(editor as HTMLTextAreaElement).value}\nEdição manual` } });
    expect(screen.getByText("Alterações não salvas")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Salvar" }));
    await waitFor(() => expect(mock.report?.markdown).toContain("Edição manual"));
    expect(mock.labs[0].notes).toBe(baseLab.notes);
  });

  it("renderiza Markdown sem executar HTML ou imagens externas", () => {
    const view = render(<SafeMarkdown markdown={'# Seguro\n\n<script>alert("x")</script>\n\n![externa](https://evil.invalid/x.png)'} imageMap={new Map()} />);
    expect(screen.getByRole("heading", { name: "Seguro" })).toBeInTheDocument();
    expect(screen.getByText(/<script>alert/)).toBeInTheDocument();
    expect(view.container.querySelector("script")).toBeNull();
    expect(view.container.querySelector("img")).toBeNull();
  });

  it("apresenta estado de erro da API com opção de tentar novamente", async () => {
    installApi([], true); window.history.replaceState({}, "", "/labs"); render(<App />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Database unavailable");
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });

});
