import { useLoadingStore } from '@/stores/loading';

const API_BASE = '/api';

interface ValidationIssue {
  loc?: unknown[];
  msg?: string;
}

interface ApiErrorBody {
  error?: { code?: string; message?: string };
  detail?: string | ValidationIssue[];
  request_id?: string;
}

function detailMessage(detail: ApiErrorBody['detail']): string | undefined {
  if (typeof detail === 'string') return detail;
  if (!Array.isArray(detail)) return undefined;
  return detail
    .map((issue) => {
      const loc = Array.isArray(issue.loc) ? issue.loc.filter((x) => x !== 'body' && x !== 'query').join('.') : '';
      return `${loc ? loc + ': ' : ''}${issue.msg || ''}`.trim();
    })
    .filter(Boolean)
    .join('; ');
}

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;

  constructor(status: number, body: ApiErrorBody | string) {
    const parsed: ApiErrorBody = typeof body === 'string' ? { error: { code: 'UNKNOWN', message: body } } : body;
    super(detailMessage(parsed.detail) || parsed.error?.message || `HTTP ${status}`);
    this.status = status;
    this.code = parsed.error?.code || (status === 422 ? 'VALIDATION' : 'UNKNOWN');
    this.requestId = parsed.request_id;
  }
}

export interface ApiResponse<T> {
  data: T;
}

type Query = Record<string, string | number | boolean | undefined | null>;

export function apiUrl(path: string, query?: Query): string {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(query ?? {})) {
    if (v !== undefined && v !== null) params.set(k, String(v));
  }
  const qs = params.toString();
  return qs ? `${API_BASE}${path}?${qs}` : `${API_BASE}${path}`;
}

function request<T>(method: string, path: string, opts: { query?: Query; body?: unknown } = {}): Promise<ApiResponse<T>> {
  return tracked(() => send<T>(method, path, opts));
}

async function send<T>(method: string, path: string, opts: { query?: Query; body?: unknown } = {}): Promise<ApiResponse<T>> {
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json';

  const res = await fetch(apiUrl(path, opts.query), {
    method,
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
    credentials: 'same-origin',
  });

  if (res.status === 204) return { data: undefined as unknown as T };

  const isJson = (res.headers.get('content-type') || '').includes('application/json');
  const payload = isJson ? await res.json() : await res.text();
  if (!res.ok) throw new ApiError(res.status, payload as ApiErrorBody | string);
  return { data: payload as T };
}

async function tracked<T>(work: () => Promise<T>): Promise<T> {
  const loading = useLoadingStore();
  loading.start();
  try {
    return await work();
  } finally {
    loading.stop();
  }
}

export const apiClient = {
  get: <T>(path: string, query?: Query) => request<T>('GET', path, { query }),
  post: <T>(path: string, body?: unknown, query?: Query) => request<T>('POST', path, { body, query }),
};
