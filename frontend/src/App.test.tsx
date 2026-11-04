import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "./App";
import type { AIReportVersion, Evidence, Lab, Report, SmartEvidenceAnalysis } from "./types";
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
  const aiReportVersions: AIReportVersion[] = [];
  const analyses = new Map<number, SmartEvidenceAnalysis>();
  let aiSettings = { enabled: true, model: "qwen3-vl:2b", timeout_seconds: 120, keep_alive: "5m", base_url: "http://127.0.0.1:11434" };
  const aiStatus = () => ({ enabled: aiSettings.enabled, available: aiSettings.enabled, version: aiSettings.enabled ? "0.12.0" : null, selected_model: aiSettings.model, selected_model_installed: aiSettings.enabled, capabilities: aiSettings.enabled ? { text: true, images: true, declared: ["completion", "vision"] } : null, error: aiSettings.enabled ? null : "A IA está desativada." });
  const fetchMock = vi.fn(async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(typeof input === "string" ? input : input instanceof URL ? input.href : input.url);
    const method = init?.method || "GET";
    if (url.pathname === "/api/ai/settings" && method === "GET") return json(aiSettings);
    if (url.pathname === "/api/ai/settings" && method === "PATCH") { aiSettings = { ...aiSettings, ...JSON.parse(String(init?.body)) }; return json(aiSettings); }
    if (url.pathname === "/api/ai/status" && method === "GET") return json(aiStatus());
    if (url.pathname === "/api/ai/models" && method === "GET") return json([{ name: "qwen3-vl:2b", size: 1_900_000_000, modified_at: null, capabilities: { text: true, images: true, declared: ["completion", "vision"] } }]);
    if (url.pathname === "/api/ai/test-connection" && method === "POST") return json(aiStatus());
    if (url.pathname === "/api/ai/test-generation" && method === "POST") return json({ model: aiSettings.model, text: "Geração local funcionando.", done: true });
    if (url.pathname === "/api/ai/operations/current" && method === "DELETE") return json({ cancelled: true });
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
    const aiReportCollection = url.pathname.match(/^\/api\/labs\/(\d+)\/report\/ai\/versions$/);
    if (aiReportCollection && method === "GET") return json(aiReportVersions);
    const aiReportGenerate = url.pathname.match(/^\/api\/labs\/(\d+)\/report\/ai\/generate$/);
    if (aiReportGenerate && method === "POST") {
      const payload = JSON.parse(String(init?.body)); const now = new Date().toISOString();
      const version: AIReportVersion = { id: aiReportVersions.length + 1, lab_id: Number(aiReportGenerate[1]), action: payload.action, style: payload.style, status: "suggested", model_name: aiSettings.model, original_text: baseLab.notes, suggested_text: "# Cache Poisoning\n\n## Objetivo\n\nDocumentação sugerida localmente.", ambiguities: ["Ferramenta não informada."], questions: ["Qual ferramenta foi utilizada?"], created_at: now, updated_at: now };
      aiReportVersions.unshift(version); return json(version);
    }
    const aiReportReview = url.pathname.match(/^\/api\/labs\/(\d+)\/report\/ai\/versions\/(\d+)$/);
    if (aiReportReview && method === "PATCH") {
      const version = aiReportVersions.find((item) => item.id === Number(aiReportReview[2]))!; const action = JSON.parse(String(init?.body)).action;
      version.status = action === "accept" ? "accepted" : "rejected"; version.updated_at = new Date().toISOString(); return json(version);
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
    const analysisRoute = url.pathname.match(/^\/api\/labs\/(\d+)\/evidences\/(\d+)\/analysis$/);
    if (analysisRoute) {
      const id = Number(analysisRoute[2]);
      if (method === "GET") return json(analyses.get(id) ?? null);
      if (method === "POST") {
        const now = new Date().toISOString();
        const analysis: SmartEvidenceAnalysis = { id, evidence_id: id, image_sha256: "a".repeat(64), model_name: aiSettings.model, instruction_version: "smart-evidence-v1", detected_tool: "Burp Suite Repeater", visible_observations: ["Resposta HTTP 200 visível"], objective_explanation: "Observação: resposta 200. Inferência: a requisição foi repetida.", suggested_step: "02 · Validação", suggested_caption: "Resposta HTTP no Repeater", possible_sensitive_data: ["Possível cookie"], uncertainties: [], status: "suggested", created_at: now, updated_at: now, cached: false };
        analyses.set(id, analysis); return json(analysis);
      }
      if (method === "PATCH") {
        const payload = JSON.parse(String(init?.body)); const current = analyses.get(id)!;
        const updated = { ...current, ...payload, status: payload.action === "accept" ? "accepted" : payload.action === "reject" ? "rejected" : "suggested", updated_at: new Date().toISOString() } as SmartEvidenceAnalysis;
        delete (updated as SmartEvidenceAnalysis & { action?: string }).action;
        analyses.set(id, updated);
        if (payload.action === "accept") { const evidence = evidences.find((item) => item.id === id)!; evidence.description = updated.suggested_caption; evidence.step_label = updated.suggested_step; }
        return json(updated);
      }
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

  it("analisa, permite revisar a legenda e aceita Smart Evidence", async () => {
    const mock = installApi(); window.history.replaceState({}, "", "/labs/1"); render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Evidências" }));
    fireEvent.change(await screen.findByLabelText("Selecionar evidências"), { target: { files: [new File(["shot"], "repeater.png", { type: "image/png" })] } });
    await screen.findByText("1 evidência enviada com sucesso.");
    fireEvent.click(await screen.findByRole("button", { name: "Analisar com IA" }));
    expect(await screen.findByDisplayValue("Resposta HTTP no Repeater")).toBeDisabled();
    expect(screen.getByDisplayValue("Possível cookie")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Editar análise" }));
    fireEvent.change(screen.getByLabelText("Legenda sugerida"), { target: { value: "Resposta 200 confirmada visualmente" } });
    fireEvent.change(screen.getByLabelText("Etapa sugerida"), { target: { value: "02 · Revisão manual" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar análise" }));
    await screen.findByText("Análise editada e salva para revisão.");
    fireEvent.click(screen.getByRole("button", { name: "Aceitar" }));
    await screen.findByText("Análise aceita; legenda e etapa estão disponíveis para o README.");
    await waitFor(() => expect(mock.evidences[0].description).toBe("Resposta 200 confirmada visualmente"));
    expect(mock.evidences[0].step_label).toBe("02 · Revisão manual");
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

  it("gera README com Ollama, compara e exige aceite humano antes do editor", async () => {
    const mock = installApi(); window.history.replaceState({}, "", "/labs/1"); render(<App />);
    fireEvent.click(await screen.findByRole("tab", { name: "Relatório" }));
    fireEvent.change(await screen.findByLabelText("Estilo do relatório"), { target: { value: "study" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar README com IA" }));
    expect(await screen.findByLabelText("Texto original")).toHaveValue(baseLab.notes);
    expect((screen.getByLabelText("Texto sugerido") as HTMLTextAreaElement).value).toContain("Documentação sugerida");
    expect(screen.getByText("Qual ferramenta foi utilizada?")).toBeInTheDocument();
    expect(screen.queryByLabelText("Editor Markdown")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Aceitar no editor" }));
    expect(((await screen.findByLabelText("Editor Markdown")) as HTMLTextAreaElement).value).toContain("Documentação sugerida");
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

  it("configura e testa a integração local de IA", async () => {
    installApi(); window.history.replaceState({}, "", "/settings/ai"); render(<App />);
    expect(await screen.findByRole("heading", { name: "Configurações de IA" })).toBeInTheDocument();
    expect(screen.getByText("Ollama disponível")).toBeInTheDocument();
    expect(screen.getByLabelText("Modelo selecionado")).toHaveValue("qwen3-vl:2b");
    fireEvent.click(screen.getByRole("button", { name: "Testar geração" }));
    expect(await screen.findByText("Geração local funcionando.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("checkbox"));
    expect((await screen.findAllByText("Desativada")).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: "Testar geração" })).toBeDisabled();
  });
});
