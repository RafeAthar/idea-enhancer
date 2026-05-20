/**
 * TF-IDF search — ported from Python corpus.py.
 * Stdlib-only implementation for finding similar reports.
 */

import { listReports, parseFrontmatter } from './storage';
import type { SearchResult } from '../types';

const WORD_RE = /[a-z][a-z0-9]+/g;
const STOPWORDS = new Set([
  'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'has', 'are',
  'was', 'were', 'but', 'not', 'you', 'your', 'they', 'their', 'would',
  'could', 'should', 'will', 'what', 'which', 'when', 'where', 'while',
  'into', 'than', 'then', 'them', 'also', 'any', 'all', 'can', 'may',
  'more', 'less', 'very', 'much', 'some', 'such', 'one', 'two', 'three',
  'about', 'over', 'under', 'between', 'out', 'off', 'down', 'up', 'its',
  'it', 'is', 'be', 'an', 'a', 'of', 'to', 'in', 'on', 'or', 'as', 'by',
  'at', 'if', 'we', 'us', 'our', 'i', 'do', 'does', 'did', 'so',
]);

function tokens(text: string): string[] {
  return (text.toLowerCase().match(WORD_RE) || []).filter((w) => !STOPWORDS.has(w));
}

function tfidfMatrix(docs: string[]): [Map<string, number>[], Map<string, number>] {
  const tfs: Map<string, number>[] = docs.map((doc) => {
    const counts = new Map<string, number>();
    for (const t of tokens(doc)) {
      counts.set(t, (counts.get(t) || 0) + 1);
    }
    return counts;
  });

  const df = new Map<string, number>();
  for (const tf of tfs) {
    for (const term of tf.keys()) {
      df.set(term, (df.get(term) || 0) + 1);
    }
  }

  const n = docs.length || 1;
  const idf = new Map<string, number>();
  for (const [term, cnt] of df) {
    idf.set(term, Math.log((n + 1) / (cnt + 1)) + 1);
  }

  return [tfs, idf];
}

function vec(tf: Map<string, number>, idf: Map<string, number>): Map<string, number> {
  if (tf.size === 0) return new Map();
  const norm = Math.max(...tf.values());
  const v = new Map<string, number>();
  for (const [term, count] of tf) {
    v.set(term, (count / norm) * (idf.get(term) || 0));
  }
  return v;
}

function cosine(a: Map<string, number>, b: Map<string, number>): number {
  if (a.size === 0 || b.size === 0) return 0;
  let dot = 0;
  for (const [k, va] of a) {
    if (b.has(k)) dot += va * (b.get(k) || 0);
  }
  let na = 0;
  for (const v of a.values()) na += v * v;
  let nb = 0;
  for (const v of b.values()) nb += v * v;
  na = Math.sqrt(na);
  nb = Math.sqrt(nb);
  return na && nb ? dot / (na * nb) : 0;
}

export function searchReports(query: string, top = 5): SearchResult[] {
  const reports = listReports();
  if (reports.length === 0) return [];

  const docs = reports.map((r) => r['body'] || '');
  const [tfs, idf] = tfidfMatrix([...docs, query]);
  const queryVec = vec(tfs[tfs.length - 1], idf);

  const scored: [number, Record<string, string>][] = [];
  for (let i = 0; i < tfs.length - 1; i++) {
    scored.push([cosine(vec(tfs[i], idf), queryVec), reports[i]]);
  }
  scored.sort((a, b) => b[0] - a[0]);

  return scored
    .slice(0, top)
    .filter(([sim]) => sim > 0)
    .map(([sim, r]) => ({
      slug: r['slug'] || '',
      similarity: sim,
      recommendation: (r['recommendation'] || 'explore') as 'explore' | 'build' | 'kill',
      date: r['date'] || '',
    }));
}
