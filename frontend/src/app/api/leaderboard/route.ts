/**
 * GET /api/leaderboard — Reports ranked by score.
 */

import { NextResponse } from 'next/server';
import { listReports } from '@/lib/pipeline/storage';

export async function GET() {
  try {
    const reports = listReports();

    const ranked = reports
      .map((r) => {
        const scoreStr = r['score'] || '';
        const scoreMatch = scoreStr.match(/([0-9]+(?:\.[0-9]+)?)/);
        const score = scoreMatch ? parseFloat(scoreMatch[1]) : -1;
        return {
          slug: r['slug'] || '',
          title: r['title'] || r['slug'] || 'Untitled',
          score,
          recommendation: (r['recommendation'] || 'explore') as 'explore' | 'build' | 'kill',
          date: r['date'] || '',
        };
      })
      .sort((a, b) => b.score - a.score)
      .map((r, idx) => ({ ...r, rank: idx + 1 }));

    return NextResponse.json(ranked);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch leaderboard' },
      { status: 500 }
    );
  }
}
