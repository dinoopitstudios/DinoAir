/**
 * File Search service integration - read-only GET calls and index mutations.
 */
import { request } from '../lib/api';

// Define interfaces for API responses
export interface SearchResult {
  files: Array<{
    path: string;
    name: string;
    size: number;
    modified: string; // ISO date string
    [key: string]: unknown; // For any additional fields
  }>;
  total: number;
  [key: string]: unknown;
}

export interface FileInfo {
  path: string;
  name: string;
  size: number;
  modified: string; // ISO date string
  type: string;
  [key: string]: unknown;
}

export interface SearchStats {
  totalFiles: number;
  totalDirectories: number;
  lastIndexed: string; // ISO date string
  [key: string]: unknown;
}

export interface Directories {
  directories: string[];
  [key: string]: unknown;
}

export interface FileEmbeddings {
  path: string;
  embeddings: number[];
  [key: string]: unknown;
}
export function searchByKeywords(keywords: string): Promise<SearchResult> {
  const qp = `?keywords=${encodeURIComponent(keywords)}`;
  return request(`/files/search${qp}`);
}

export function getFileInfo(path: string): Promise<FileInfo> {
  const qp = `?path=${encodeURIComponent(path)}`;
  return request(`/files/info${qp}`);
}

export function getStats(): Promise<SearchStats> {
  return request('/search/stats');
}

export function getDirectories(): Promise<Directories> {
  return request('/search/directories');
}

export function getFileEmbeddings(path: string): Promise<FileEmbeddings> {
  const qp = `?path=${encodeURIComponent(path)}`;
  return request(`/files/embeddings${qp}`);
}

export function addFileToIndex(
  path: string
): Promise<{ success?: boolean } & Record<string, unknown>> {
  return request('/files/index', {
    method: 'POST',
    body: JSON.stringify({ path }),
  });
}

export function removeFileFromIndex(
  path: string
): Promise<{ success?: boolean } & Record<string, unknown>> {
  // Using body payload for DELETE per README semantics (server should support).
  return request('/files/index', {
    method: 'DELETE',
    body: JSON.stringify({ path }),
  });
}
