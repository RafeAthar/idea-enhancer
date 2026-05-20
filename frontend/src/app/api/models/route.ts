/**
 * GET /api/models — Return available models (z-ai-web-dev-sdk uses its own model).
 */

import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json([]);
}
