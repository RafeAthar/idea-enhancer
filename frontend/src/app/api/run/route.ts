/**
 * POST /api/run — SSE streaming endpoint for running the pipeline.
 * Emits real-time events as the pipeline progresses.
 */

import { NextRequest } from 'next/server';
import { runPipeline, resumePipeline } from '@/lib/pipeline/runner';

export async function POST(request: NextRequest) {
  const body = await request.json();
  const { idea, skip_interview } = body;

  if (!idea || !idea.trim()) {
    return new Response(JSON.stringify({ error: 'Idea is required' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }

  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const emit = (eventType: string, data: Record<string, unknown>) => {
        try {
          const message = `event: ${eventType}\ndata: ${JSON.stringify(data)}\n\n`;
          controller.enqueue(encoder.encode(message));
        } catch {
          // Stream may be closed
        }
      };

      try {
        await runPipeline(idea.trim(), {
          skipInterview: !!skip_interview,
          emit,
        });
      } catch (error) {
        emit('pipeline_error', {
          phase: 'pipeline',
          error: error instanceof Error ? error.message : String(error),
        });
      } finally {
        try {
          controller.close();
        } catch {
          // Already closed
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
    },
  });
}
