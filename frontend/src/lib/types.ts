// ============================================================
// SSE Event Types
// ============================================================

export type SSEEventType =
  | 'pipeline_start'
  | 'phase_start'
  | 'api_call_start'
  | 'thinking_delta'
  | 'text_delta'
  | 'web_search_start'
  | 'web_search_result'
  | 'usage_update'
  | 'api_call_end'
  | 'phase_complete'
  | 'interview_questions'
  | 'pipeline_complete'
  | 'pipeline_error';

export interface PipelineStartEvent {
  type: 'pipeline_start';
  idea: string;
  model: string;
  timestamp: string;
}

export interface PhaseStartEvent {
  type: 'phase_start';
  phase: 'interview' | 'research' | 'critique' | 'decision';
  timestamp: string;
}

export interface ApiCallStartEvent {
  type: 'api_call_start';
  call_id: string;
  phase: string;
  model: string;
}

export interface ThinkingDeltaEvent {
  type: 'thinking_delta';
  call_id: string;
  text: string;
}

export interface TextDeltaEvent {
  type: 'text_delta';
  call_id: string;
  text: string;
}

export interface WebSearchStartEvent {
  type: 'web_search_start';
  call_id: string;
  query: string;
}

export interface WebSearchResultEvent {
  type: 'web_search_result';
  call_id: string;
  url: string;
  snippet: string;
}

export interface UsageUpdateEvent {
  type: 'usage_update';
  call_id: string;
  input_tokens: number;
  output_tokens: number;
  cost_so_far: number;
}

export interface ApiCallEndEvent {
  type: 'api_call_end';
  call_id: string;
  total_tokens: number;
  cost: number;
  duration: number;
}

export interface PhaseCompleteEvent {
  type: 'phase_complete';
  phase: string;
  duration: number;
  result_summary: string;
}

export interface InterviewQuestionsEvent {
  type: 'interview_questions';
  run_id: string;
  questions: string[];
}

export interface PipelineCompleteEvent {
  type: 'pipeline_complete';
  report_slug: string;
  total_cost: number;
  total_duration: number;
}

export interface PipelineErrorEvent {
  type: 'pipeline_error';
  phase: string;
  error: string;
}

export type SSEEvent =
  | PipelineStartEvent
  | PhaseStartEvent
  | ApiCallStartEvent
  | ThinkingDeltaEvent
  | TextDeltaEvent
  | WebSearchStartEvent
  | WebSearchResultEvent
  | UsageUpdateEvent
  | ApiCallEndEvent
  | PhaseCompleteEvent
  | InterviewQuestionsEvent
  | PipelineCompleteEvent
  | PipelineErrorEvent;

// ============================================================
// Report Types (matching Python models.py)
// ============================================================

export interface ReportSummary {
  slug: string;
  title: string;
  date: string;
  score: number;
  recommendation: 'explore' | 'build' | 'kill';
}

// Scores matching the Python model: tam, competitive_density, moat, founder_fit, why_now, capital_efficiency
export interface Scores {
  tam: number;
  competitive_density: number;
  moat: number;
  founder_fit: number;
  why_now: number;
  capital_efficiency: number;
}

export interface PersonaCritique {
  persona: string;
  content: string;
}

export interface QA {
  question: string;
  answer: string;
}

export interface DecisionArtifact {
  scores: Scores;
  kill_criteria: string[];
  validation_experiment: string;
  recommendation: 'explore' | 'build' | 'kill';
  rationale: string;
}

export interface Report {
  title: string;
  slug: string;
  date: string;
  idea: string;
  score: number;
  recommendation: 'explore' | 'build' | 'kill';
  interview: QA[];
  market: string;
  competitors: string;
  critiques: PersonaCritique[];
  synthesis: string;
  decision: DecisionArtifact;
}

// ============================================================
// Leaderboard Types
// ============================================================

export interface LeaderboardEntry {
  rank: number;
  slug: string;
  title: string;
  score: number;
  recommendation: 'explore' | 'build' | 'kill';
  date: string;
}

// ============================================================
// Search Types
// ============================================================

export interface SearchResult {
  slug: string;
  similarity: number;
  recommendation: 'explore' | 'build' | 'kill';
  date: string;
}

// ============================================================
// Compare Types
// ============================================================

export interface CompareResult {
  comparison: string;
}

// ============================================================
// Model Types
// ============================================================

export interface ModelInfo {
  id: string;
  input_cost: number;
  output_cost: number;
}

// ============================================================
// Pipeline State
// ============================================================

export type PipelinePhase = 'interview' | 'research' | 'critique' | 'decision';

export type PipelineStatus = 'idle' | 'running' | 'interview' | 'complete' | 'error';

export interface CallState {
  callId: string;
  phase: string;
  model: string;
  thinking: string;
  text: string;
  webSearches: WebSearchInfo[];
  inputTokens: number;
  outputTokens: number;
  cost: number;
  duration: number;
  isComplete: boolean;
}

export interface WebSearchInfo {
  query: string;
  results: { url: string; snippet: string }[];
}

export interface PhaseCost {
  phase: PipelinePhase;
  cost: number;
  tokens: number;
  duration: number;
}

export interface PipelineState {
  status: PipelineStatus;
  idea: string;
  model: string;
  runId: string | null;
  reportSlug: string | null;
  currentPhase: PipelinePhase | null;
  completedPhases: PipelinePhase[];
  calls: Record<string, CallState>;
  phaseCosts: PhaseCost[];
  totalCost: number;
  totalTokens: number;
  totalDuration: number;
  interviewQuestions: string[];
  interviewAnswers: Record<number, string>;
  error: string | null;
  decision: DecisionArtifact | null;
  market: string;
  competitors: string;
  critiques: PersonaCritique[];
  synthesis: string;
}

export function createInitialPipelineState(): PipelineState {
  return {
    status: 'idle',
    idea: '',
    model: '',
    runId: null,
    reportSlug: null,
    currentPhase: null,
    completedPhases: [],
    calls: {},
    phaseCosts: [],
    totalCost: 0,
    totalTokens: 0,
    totalDuration: 0,
    interviewQuestions: [],
    interviewAnswers: {},
    error: null,
    decision: null,
    market: '',
    competitors: '',
    critiques: [],
    synthesis: '',
  };
}

// ============================================================
// API Request Types
// ============================================================

export interface RunPipelineRequest {
  idea: string;
  model?: string;
  skip_interview?: boolean;
  non_interactive?: boolean;
}

export interface SubmitAnswersRequest {
  run_id: string;
  answers: { question: string; answer: string }[];
}

export interface SearchRequest {
  query: string;
}

export interface CompareRequest {
  slug_a: string;
  slug_b: string;
}

// ============================================================
// Tab Types
// ============================================================

export type AppTab = 'pipeline' | 'reports' | 'report-viewer' | 'compare';

// ============================================================
// Score dimension labels for UI display
// ============================================================

export const SCORE_DIMENSIONS: { key: keyof Scores; label: string; shortLabel: string }[] = [
  { key: 'tam', label: 'TAM', shortLabel: 'TAM' },
  { key: 'competitive_density', label: 'Competitive Density', shortLabel: 'Comp Density' },
  { key: 'moat', label: 'Moat', shortLabel: 'Moat' },
  { key: 'founder_fit', label: 'Founder-Fit', shortLabel: 'Founder Fit' },
  { key: 'why_now', label: 'Why-Now Timing', shortLabel: 'Why-Now' },
  { key: 'capital_efficiency', label: 'Capital Efficiency', shortLabel: 'Cap Efficiency' },
];
