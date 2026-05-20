import type {
  ReportSummary,
  Report,
  LeaderboardEntry,
  SearchResult,
  CompareResult,
  ModelInfo,
  SubmitAnswersRequest,
  SearchRequest,
  CompareRequest,
} from './types';

const API_BASE = '/api';

function apiUrl(endpoint: string): string {
  return `${API_BASE}${endpoint}`;
}

export async function fetchReports(): Promise<ReportSummary[]> {
  const res = await fetch(apiUrl('/reports'));
  if (!res.ok) throw new Error(`Failed to fetch reports: ${res.statusText}`);
  return res.json();
}

export async function fetchReport(slug: string): Promise<Report> {
  const res = await fetch(apiUrl(`/reports/${slug}`));
  if (!res.ok) throw new Error(`Failed to fetch report: ${res.statusText}`);
  return res.json();
}

export async function fetchReportRaw(slug: string): Promise<string> {
  const res = await fetch(apiUrl(`/reports/${slug}/raw`));
  if (!res.ok) throw new Error(`Failed to fetch raw report: ${res.statusText}`);
  return res.text();
}

export async function searchReports(query: string): Promise<SearchResult[]> {
  const body: SearchRequest = { query };
  const res = await fetch(apiUrl('/search'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to search reports: ${res.statusText}`);
  return res.json();
}

export async function compareIdeas(slugA: string, slugB: string): Promise<CompareResult> {
  const body: CompareRequest = { slug_a: slugA, slug_b: slugB };
  const res = await fetch(apiUrl('/compare'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to compare ideas: ${res.statusText}`);
  return res.json();
}

export async function fetchLeaderboard(): Promise<LeaderboardEntry[]> {
  const res = await fetch(apiUrl('/leaderboard'));
  if (!res.ok) throw new Error(`Failed to fetch leaderboard: ${res.statusText}`);
  return res.json();
}

export async function submitAnswers(runId: string, answers: { question: string; answer: string }[]): Promise<void> {
  const body: SubmitAnswersRequest = { run_id: runId, answers };
  const res = await fetch(apiUrl('/run/answer'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`Failed to submit answers: ${res.statusText}`);
}

export async function fetchModels(): Promise<ModelInfo[]> {
  // Return empty array since z-ai-web-dev-sdk uses its own model
  return [];
}

export async function checkHealth(): Promise<boolean> {
  try {
    const res = await fetch(apiUrl('/health'));
    return res.ok;
  } catch {
    return false;
  }
}

export function getRunUrl(): string {
  return apiUrl('/run');
}
