import { apiClient } from './client';
import type { SessionDetail, SessionSummary, Supplier } from './types';

export const fetchSessions = () => apiClient.get<SessionSummary[]>('/sessions').then((r) => r.data);
export const fetchSession = (key: string) => apiClient.get<SessionDetail>(`/sessions/${key}`).then((r) => r.data);
export const fetchSuppliers = () => apiClient.get<Supplier[]>('/suppliers').then((r) => r.data);
