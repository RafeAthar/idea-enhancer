import type { SSEEvent, SSEEventType } from './types';

export interface SSEClientOptions {
  onEvent: (event: SSEEvent) => void;
  onError?: (error: Error) => void;
  onClose?: () => void;
}

/**
 * Connect to the SSE pipeline endpoint via POST.
 * Parses the response as SSE format and calls onEvent for each parsed event.
 * Returns an AbortController for cancellation.
 */
export function connectSSE(
  url: string,
  body: Record<string, unknown>,
  options: SSEClientOptions
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`SSE connection failed: ${response.status} ${response.statusText}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events from the buffer
        const lines = buffer.split('\n');
        buffer = '';

        let currentEventType = '';
        let currentData = '';

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];

          if (line.startsWith('event: ')) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            currentData += line.slice(6);
          } else if (line.startsWith('data:')) {
            currentData += line.slice(5);
          } else if (line === '') {
            // Empty line = end of event
            if (currentData) {
              try {
                const parsed = JSON.parse(currentData);
                const eventType = (currentEventType || parsed.type) as SSEEventType;
                const event = { ...parsed, type: eventType } as SSEEvent;
                options.onEvent(event);
              } catch (e) {
                console.warn('Failed to parse SSE data:', currentData, e);
              }
            }
            currentEventType = '';
            currentData = '';
          } else {
            // Keep partial lines in buffer
            if (i === lines.length - 1) {
              buffer = line;
            }
          }
        }
      }

      options.onClose?.();
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        options.onClose?.();
        return;
      }
      options.onError?.(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}
