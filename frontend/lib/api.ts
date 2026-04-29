export type ScoreReason = {
  key: string;
  label: string;
  score: number;
  detail: string;
};

export type EventCluster = {
  id: string;
  title: string;
  summary: string | null;
  translatedTitle: string | null;
  translatedSummary: string | null;
  translatedAt: string | null;
  displayTitle: string;
  displaySummary: string | null;
  hotScore: number;
  scoreReasonJson: ScoreReason[];
  confidence: number;
  firstSeenAt: string | null;
  lastSeenAt: string | null;
  evidenceCount: number;
  sourceNames: string[];
  sourceTypes: string[];
};

export type EventEvidence = {
  id: string;
  rawItemId: string;
  sourceName: string;
  sourceUrl: string;
  quote: string | null;
  confidence: number;
  rawTitle: string;
  rawContentText: string | null;
};

export type EventClusterDetail = EventCluster & {
  evidence: EventEvidence[];
};

export type FetchRun = {
  id: string;
  sourceId: string;
  status: string;
  itemsFound: number;
  itemsCreated: number;
  errorMessage: string | null;
};

export type AiRun = {
  id: string;
  taskType: string;
  inputHash: string;
  model: string | null;
  status: string;
  tokenEstimate: number | null;
  errorMessage: string | null;
};

export type BriefTemplate = {
  id: string;
  name: string;
  mode: string;
  sectionsJson: string[];
  styleRules: string | null;
};

export type BriefExport = {
  id: string;
  templateId: string;
  title: string;
  eventClusterIdsJson: string[];
  manualNotesJson: Record<string, string>;
  markdown: string;
  generatedAt: string;
};

export type Source = {
  id: string;
  type: string;
  name: string;
  url: string | null;
  enabled: boolean;
  weight: number;
  pollIntervalMinutes: number;
  configJson: Record<string, unknown>;
  lastFetchedAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
};

const API_BASE_URL =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const PUBLIC_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function postJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function postJsonBody<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function patchJsonBody<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function deleteJson(path: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return "未记录";
  }
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}
