/**
 * Discovery, likes and passes, matches and notifications.
 *
 * Who appears and every score are decided by the backend
 * (backend/app/services/discovery.py and compatibility.py).
 */

import { apiGet, apiPost } from "@/services/api-client";
import {
  parseDecision,
  parseDiscoveryPage,
  parseMatches,
  parseNotifications,
  parseStudentView,
} from "@/services/parse";
import type {
  Decision,
  DecisionResult,
  DiscoveryPage,
  MatchSummary,
  NotificationList,
  StudentView,
} from "@/types/discovery";

/** How many profiles to load at a time. */
export const DISCOVERY_PAGE_SIZE = 10;

export async function fetchDiscovery({
  cursor,
  limit = DISCOVERY_PAGE_SIZE,
  signal,
}: {
  cursor?: string | null;
  limit?: number;
  signal?: AbortSignal;
} = {}): Promise<DiscoveryPage> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) {
    params.set("cursor", cursor);
  }
  return parseDiscoveryPage(
    await apiGet(`/discovery?${params.toString()}`, { signal }),
  );
}

export async function fetchStudent(
  id: string,
  signal?: AbortSignal,
): Promise<StudentView> {
  return parseStudentView(
    await apiGet(`/students/${encodeURIComponent(id)}`, { signal }),
  );
}

export async function sendDecision(
  studentId: string,
  decision: Decision,
): Promise<DecisionResult> {
  const action = decision === "LIKE" ? "like" : "pass";
  return parseDecision(
    await apiPost(`/discovery/${encodeURIComponent(studentId)}/${action}`),
  );
}

export async function fetchMatches(
  signal?: AbortSignal,
): Promise<MatchSummary[]> {
  return parseMatches(await apiGet("/matches", { signal }));
}

export async function fetchNotifications(
  signal?: AbortSignal,
): Promise<NotificationList> {
  return parseNotifications(await apiGet("/notifications", { signal }));
}

export async function markNotificationRead(id: string): Promise<void> {
  await apiPost(`/notifications/${encodeURIComponent(id)}/read`);
}

export async function markAllNotificationsRead(): Promise<void> {
  await apiPost("/notifications/read-all");
}
