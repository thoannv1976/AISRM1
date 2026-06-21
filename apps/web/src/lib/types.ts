// Shared TypeScript types mirroring backend DTOs.

export interface UserOut {
  id: string;
  organization_id: string;
  email: string;
  display_name: string;
  status: string;
  locale: string;
  title?: string | null;
  primary_unit_id?: string | null;
  is_external?: boolean;
}

export interface MeOut {
  user: UserOut;
  permissions: string[];
  system_roles: string[];
  is_admin: boolean;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface Proposal {
  id: string;
  proposal_code: string;
  title: string;
  status: string;
  abstract?: string | null;
  pi_id: string;
  lead_unit_id?: string | null;
  budget_total: string | number;
  currency: string;
  content_json?: Record<string, unknown>;
  version: number;
  call_id: string;
}

export interface Call {
  id: string;
  code: string;
  title: string;
  description?: string | null;
  status: string;
  open_at?: string | null;
  close_at?: string | null;
  budget_limit?: string | number | null;
  currency: string;
  fields: string[];
}

export interface Researcher {
  id: string;
  full_name: string;
  academic_title?: string | null;
  degree?: string | null;
  unit_id?: string | null;
  email?: string | null;
  keywords: string[];
  h_index?: number | null;
  public_visibility: boolean;
}

export interface Project {
  id: string;
  project_code: string;
  title: string;
  status: string;
  approved_budget: string | number;
  currency: string;
  completion_percent: string | number;
  start_date?: string | null;
  end_date?: string | null;
}

export interface ResearchOutput {
  id: string;
  output_type: string;
  title: string;
  year?: number | null;
  doi?: string | null;
  venue_name?: string | null;
  status: string;
  verification_status: string;
}

export interface ValidationIssue {
  code: string;
  severity: string;
  message: string;
  field?: string | null;
}

export interface AIOutput {
  id: string;
  job_id: string;
  output_type: string;
  content_json: Record<string, any>;
  confidence?: number | null;
  insufficient_evidence: boolean;
  human_status: string;
  citations: { citation_id: string; excerpt?: string | null; document_id?: string | null }[];
}

export interface Suggestion {
  reviewer_id: string;
  full_name: string;
  score: number;
  reasons: string[];
  excluded: boolean;
  exclusion_reason?: string | null;
}
