/**
 * POST /api/compare — Compare two ideas using LLM.
 */

import { NextRequest, NextResponse } from 'next/server';
import { findReportBySlug } from '@/lib/pipeline/storage';
import { COMPARE_SYSTEM } from '@/lib/pipeline/prompts';
import { call } from '@/lib/pipeline/client';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { slug_a, slug_b } = body;

  if (!slug_a || !slug_b) {
    return NextResponse.json({ error: 'Both slug_a and slug_b are required' }, { status: 400 });
  }

  try {
    const reportA = findReportBySlug(slug_a);
    const reportB = findReportBySlug(slug_b);

    if (!reportA || !reportB) {
      return NextResponse.json({ error: 'One or both reports not found' }, { status: 404 });
    }

    const user = `### Idea A — ${reportA['slug']}\n\n${reportA['body']}\n\n### Idea B — ${reportB['slug']}\n\n${reportB['body']}\n\nCompare per the system prompt.`;

    const comparison = await call(COMPARE_SYSTEM, user, { maxTokens: 4000 });

    return NextResponse.json({ comparison });
  } catch (error) {
    return NextResponse.json(
      { error: 'Comparison failed: ' + (error instanceof Error ? error.message : String(error)) },
      { status: 500 }
    );
  }
}
