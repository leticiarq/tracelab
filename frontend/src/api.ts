import type { AIGeneration, AIModel, AISettings, AIStatus, Category, Evidence, Lab, LabInput, LabStatus, Page, Platform, Report } from "./types";

const API_URL = (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: init?.body && !(init.body instanceof FormData) ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new ApiError("Não foi possível conectar à API. Verifique se o backend está em execução.", 0);
  }

  if (!response.ok) {
    let message = "A API não conseguiu concluir a operação.";
    try {
      const body = (await response.json()) as { detail?: string | Array<{ msg: string }> };
      if (typeof body.detail === "string") message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((item) => item.msg).join("; ");
    } catch {
      // Keep the safe fallback for non-JSON responses.
    }
    throw new ApiError(message, response.status);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function requestBlob(path: string, init: RequestInit): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
  if (!response.ok) {
    let message = "Não foi possível exportar o relatório.";
    try { const body = await response.json() as { detail?: string }; if (body.detail) message = body.detail; } catch { /* safe fallback */ }
    throw new ApiError(message, response.status);
  }
  const disposition = response.headers.get("Content-Disposition") || "";
  const filename = disposition.match(/filename="([^"]+)"/)?.[1] || "tracelab-report.zip";
  return { blob: await response.blob(), filename };
}

function queryString(params: Record<string, string | number | undefined | null>) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
  });
  const value = query.toString();
  return value ? `?${value}` : "";
}

export const api = {
  listLabs(params: {
    page?: number;
    page_size?: number;
    search?: string;
    platform_id?: number;
    category_id?: number;
    status?: LabStatus;
  } = {}) {
    return request<Page<Lab>>(`/api/labs${queryString(params)}`);
  },
  getLab(id: number) {
    return request<Lab>(`/api/labs/${id}`);
  },
  createLab(data: LabInput) {
    return request<Lab>("/api/labs", { method: "POST", body: JSON.stringify(data) });
  },
  updateLab(id: number, data: Partial<LabInput & Pick<Lab, "notes" | "objective" | "vulnerability_description" | "impact" | "mitigation" | "learnings" | "resolution_steps">>) {
    return request<Lab>(`/api/labs/${id}`, { method: "PATCH", body: JSON.stringify(data) });
  },
  deleteLab(id: number) {
    return request<void>(`/api/labs/${id}`, { method: "DELETE" });
  },
  listPlatforms() {
    return request<Page<Platform>>("/api/platforms?page_size=100");
  },
  createPlatform(data: { name: string; website_url: string }) {
    return request<Platform>("/api/platforms", { method: "POST", body: JSON.stringify(data) });
  },
  listCategories(platformId?: number) {
    return request<Page<Category>>(
      `/api/categories${queryString({ page_size: 100, platform_id: platformId })}`,
    );
  },
  createCategory(data: { name: string; platform_id: number | null }) {
    return request<Category>("/api/categories", { method: "POST", body: JSON.stringify(data) });
  },
  listEvidences(labId: number) {
    return request<Evidence[]>(`/api/labs/${labId}/evidences`);
  },
  uploadEvidences(labId: number, files: File[]) {
    const body = new FormData();
    files.forEach((file) => body.append("files", file));
    return request<Evidence[]>(`/api/labs/${labId}/evidences`, { method: "POST", body });
  },
  updateEvidence(labId: number, evidenceId: number, data: { description?: string; step_label?: string | null }) {
    return request<Evidence>(`/api/labs/${labId}/evidences/${evidenceId}`, { method: "PATCH", body: JSON.stringify(data) });
  },
  reorderEvidences(labId: number, evidenceIds: number[]) {
    return request<Evidence[]>(`/api/labs/${labId}/evidences/order`, { method: "PATCH", body: JSON.stringify({ evidence_ids: evidenceIds }) });
  },
  deleteEvidence(labId: number, evidenceId: number) {
    return request<void>(`/api/labs/${labId}/evidences/${evidenceId}`, { method: "DELETE" });
  },
  getReport(labId: number) {
    return request<Report | null>(`/api/labs/${labId}/report`);
  },
  generateReport(labId: number, confirmOverwrite = false) {
    return request<Report>(`/api/labs/${labId}/report/generate`, { method: "POST", body: JSON.stringify({ confirm_overwrite: confirmOverwrite }) });
  },
  saveReport(labId: number, markdown: string) {
    return request<Report>(`/api/labs/${labId}/report`, { method: "PUT", body: JSON.stringify({ markdown }) });
  },
  exportReport(labId: number, evidenceIds: number[], sensitiveReviewed: boolean) {
    return requestBlob(`/api/labs/${labId}/report/export`, { method: "POST", body: JSON.stringify({ evidence_ids: evidenceIds, sensitive_reviewed: sensitiveReviewed }) });
  },
  getAISettings() {
    return request<AISettings>("/api/ai/settings");
  },
  updateAISettings(data: { enabled?: boolean; model?: string }) {
    return request<AISettings>("/api/ai/settings", { method: "PATCH", body: JSON.stringify(data) });
  },
  getAIStatus() {
    return request<AIStatus>("/api/ai/status");
  },
  listAIModels() {
    return request<AIModel[]>("/api/ai/models");
  },
  testAIConnection() {
    return request<AIStatus>("/api/ai/test-connection", { method: "POST" });
  },
  testAIGeneration() {
    return request<AIGeneration>("/api/ai/test-generation", { method: "POST" });
  },
  cancelAIOperation() {
    return request<{ cancelled: boolean }>("/api/ai/operations/current", { method: "DELETE" });
  },
};

export function evidenceContentUrl(labId: number, evidenceId: number) {
  return `${API_URL}/api/labs/${labId}/evidences/${evidenceId}/content`;
}

export function evidenceDownloadUrl(labId: number, evidenceId: number) {
  return `${API_URL}/api/labs/${labId}/evidences/${evidenceId}/download`;
}

export async function listAllLabs(): Promise<Lab[]> {
  const first = await api.listLabs({ page: 1, page_size: 100 });
  if (first.pages <= 1) return first.items;
  const remaining = await Promise.all(
    Array.from({ length: first.pages - 1 }, (_, index) =>
      api.listLabs({ page: index + 2, page_size: 100 }),
    ),
  );
  return [first, ...remaining].flatMap((page) => page.items);
}
