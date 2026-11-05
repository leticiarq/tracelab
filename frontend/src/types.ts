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
  resolution_steps: string | null;
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
  finding_id: number | null;
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

export type FindingStatus = "open" | "confirmed" | "remediated" | "accepted_risk";

export interface CVSSAssessment {
  id: number;
  finding_id: number;
  version: string;
  vector: string;
  score: number;
  severity: string;
  justification: string;
  created_at: string;
  updated_at: string;
}

export interface Finding {
  id: number;
  lab_id: number;
  title: string;
  slug: string;
  category: string | null;
  cwe_id: string | null;
  description: string;
  technical_details: string;
  reproduction_steps: string;
  impact: string;
  mitigation: string;
  status: FindingStatus;
  display_order: number;
  created_at: string;
  updated_at: string;
  cvss_assessment: CVSSAssessment | null;
  evidences?: Evidence[];
}

export type FindingInput = Pick<Finding, "title" | "category" | "cwe_id" | "description" | "technical_details" | "reproduction_steps" | "impact" | "mitigation" | "status">;

export interface Report {
  id: number;
  lab_id: number;
  markdown: string;
  revision: number;
  generated_at: string;
  updated_at: string;
  incomplete_fields: string[];
  sensitive_warnings: string[];
}

export const STATUS_LABELS: Record<LabStatus, string> = {
  todo: "Não iniciado",
  in_progress: "Em andamento",
  solved: "Resolvido",
  documented: "Documentado",
};

export const DIFFICULTIES = ["Fácil", "Médio", "Difícil", "Insano"] as const;
