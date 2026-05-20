/**
 * LLM client using z-ai-web-dev-sdk — replaces the Python Anthropic client.
 * Provides streaming and non-streaming calls with usage tracking.
 */

import ZAI from 'z-ai-web-dev-sdk';

// ── Token / cost tracking ──────────────────────────────────────────

export interface UsageStats {
  totalInputTokens: number;
  totalOutputTokens: number;
  callCount: number;
}

let _usage: UsageStats = {
  totalInputTokens: 0,
  totalOutputTokens: 0,
  callCount: 0,
};

export function resetUsage(): void {
  _usage = { totalInputTokens: 0, totalOutputTokens: 0, callCount: 0 };
}

export function getUsage(): UsageStats {
  return { ..._usage };
}

function recordUsage(inputTokens: number, outputTokens: number): void {
  _usage.totalInputTokens += inputTokens;
  _usage.totalOutputTokens += outputTokens;
  _usage.callCount++;
}

// ── ZAI Client singleton ───────────────────────────────────────────

let _zai: ZAI | null = null;

async function getClient(): Promise<ZAI> {
  if (!_zai) {
    _zai = await ZAI.create();
  }
  return _zai;
}

// ── SSE Event emitter type ─────────────────────────────────────────

export interface SSEEmitter {
  (eventType: string, data: Record<string, unknown>): void;
}

// ── Non-streaming call ─────────────────────────────────────────────

export async function call(
  system: string,
  user: string,
  options?: {
    maxTokens?: number;
    phase?: string;
    callId?: string;
    emit?: SSEEmitter;
  }
): Promise<string> {
  const { maxTokens = 16000, phase = '', callId = '', emit } = options || {};
  const zai = await getClient();

  const startTime = Date.now();

  emit?.('api_call_start', {
    call_id: callId,
    phase,
    model: 'z-ai',
  });

  try {
    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
      ],
      max_tokens: maxTokens,
    });

    const content = completion.choices[0]?.message?.content || '';
    const inputTokens = completion.usage?.prompt_tokens || 0;
    const outputTokens = completion.usage?.completion_tokens || 0;
    const duration = Date.now() - startTime;

    recordUsage(inputTokens, outputTokens);

    emit?.('usage_update', {
      call_id: callId,
      input_tokens: _usage.totalInputTokens,
      output_tokens: _usage.totalOutputTokens,
      cost_so_far: 0,
    });

    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: inputTokens + outputTokens,
      cost: 0,
      duration,
    });

    return content;
  } catch (error) {
    const duration = Date.now() - startTime;
    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: 0,
      cost: 0,
      duration,
    });
    throw error;
  }
}

// ── Streaming call (yields text deltas via SSE) ────────────────────

export async function callStreaming(
  system: string,
  user: string,
  options?: {
    maxTokens?: number;
    phase?: string;
    callId?: string;
    emit?: SSEEmitter;
  }
): Promise<string> {
  const { maxTokens = 16000, phase = '', callId = '', emit } = options || {};
  const zai = await getClient();

  const startTime = Date.now();

  emit?.('api_call_start', {
    call_id: callId,
    phase,
    model: 'z-ai',
  });

  try {
    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: user },
      ],
      max_tokens: maxTokens,
      stream: true,
    });

    let fullText = '';
    let inputTokens = 0;
    let outputTokens = 0;

    // Handle both streaming and non-streaming responses
    if (Symbol.asyncIterator in Object(completion)) {
      for await (const chunk of completion as AsyncIterable<any>) {
        const delta = chunk.choices?.[0]?.delta?.content || '';
        if (delta) {
          fullText += delta;
          emit?.('text_delta', {
            call_id: callId,
            text: delta,
          });
        }

        // Track usage from chunks if available
        if (chunk.usage) {
          inputTokens = chunk.usage.prompt_tokens || 0;
          outputTokens = chunk.usage.completion_tokens || 0;
        }
      }
    } else {
      // Non-streaming fallback
      const resp = completion as any;
      fullText = resp.choices?.[0]?.message?.content || '';
      inputTokens = resp.usage?.prompt_tokens || 0;
      outputTokens = resp.usage?.completion_tokens || 0;

      // Emit as one big delta
      emit?.('text_delta', {
        call_id: callId,
        text: fullText,
      });
    }

    const duration = Date.now() - startTime;

    recordUsage(inputTokens, outputTokens);

    emit?.('usage_update', {
      call_id: callId,
      input_tokens: _usage.totalInputTokens,
      output_tokens: _usage.totalOutputTokens,
      cost_so_far: 0,
    });

    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: inputTokens + outputTokens,
      cost: 0,
      duration,
    });

    return fullText;
  } catch (error) {
    const duration = Date.now() - startTime;
    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: 0,
      cost: 0,
      duration,
    });
    throw error;
  }
}

// ── Call with web search ───────────────────────────────────────────

export async function callWithWebSearch(
  system: string,
  user: string,
  options?: {
    maxTokens?: number;
    phase?: string;
    callId?: string;
    emit?: SSEEmitter;
  }
): Promise<string> {
  const { maxTokens = 16000, phase = '', callId = '', emit } = options || {};
  const zai = await getClient();

  const startTime = Date.now();

  emit?.('api_call_start', {
    call_id: callId,
    phase,
    model: 'z-ai',
  });

  try {
    // First, use web search to gather information
    const searchQueries = await generateSearchQueries(zai, system, user);
    
    // Execute web searches
    const searchResults: Array<{ query: string; results: Array<{ url: string; snippet: string }> }> = [];
    for (const query of searchQueries) {
      emit?.('web_search_start', {
        call_id: callId,
        query,
      });

      try {
        const result = await zai.functions.invoke('web_search', { query, num: 5 });
        const results = Array.isArray(result)
          ? result.map((r: any) => ({
              url: r.url || '',
              snippet: r.snippet || '',
            }))
          : [];

        searchResults.push({ query, results });

        // Emit each search result
        for (const r of results) {
          emit?.('web_search_result', {
            call_id: callId,
            url: r.url,
            snippet: r.snippet,
          });
        }
      } catch (searchErr) {
        console.warn('Web search failed for query:', query, searchErr);
        searchResults.push({ query, results: [] });
      }
    }

    // Format search results into the user prompt
    let searchContext = '';
    if (searchResults.length > 0) {
      searchContext = '\n\n---\nWeb search results:\n';
      for (const sr of searchResults) {
        searchContext += `\nQuery: "${sr.query}"\n`;
        for (const r of sr.results) {
          searchContext += `- [${r.snippet}](${r.url})\n`;
        }
      }
    }

    // Now call the LLM with the search results embedded
    const enhancedUser = user + searchContext;

    const completion = await zai.chat.completions.create({
      messages: [
        { role: 'system', content: system },
        { role: 'user', content: enhancedUser },
      ],
      max_tokens: maxTokens,
      stream: true,
    });

    let fullText = '';
    let inputTokens = 0;
    let outputTokens = 0;

    if (Symbol.asyncIterator in Object(completion)) {
      for await (const chunk of completion as AsyncIterable<any>) {
        const delta = chunk.choices?.[0]?.delta?.content || '';
        if (delta) {
          fullText += delta;
          emit?.('text_delta', {
            call_id: callId,
            text: delta,
          });
        }
        if (chunk.usage) {
          inputTokens = chunk.usage.prompt_tokens || 0;
          outputTokens = chunk.usage.completion_tokens || 0;
        }
      }
    } else {
      const resp = completion as any;
      fullText = resp.choices?.[0]?.message?.content || '';
      inputTokens = resp.usage?.prompt_tokens || 0;
      outputTokens = resp.usage?.completion_tokens || 0;
      emit?.('text_delta', { call_id: callId, text: fullText });
    }

    const duration = Date.now() - startTime;
    recordUsage(inputTokens, outputTokens);

    emit?.('usage_update', {
      call_id: callId,
      input_tokens: _usage.totalInputTokens,
      output_tokens: _usage.totalOutputTokens,
      cost_so_far: 0,
    });

    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: inputTokens + outputTokens,
      cost: 0,
      duration,
    });

    return fullText;
  } catch (error) {
    const duration = Date.now() - startTime;
    emit?.('api_call_end', {
      call_id: callId,
      total_tokens: 0,
      cost: 0,
      duration,
    });
    throw error;
  }
}

// ── Helper: generate search queries from the prompt ────────────────

async function generateSearchQueries(
  zai: ZAI,
  system: string,
  user: string
): Promise<string[]> {
  try {
    const completion = await zai.chat.completions.create({
      messages: [
        {
          role: 'system',
          content:
            'Given a research task, generate 2-4 specific web search queries that would help find relevant market data, competitors, and trends. Output only the queries, one per line, no numbering, no quotes.',
        },
        {
          role: 'user',
          content: `Research task:\nSystem: ${system.slice(0, 500)}\nUser: ${user.slice(0, 500)}`,
        },
      ],
      max_tokens: 200,
    });

    const content = completion.choices[0]?.message?.content || '';
    return content
      .split('\n')
      .map((l: string) => l.trim().replace(/^["'\d.]+\s*/, ''))
      .filter((l: string) => l.length > 5)
      .slice(0, 4);
  } catch {
    // Fallback: extract key terms from the idea
    return [user.slice(0, 100)];
  }
}
