/**
 * Projects service integration - read-only GET calls for connectivity tests.
 */
import { request } from '../lib/api';

export type Project = Record<string, unknown>;
export type Projects = Project[];
export interface ProjectStats {
  totalProjects: number;
  activeProjects: number;
  archivedProjects: number;
  [key: string]: number; // If there may be additional numeric stats
}

export function listAll(): Promise<Projects> {
  return request('/projects');
}

export function get(id: string | number): Promise<Project> {
  return request(`/projects/${encodeURIComponent(String(id))}`);
}

export function search(q: string): Promise<Projects> {
  const qp = `?q=${encodeURIComponent(q)}`;
  return request(`/projects/search${qp}`);
}

export function byStatus(status: string): Promise<Projects> {
  const qp = `?status=${encodeURIComponent(status)}`;
  return request(`/projects/by-status${qp}`);
}

export function getStats(): Promise<ProjectStats> {
  return request('/projects/stats');
}

export function getTree(id: string | number): Promise<Record<string, unknown>> {
  return request(`/projects/${encodeURIComponent(String(id))}/tree`);
}
