/**
 * GET /api/reports — List all reports as summaries.
 */

import { NextResponse } from 'next/server';
import { listReports, parseFrontmatter } from '@/lib/pipeline/storage';

export async function GET() {
  try {
    const reports = listReports();
    const summaries = reports.map((r) => {
      const scoreStr = r['score'] || '';
      const scoreMatch = scoreStr.match(/([0-9]+(?:\.[0-9]+)?)/);
      const score = scoreMatch ? parseFloat(scoreMatch[1]) : -1;

      return {
        slug: r['slug'] || '',
        title: r['title'] || r['slug'] || 'Untitled',
        date: r['date'] || '',
        score,
        recommendation: (r['recommendation'] || 'explore') as 'explore' | 'build' | 'kill',
      };
    });

    return NextResponse.json(summaries);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to list reports' },
      { status: 500 }
    );
  }
}
