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
  editorialTitle: string | null;
  editorialSummary: string | null;
  editorialCategory: string | null;
  editorialTagsJson: string[];
  editorialPriority: number;
  editorialAt: string | null;
  displayTitle: string;
  displaySummary: string | null;
  hotScore: number;
  scoreReasonJson: ScoreReason[];
  confidence: number;
  eventPhase: string | null;
  credibilityScore: number;
  propagationScore: number;
  primaryIndustry: string | null;
  relatedIndustriesJson: string[];
  industryConfidence: number;
  industryReason: string | null;
  industryClassifiedAt: string | null;
  impactDomainsJson: string[];
  entitiesJson: string[];
  historicalMatchesJson: Array<{
    clusterId: string;
    title: string;
    score: number;
    lastSeenAt: string | null;
  }>;
  intelligenceReasonJson: ScoreReason[];
  firstSeenAt: string | null;
  lastSeenAt: string | null;
  evidenceCount: number;
  sourceNames: string[];
  sourceTypes: string[];
  primarySourceName: string | null;
  primarySourceType: string | null;
  otherSourceTypeCount: number;
};

export type TimelineItem = {
  id: string;
  displayTitle: string;
  displaySummary: string | null;
  sourceName: string;
  sourceType: string | null;
  sourceNames: string[];
  sourceTypes: string[];
  industries: string[];
  industryLabels: string[];
  primaryIndustry: string | null;
  primaryIndustryLabel: string | null;
  relatedIndustries: string[];
  relatedIndustryLabels: string[];
  author: string | null;
  publishedAt: string | null;
  displayedAt: string;
  timeBasis: string;
  lastSeenAt: string | null;
  seenAt: string | null;
  score: number;
  selected: boolean;
  category: string;
  categoryLabel: string;
  tags: string[];
  reason: string;
  url: string | null;
  avatarUrl: string | null;
  mediaUrls: string[];
  evidenceCount: number;
  confidence: number;
};

export type TimelinePage = {
  items: TimelineItem[];
  total: number;
  page: number;
  take: number;
};

export type DailyArchive = {
  date: string;
  title: string;
  storyCount: number;
  generatedAt: string;
};

export type DailySection = {
  key: string;
  index: string;
  label: string;
  englishLabel: string;
  items: TimelineItem[];
};

export type DailyDigest = {
  date: string;
  title: string;
  generatedAt: string;
  storyCount: number;
  sections: DailySection[];
  markdown: string;
  archive: DailyArchive[];
};

export type IndustryReport = {
  domain: string;
  label: string;
  englishLabel: string;
  description: string;
  title: string;
  storyCount: number;
  latestDate: string | null;
  generatedAt: string | null;
  archive: DailyArchive[];
};

export type IndustryDigest = DailyDigest & {
  domain: string;
  label: string;
  englishLabel: string;
  description: string;
};

export type AutomationSchedule = {
  id: string;
  taskType: string;
  enabled: boolean;
  timezone: string;
  runTime: string | null;
  cadenceMinutes: number;
  configJson: Record<string, unknown>;
  lastRunAt: string | null;
  nextRunAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AutomationSettings = {
  schedules: AutomationSchedule[];
};

export type AutomationRunLog = {
  id: string;
  taskType: string;
  status: string;
  startedAt: string;
  finishedAt: string | null;
  payloadJson: Record<string, unknown>;
  errorMessage: string | null;
};

export type AutomationRunResult = {
  taskType: string;
  status: string;
  payload: Record<string, unknown>;
  error: string | null;
};

export type FeedbackEntry = {
  id: string;
  message: string;
  contact: string | null;
  status: string;
  createdAt: string;
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
  rawPublishedAt: string | null;
  rawFetchedAt: string;
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

export type RefreshRun = {
  status: string;
  fetchRuns: FetchRun[];
  clustering: {
    status: string;
    candidatesCreated: number;
    clustersCreated: number;
    clustersUpdated: number;
    evidenceCreated: number;
    aiRunsCreated: number;
    errors: string[];
  };
  classification: {
    status: string;
    clustersClassified: number;
    clustersSkipped: number;
    aiRunsCreated: number;
    errors: string[];
  };
  translation: {
    status: string;
    clustersTranslated: number;
    clustersSkipped: number;
    aiRunsCreated: number;
    errors: string[];
  };
  editorial: {
    status: string;
    clustersEdited: number;
    clustersSkipped: number;
    aiRunsCreated: number;
    errors: string[];
  };
  scoring: {
    clustersScored: number;
  };
  errors: string[];
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

export type SourceHealth = {
  sourceId: string;
  name: string;
  type: string;
  status: string;
  enabled: boolean;
  isDue: boolean;
  lastFetchedAt: string | null;
  nextFetchAt: string | null;
  lastRunStatus: string | null;
  lastRunAt: string | null;
  lastError: string | null;
  totalRuns: number;
  failedRuns: number;
  consecutiveFailures: number;
};

export type MaintenanceHealth = {
  status: string;
  generatedAt: string;
  sourceCount: number;
  enabledSourceCount: number;
  failingSourceCount: number;
  staleSourceCount: number;
  disabledSourceCount: number;
  neverFetchedSourceCount: number;
  sources: SourceHealth[];
};

export type LocalCredential = {
  id: string;
  key: string;
  label: string;
  provider: string | null;
  environmentKey: string | null;
  secretHint: string | null;
  configured: boolean;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
};

export type BriefExport = {
  id: string;
  templateId: string;
  title: string;
  briefType: string | null;
  scopeType: string;
  scopeKey: string;
  reportDate: string | null;
  isPublic: boolean;
  eventClusterIdsJson: string[];
  manualNotesJson: Record<string, string>;
  exportFormatsJson: string[];
  deliveryTargetsJson: Array<{
    targetType: string;
    targetLabel: string;
    status: string;
  }>;
  markdown: string;
  generatedAt: string;
};

export type BriefDelivery = {
  id: string;
  exportId: string;
  targetType: string;
  targetLabel: string;
  status: string;
  payloadJson: Record<string, unknown>;
  errorMessage: string | null;
  createdAt: string;
};

export type TeamSummary = {
  users: TeamUser[];
  spaces: TeamSpace[];
  memberships: TeamMembership[];
  sourceLinks: SourceSpaceLink[];
  bookmarks: EventBookmark[];
  annotations: EventAnnotation[];
  briefReviews: BriefReview[];
  auditLogs: AuditLog[];
};

export type TeamUser = {
  id: string;
  displayName: string;
  email: string | null;
  role: string;
  createdAt: string;
};

export type TeamSpace = {
  id: string;
  name: string;
  description: string | null;
  createdAt: string;
};

export type TeamMembership = {
  id: string;
  spaceId: string;
  userId: string;
  role: string;
  createdAt: string;
};

export type SourceSpaceLink = {
  id: string;
  spaceId: string;
  sourceId: string;
  createdByUserId: string | null;
  createdAt: string;
};

export type EventBookmark = {
  id: string;
  spaceId: string;
  userId: string;
  eventClusterId: string;
  note: string | null;
  createdAt: string;
};

export type EventAnnotation = {
  id: string;
  spaceId: string;
  userId: string;
  eventClusterId: string;
  label: string;
  note: string;
  status: string;
  createdAt: string;
};

export type BriefReview = {
  id: string;
  spaceId: string;
  briefExportId: string;
  requestedByUserId: string;
  reviewerUserId: string | null;
  status: string;
  notes: string | null;
  createdAt: string;
  updatedAt: string;
};

export type AuditLog = {
  id: string;
  actorUserId: string | null;
  action: string;
  entityType: string;
  entityId: string;
  detailJson: Record<string, unknown>;
  createdAt: string;
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
  latestPublishedAt: string | null;
  lastError: string | null;
  createdAt: string;
  updatedAt: string;
};

export type SourcePlatformCapability = {
  platform: string;
  sourceType: string;
  category: string;
  accessMode: string;
  automationLevel: string;
  status: string;
  requiresCredential: boolean;
  requiresApproval: boolean;
  supportsMetrics: boolean;
  costLevel: string;
  notes: string;
};

export type DomesticPlatformPolicy = {
  platform: string;
  sourceType: string;
  status: string;
  automationLevel: string;
  requiresCredential: boolean;
  requiresApproval: boolean;
  allowedPaths: string[];
  prohibitedPaths: string[];
  manualSourceName: string;
  notes: string;
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
