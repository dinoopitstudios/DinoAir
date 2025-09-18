/**
 * Core service integration for Tools page.
 * Includes read-only GET calls and selected mutation calls.
 */
import { request } from '../lib/api';

export type CurrentTimeResponse = { iso?: string } & Record<string, unknown>;
export type ListDirectoryResponse = {
  entries?: string[];
  [key: string]: unknown;
};
export type AddTwoNumbersResponse = {
  result?: number;
  [key: string]: unknown;
};

export function getCurrentTime(): Promise<CurrentTimeResponse> {
  return request('/core/current-time');
}

export function listDirectory(path: string): Promise<ListDirectoryResponse> {
  const qp = `?path=${encodeURIComponent(path)}`;
  return request(`/core/list-directory${qp}`);
}

export function addTwoNumbers(a: number, b: number): Promise<AddTwoNumbersResponse> {
  return request('/core/add-two-numbers', {
    method: 'POST',
    body: JSON.stringify({ a, b }),
  });
}
