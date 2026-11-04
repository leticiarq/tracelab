export type LabStatus = "todo" | "in_progress" | "solved" | "documented";

export interface Platform {
  id: number;
  name: string;
  slug: string;
  website_url: string;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  platform_id: number | null;
}

export interface Lab {
  id: number;
  title: string;
  slug: string;
  platform_id: number;
  category_id: number | null;
  source_url: string | null;
  difficulty: string | null;
  status: LabStatus;
  notes: string;
  objective: string | null;
  vulnerability_description: string | null;
  impact: string | null;
  mitigation: string | null;
  learnings: string | null;
  created_at: string;
  updated_at: string;
  solved_at: string | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface LabInput {
  title: string;
  platform_id: number;
  category_id: number | null;
  source_url: string | null;
  difficulty: string | null;
  status: LabStatus;
}

export interface Evidence {
  id: number;
  lab_id: number;
  original_filename: string;
  stored_filename: string;
  mime_type: string;
  file_size: number;
  sha256: string;
  description: string;
  step_label: string | null;
  display_order: number;
  created_at: string;
}

export const STATUS_LABELS: Record<LabStatus, string> = {
  todo: "Não iniciado",
  in_progress: "Em andamento",
  solved: "Resolvido",
  documented: "Documentado",
};

export const DIFFICULTIES = ["Fácil", "Médio", "Difícil", "Insano"] as const;
