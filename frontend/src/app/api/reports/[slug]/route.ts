/**
 * GET /api/reports/[slug] — Get a specific report.
 * GET /api/reports/[slug]?raw=true — Get raw markdown.
 */

import { NextRequest, NextResponse } from 'next/server';
import { findReportBySlug, parseFrontmatter } from '@/lib/pipeline/storage';

function parseReportFromMarkdown(markdown: string) {
  const meta = parseFrontmatter(markdown);
  const body = markdown.replace(/^---[\s\S]*?---\n/, '');

  const scoreStr = meta['score'] || '';
  const scoreMatch = scoreStr.match(/([0-9]+(?:\.[0-9]+)?)/);
  const score = scoreMatch ? parseFloat(scoreMatch[1]) : -1;

  const idea = extractSection(body, 'Idea');
  const interview = extractInterview(body);
  const market = extractSection(body, 'Market analysis');
  const competitors = extractSection(body, 'Competitor scan');
  const critiques = extractCritiques(body);
  const synthesis = extractSection(body, 'Synthesis');
  const decision = extractDecision(body);

  return {
    title: meta['title'] || 'Untitled',
    slug: meta['slug'] || '',
    date: meta['date'] || '',
    idea,
    score,
    recommendation: (meta['recommendation'] || 'explore') as 'explore' | 'build' | 'kill',
    interview,
    market,
    competitors,
    critiques,
    synthesis,
    decision,
  };
}

function extractSection(text: string, header: string): string {
  const pattern = new RegExp(`^##\\s*${header}\\s*\\n([\\s\\S]*?)(?=^##\\s|\\Z)`, 'm');
  const m = text.match(pattern);
  return m ? m[1].trim() : '';
}

function extractInterview(text: string): Array<{ question: string; answer: string }> {
  const section = extractSection(text, 'Clarifying questions');
  if (!section) return [];

  const qas: Array<{ question: string; answer: string }> = [];
  const parts = section.split(/\*\*\d+\.\s/).filter((p) => p.trim());
  for (const part of parts) {
    const lines = part.split('\n');
    const question = lines[0]?.replace(/\*\*$/, '').trim() || '';
    const answer = lines.slice(1).join('\n').trim().replace(/^_\(|\)_$/g, '');
    if (question) {
      qas.push({ question, answer });
    }
  }
  return qas;
}

function extractCritiques(text: string): Array<{ persona: string; content: string }> {
  const section = extractSection(text, 'Multi-persona critique');
  if (!section) return [];

  const critiques: Array<{ persona: string; content: string }> = [];
  const parts = section.split(/^###\s/m).filter((p) => p.trim());
  for (const part of parts) {
    const lines = part.split('\n');
    const persona = lines[0]?.trim() || '';
    const content = lines.slice(1).join('\n').trim();
    if (persona) {
      critiques.push({ persona, content });
    }
  }
  return critiques;
}

function extractDecision(text: string): any {
  const section = extractSection(text, 'Decision artifact');
  if (!section) return null;

  const scoresSection = section.match(/### Scores \(1-10\)\s*\n([\s\S]*?)(?=###|$)/);
  const scores: Record<string, number> = {};
  if (scoresSection) {
    const scoreLines = [...scoresSection[1].matchAll(/^-\s*(.+?):\s*(\d+)/gm)];
    for (const m of scoreLines) {
      const label = m[1].trim().toLowerCase();
      const val = parseInt(m[2], 10);
      if (label.includes('tam')) scores.tam = val;
      else if (label.includes('competitive density') || label.includes('competitive_density')) scores.competitive_density = val;
      else if (label === 'moat') scores.moat = val;
      else if (label.includes('founder')) scores.founder_fit = val;
      else if (label.includes('why-now') || label.includes('why now')) scores.why_now = val;
      else if (label.includes('capital')) scores.capital_efficiency = val;
    }
  }

  const killSection = section.match(/### Kill criteria\s*\n([\s\S]*?)(?=###|$)/);
  const killCriteria: string[] = [];
  if (killSection) {
    const killLines = [...killSection[1].matchAll(/^-\s*(.+)$/gm)];
    for (const m of killLines) killCriteria.push(m[1].trim());
  }

  const expSection = section.match(/### Cheapest validation experiment\s*\n([\s\S]*?)(?=###|$)/);
  const validationExperiment = expSection ? expSection[1].trim() : '';

  const recSection = section.match(/### Recommendation\s*\n([\s\S]*?)(?=###|$)/);
  let recommendation = 'explore';
  let rationale = '';
  if (recSection) {
    const recText = recSection[1].trim();
    const recMatch = recText.match(/\*\*(kill|explore|build)\*\*\s*[—\-]\s*(.*)/i);
    if (recMatch) {
      recommendation = recMatch[1].toLowerCase();
      rationale = recMatch[2].trim();
    } else {
      rationale = recText;
    }
  }

  return {
    scores: {
      tam: scores.tam || 5,
      competitive_density: scores.competitive_density || 5,
      moat: scores.moat || 5,
      founder_fit: scores.founder_fit || 5,
      why_now: scores.why_now || 5,
      capital_efficiency: scores.capital_efficiency || 5,
    },
    kill_criteria: killCriteria.length > 0 ? killCriteria : ['No kill criteria identified'],
    validation_experiment: validationExperiment || 'No experiment defined',
    recommendation,
    rationale,
  };
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;

  try {
    const report = findReportBySlug(slug);
    if (!report || !report['body']) {
      return NextResponse.json({ error: 'Report not found' }, { status: 404 });
    }

    const url = new URL(request.url);
    if (url.searchParams.get('raw') === 'true') {
      return new Response(report['body'], {
        headers: { 'Content-Type': 'text/markdown' },
      });
    }

    const parsed = parseReportFromMarkdown(report['body']);
    return NextResponse.json(parsed);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to read report' },
      { status: 500 }
    );
  }
}
