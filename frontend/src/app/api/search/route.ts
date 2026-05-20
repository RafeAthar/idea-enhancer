/**
 * POST /api/search — TF-IDF search across reports.
 */

import { NextRequest, NextResponse } from 'next/server';
import { searchReports } from '@/lib/pipeline/corpus';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { query } = body;

  if (!query || !query.trim()) {
    return NextResponse.json({ error: 'Query is required' }, { status: 400 });
  }

  try {
    const results = searchReports(query.trim());
    return NextResponse.json(results);
  } catch (error) {
    return NextResponse.json(
      { error: 'Search failed' },
      { status: 500 }
    );
  }
}
