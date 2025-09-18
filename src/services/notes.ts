/**
 * Notes service integration - read-only GET calls and create mutation.
 */
import { request } from '../lib/api';

export type Note = {
  id: string | number;
  title?: string;
  content?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
} & Record<string, unknown>;

export type TagsResponse = { tags: string[] };

export function listAllNotes(): Promise<Note[]> {
  return request('/notes');
}

export function searchNotes(q: string): Promise<Note[]> {
  const qp = `?q=${encodeURIComponent(q)}`;
  return request(`/notes/search${qp}`);
}

export function getAllTags(): Promise<TagsResponse> {
  return request('/notes/tags');
}

export function getNotesByTag(tag: string): Promise<Note[]> {
  const qp = `?tag=${encodeURIComponent(tag)}`;
  return request(`/notes/by-tag${qp}`);
}

export function createNote(input: {
  title: string;
  content: string;
  tags?: string[];
}): Promise<Note> {
  return request('/notes', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}
