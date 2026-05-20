/**
 * Pipeline runner — orchestrates the full idea-enhancement pipeline.
 * Ported from Python pipeline.py, using z-ai-web-dev-sdk.
 * Emits SSE events for real-time UI updates.
 */

import { call, callStreaming, callWithWebSearch, resetUsage, getUsage } from './client';
import type { SSEEmitter } from './client';
import {
  INTERVIEW_SYSTEM, interviewUser,
  MARKET_SYSTEM, marketUser,
  COMPETITOR_SYSTEM, competitorUser,
  PERSONAS, personaUser,
  SYNTHESIS_SYSTEM, synthesisUser,
  DECISION_SYSTEM, decisionUser,
  TITLE_SYSTEM, titleUser,
} from './prompts';
import { parseDecision } from './decision';
import { slugify, writeReport } from './storage';
import type { QA, PersonaCritique, DecisionArtifact, Scores } from '../types';

// ── Interview question parser ──────────────────────────────────────

const QUESTION_RE = /^\s*\d+[.)]\s*(.+)$/;

function parseQuestions(text: string): string[] {
  const questions: string[] = [];
  for (const line of text.split('\n')) {
    const m = line.match(QUESTION_RE);
    if (m) questions.push(m[1].trim());
  }
  if (questions.length === 0) {
    // Fallback: take non-empty, non-header lines
    for (const line of text.split('\n')) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        questions.push(trimmed);
      }
    }
  }
  return questions.slice(0, 7);
}

function contextBlock(qas: QA[]): string {
  return qas
    .filter((qa) => qa.answer.trim())
    .map((qa) => `Q: ${qa.question}\nA: ${qa.answer}`)
    .join('\n\n');
}

// ── Active pipeline state for interview pause/resume ───────────────

interface ActivePipeline {
  runId: string;
  idea: string;
  interview: QA[];
  resolveInterview: () => void;
}

const activePipelines = new Map<string, ActivePipeline>();

export function resumePipeline(runId: string, answers: { question: string; answer: string }[]): void {
  const pipeline = activePipelines.get(runId);
  if (!pipeline) return;

  // Update interview answers
  for (const ans of answers) {
    const idx = pipeline.interview.findIndex((qa) => qa.question === ans.question);
    if (idx >= 0) {
      pipeline.interview[idx].answer = ans.answer;
    }
  }

  // Resume the pipeline
  pipeline.resolveInterview();
}

// ── Main pipeline runner ───────────────────────────────────────────

export async function runPipeline(
  idea: string,
  options: {
    skipInterview?: boolean;
    emit: SSEEmitter;
  }
): Promise<void> {
  const { skipInterview = false, emit } = options;
  const startTime = Date.now();

  idea = idea.trim();
  if (!idea) throw new Error('Idea text is empty.');

  resetUsage();

  const runId = `run-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  let interview: QA[] = [];
  let market = '';
  let competitors = '';
  let critiques: PersonaCritique[] = [];
  let synthesis = '';
  let decision: DecisionArtifact | null = null;
  let title = '';
  let slug = '';

  try {
    // ── Title generation ───────────────────────────────────────────
    emit('pipeline_start', {
      idea,
      model: 'z-ai',
      timestamp: new Date().toISOString(),
    });

    title = await call(TITLE_SYSTEM, titleUser(idea), {
      maxTokens: 100,
      phase: 'title',
      callId: `${runId}-title`,
      emit,
    });

    // Clean title
    title = title.split('\n')[0]?.trim().replace(/^["']|["']$/g, '') || 'Untitled idea';
    slug = slugify(title);

    // ── Phase 1: Interview ─────────────────────────────────────────
    emit('phase_start', { phase: 'interview', timestamp: new Date().toISOString() });

    if (!skipInterview) {
      const questionsText = await call(INTERVIEW_SYSTEM, interviewUser(idea), {
        maxTokens: 2000,
        phase: 'interview',
        callId: `${runId}-interview`,
        emit,
      });

      const questions = parseQuestions(questionsText);

      // Emit interview questions and pause
      emit('interview_questions', { run_id: runId, questions });

      // Create a promise that will be resolved when the user submits answers
      const interviewQAs = questions.map((q) => ({ question: q, answer: '' }));
      interview = interviewQAs;

      await new Promise<void>((resolve) => {
        activePipelines.set(runId, {
          runId,
          idea,
          interview,
          resolveInterview: resolve,
        });
      });

      // Answers have been updated by resumePipeline
      const pipeline = activePipelines.get(runId);
      if (pipeline) {
        interview = pipeline.interview;
        activePipelines.delete(runId);
      }
    }

    const context = contextBlock(interview);
    const phase1Duration = Date.now() - startTime;
    emit('phase_complete', { phase: 'interview', duration: phase1Duration, result_summary: `${interview.length} questions` });

    // ── Phase 2: Research (parallel) ───────────────────────────────
    emit('phase_start', { phase: 'research', timestamp: new Date().toISOString() });

    const [marketResult, competitorsResult] = await Promise.all([
      callWithWebSearch(MARKET_SYSTEM, marketUser(idea, context), {
        phase: 'research',
        callId: `${runId}-market`,
        emit,
      }),
      callWithWebSearch(COMPETITOR_SYSTEM, competitorUser(idea, context), {
        phase: 'research',
        callId: `${runId}-competitors`,
        emit,
      }),
    ]);

    market = marketResult;
    competitors = competitorsResult;

    const phase2Duration = Date.now() - startTime - phase1Duration;
    emit('phase_complete', { phase: 'research', duration: phase2Duration, result_summary: 'Market + competitor scan complete' });

    // ── Phase 3: Critique (parallel personas) ──────────────────────
    emit('phase_start', { phase: 'critique', timestamp: new Date().toISOString() });

    const critiqueResults = await Promise.all(
      PERSONAS.map(([name, system], idx) =>
        callStreaming(system, personaUser(idea, context, market, competitors), {
          maxTokens: 4000,
          phase: 'critique',
          callId: `${runId}-critique-${idx}`,
          emit,
        }).then((text) => ({ name, text }))
      )
    );

    critiques = critiqueResults.map((r) => ({ persona: r.name, content: r.text }));

    // ── Phase 3b: Synthesis ────────────────────────────────────────
    const critiquesText = critiques.map((c) => `### ${c.persona}\n\n${c.content}`).join('\n\n');
    synthesis = await call(SYNTHESIS_SYSTEM, synthesisUser(critiquesText), {
      maxTokens: 3000,
      phase: 'critique',
      callId: `${runId}-synthesis`,
      emit,
    });

    const phase3Duration = Date.now() - startTime - phase2Duration - phase1Duration;
    emit('phase_complete', { phase: 'critique', duration: phase3Duration, result_summary: `${critiques.length} persona critiques + synthesis` });

    // ── Phase 4: Decision ──────────────────────────────────────────
    emit('phase_start', { phase: 'decision', timestamp: new Date().toISOString() });

    const decisionText = await call(
      DECISION_SYSTEM,
      decisionUser(idea, context, market, competitors, synthesis),
      {
        maxTokens: 2500,
        phase: 'decision',
        callId: `${runId}-decision`,
        emit,
      }
    );

    decision = parseDecision(decisionText);

    const phase4Duration = Date.now() - startTime - phase3Duration - phase2Duration - phase1Duration;
    emit('phase_complete', { phase: 'decision', duration: phase4Duration, result_summary: `Recommendation: ${decision.recommendation}` });

    // ── Save report ────────────────────────────────────────────────
    const created = new Date().toISOString().slice(0, 10);
    const filename = writeReport({
      idea,
      title,
      slug,
      created,
      interview,
      market,
      competitors,
      critiques,
      synthesis,
      decision,
    });

    const totalDuration = Date.now() - startTime;
    const avgScore = decision
      ? (decision.scores.tam +
          decision.scores.competitive_density +
          decision.scores.moat +
          decision.scores.founder_fit +
          decision.scores.why_now +
          decision.scores.capital_efficiency) /
        6
      : 0;

    emit('pipeline_complete', {
      report_slug: slug,
      total_cost: 0,
      total_duration: totalDuration,
    });
  } catch (error) {
    // Partial save on failure
    const created = new Date().toISOString().slice(0, 10);
    if (title) {
      try {
        writeReport({
          idea,
          title,
          slug,
          created,
          interview,
          market,
          competitors,
          critiques,
          synthesis,
          decision,
        });
      } catch {
        // Best effort
      }
    }

    emit('pipeline_error', {
      phase: 'pipeline',
      error: error instanceof Error ? error.message : String(error),
    });
  }
}
