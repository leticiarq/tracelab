import type { Category, Evidence, Lab, LabInput, LabStatus, Page, Platform } from "./types";

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
  updateLab(id: number, data: Partial<LabInput> & { notes?: string }) {
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
