export type Severity = "error" | "warning" | "info" | string;

export interface Finding {
  code?: string;
  severity?: Severity;
  title?: string;
  message?: string;
  evidence?: string;
  why?: string;
  recommendation?: string;
  file?: string;
  category?: string;
  confidence?: string;
}

export interface ConfigurationGroup {
  files?: string[];
  checks?: Array<{ file: string; status?: string }>;
  structural_status?: string;
  validity?: Record<string, string>;
  syntax_status?: Record<string, string>;
  dependency_resolution?: string;
}

export interface ValidationReport {
  repository?: string;
  default_branch?: string;
  status?: string;
  supported?: boolean;
  language?: string | null;
  framework?: string | null;
  test_files?: string[];
  test_file_count?: number;
  exit_code?: number | null;
  stdout?: string;
  stderr?: string;
  duration_seconds?: number | null;
  execution_mode?: string;
  message?: string;
  validation_status?: string;
  test_status?: string;
  readiness_assessment?: string;
  configuration_status?: string;
  findings?: Finding[];
  configuration?: {
    workflows?: ConfigurationGroup;
    python_test_configuration?: ConfigurationGroup;
    dependency_manifests?: ConfigurationGroup;
  };
}

export type FindingFilter = "all" | "error" | "warning" | "info";
export type ResultState = "success" | "failure" | "warning" | "error" | "partial";
