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

export type SmartEvidenceStatus = "suggested" | "accepted" | "rejected";

export interface SmartEvidenceAnalysis {
  id: number;
  evidence_id: number;
  image_sha256: string;
  model_name: string;
  instruction_version: string;
  detected_tool: string | null;
  visible_observations: string[];
  objective_explanation: string;
  suggested_step: string | null;
  suggested_caption: string;
  possible_sensitive_data: string[];
  uncertainties: string[];
  status: SmartEvidenceStatus;
  created_at: string;
  updated_at: string;
  cached: boolean;
}

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

export type AIReportAction = "improve_notes" | "explain_vulnerability" | "missing_information" | "generate_readme";
export type AIReportStyle = "professional" | "github" | "study";
export type AIReportStatus = "suggested" | "accepted" | "rejected";

export interface AIReportVersion {
  id: number;
  lab_id: number;
  action: AIReportAction;
  style: AIReportStyle;
  status: AIReportStatus;
  model_name: string;
  original_text: string;
  suggested_text: string;
  ambiguities: string[];
  questions: string[];
  created_at: string;
  updated_at: string;
}

export interface AICapabilities {
  text: boolean;
  images: boolean;
  declared: string[];
}

export interface AIModel {
  name: string;
  size: number | null;
  modified_at: string | null;
  capabilities: AICapabilities | null;
}

export interface AISettings {
  enabled: boolean;
  model: string;
  timeout_seconds: number;
  keep_alive: string;
  base_url: string;
}

export interface AIStatus {
  enabled: boolean;
  available: boolean;
  version: string | null;
  selected_model: string;
  selected_model_installed: boolean;
  capabilities: AICapabilities | null;
  error: string | null;
}

export interface AIGeneration {
  model: string;
  text: string;
  done: boolean;
}

export const STATUS_LABELS: Record<LabStatus, string> = {
  todo: "Não iniciado",
  in_progress: "Em andamento",
  solved: "Resolvido",
  documented: "Documentado",
};

export const DIFFICULTIES = ["Fácil", "Médio", "Difícil", "Insano"] as const;
