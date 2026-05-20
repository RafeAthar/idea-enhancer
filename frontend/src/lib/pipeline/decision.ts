/**
 * Decision parser — ported from Python decision.py.
 * Parses the LLM output into a structured DecisionArtifact.
 */

import type { DecisionArtifact, Scores } from '../types';

const SCORE_LINE_RE = /^-\s*([A-Za-z][A-Za-z\s\-/]*?):\s*(\d{1,2})/gm;
const RECOMMENDATION_RE = /Recommendation:\s*(kill|explore|build)\s*[\.\-:]?\s*(.*)/i;

// Mapping from normalized label → Scores field name
const SCORE_FIELDS: Record<string, keyof Scores> = {
  tam: 'tam',
  'competitive density': 'competitive_density',
  'competitive_density': 'competitive_density',
  moat: 'moat',
  'founder-fit': 'founder_fit',
  'founder fit': 'founder_fit',
  'why-now timing': 'why_now',
  'why-now': 'why_now',
  'capital efficiency': 'capital_efficiency',
};

function extractSection(text: string, header: string): string {
  const pattern = new RegExp(
    `^###\\s*${escapeRegex(header)}\\s*\\n([\\s\\S]*?)(?=^###\\s|\\Z)`,
    'm'
  );
  const m = text.match(pattern);
  return m ? m[1].trim() : '';
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function parseScores(scoresBlock: string): Scores {
  const found: Record<string, number> = {};
  let match: RegExpExecArray | null;

  // Reset regex state
  const re = new RegExp(SCORE_LINE_RE.source, 'gm');
  while ((match = re.exec(scoresBlock)) !== null) {
    const label = match[1].trim().toLowerCase();
    const val = Math.max(1, Math.min(10, parseInt(match[2], 10)));
    if (!isNaN(val)) {
      found[label] = val;
    }
  }

  // Build Scores with explicit per-field lookup
  const fieldValues: Partial<Scores> = {};
  for (const [label, fieldName] of Object.entries(SCORE_FIELDS)) {
    if (label in found) {
      (fieldValues as any)[fieldName] = found[label];
    }
  }

  return {
    tam: fieldValues.tam ?? 5,
    competitive_density: fieldValues.competitive_density ?? 5,
    moat: fieldValues.moat ?? 5,
    founder_fit: fieldValues.founder_fit ?? 5,
    why_now: fieldValues.why_now ?? 5,
    capital_efficiency: fieldValues.capital_efficiency ?? 5,
  };
}

function parseKillCriteria(block: string): string[] {
  const out: string[] = [];
  for (const line of block.split('\n')) {
    const s = line.trim();
    if (s.startsWith('-') || s.startsWith('*') || s.startsWith('•')) {
      out.push(s.slice(1).trim());
    }
  }
  return out.slice(0, 5);
}

function parseRecommendation(block: string): [string, string] {
  const m = block.match(RECOMMENDATION_RE);
  if (!m) return ['explore', block.trim()];
  return [m[1].toLowerCase(), m[2].trim().replace(/^[\-—:.]+/, '').trim()];
}

export function parseDecision(text: string): DecisionArtifact {
  const scoresBlock =
    extractSection(text, 'Scores (1-10, integer)') || extractSection(text, 'Scores');
  const killBlock = extractSection(text, 'Kill criteria');
  const expBlock = extractSection(text, 'Cheapest validation experiment');
  const recBlock = extractSection(text, 'Recommendation');

  const scores = parseScores(scoresBlock);
  const kill = parseKillCriteria(killBlock);
  const [rec, rationale] = parseRecommendation(recBlock);

  return {
    scores,
    kill_criteria: kill.length > 0 ? kill : ['(no kill criteria parsed — see raw output)'],
    validation_experiment: expBlock || '(no experiment parsed — see raw output)',
    recommendation: rec as 'kill' | 'explore' | 'build',
    rationale,
  };
}
