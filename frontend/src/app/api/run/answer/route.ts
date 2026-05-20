/**
 * POST /api/run/answer — Submit interview answers to resume a paused pipeline.
 */

import { NextRequest, NextResponse } from 'next/server';
import { resumePipeline } from '@/lib/pipeline/runner';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { run_id, answers } = body;

  if (!run_id || !answers) {
    return NextResponse.json({ error: 'run_id and answers are required' }, { status: 400 });
  }

  resumePipeline(run_id, answers);

  return NextResponse.json({ status: 'ok' });
}
