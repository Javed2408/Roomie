"use client";

import {
  ArrowLeft,
  Building2,
  CircleCheck,
  ExternalLink,
  History,
  ListChecks,
  Pencil,
  Send,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";
import { AuthorityEvidence } from "@/components/listings/authority-evidence";
import { InterestedStudents } from "@/components/listings/interested-students";
import { ListingCard } from "@/components/listings/listing-card";
import { ListingPhotoManager } from "@/components/listings/listing-photo-manager";
import { ListingStatusBadges } from "@/components/listings/listing-status-badges";
import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState } from "@/components/ui/states";
import { formatTimestampDate } from "@/lib/format";
import { ApiError, describeApiError } from "@/services/api-client";
import {
  changeLifecycle,
  deleteDraft,
  fetchMyListing,
  submitForReview,
} from "@/services/listings";
import type { OwnListing } from "@/types/listing";

type ViewState =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; message: string }
  | { status: "ready"; own: OwnListing };

function BackLink() {
  return (
    <Link
      href="/accommodation/mine"
      className="text-muted hover:text-foreground -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
    >
      <ArrowLeft aria-hidden="true" className="size-4" />
      My listings
    </Link>
  );
}

/** A sentence that says, plainly, where the listing stands. */
function statusSummary(own: OwnListing): string {
  if (own.lifecycleStatus === "DRAFT") {
    return "A private draft. Nobody else can see it until you submit it and Roomie approves it.";
  }
  if (own.lifecycleStatus === "CLOSED") {
    return "Closed. It is no longer shown to anyone.";
  }
  if (own.moderationStatus === "SUSPENDED") {
    return "Suspended by Roomie and hidden from students.";
  }
  if (own.moderationStatus === "REJECTED") {
    return "Not approved. Fix what the reviewer asked for, then submit again.";
  }
  if (own.moderationStatus === "PENDING") {
    return "Waiting for review. It stays hidden until Roomie approves it.";
  }
  if (own.lifecycleStatus === "FILLED") {
    return "Marked as filled, so it is hidden from browsing.";
  }
  return own.isPublic
    ? "Approved and visible to signed-in students."
    : "Approved, but hidden for now: for example because the society left the directory or a tenancy has ended.";
}

function HistoryList({ own }: { own: OwnListing }) {
  if (own.history.length === 0) {
    return null;
  }
  return (
    <Card>
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <History aria-hidden="true" className="text-subtle size-5" />
        History
      </h2>
      <ol className="border-border mt-4 space-y-4 border-l pl-4">
        {[...own.history].reverse().map((event, index) => (
          <li key={`${event.at}-${index}`} className="text-sm">
            <p className="text-subtle text-xs">
              {formatTimestampDate(event.at)}
            </p>
            <p className="text-foreground font-medium">{event.summary}</p>
            {event.note && (
              <p className="text-muted mt-0.5 leading-relaxed">{event.note}</p>
            )}
          </li>
        ))}
      </ol>
    </Card>
  );
}

/**
 * Everything about one of your own listings: where it is in review and
 * why, what is still needed, evidence, photos, interested students, and
 * filling or closing it. Review statuses can only be changed by Roomie.
 */
export function ManageListing({ id }: { id: string }) {
  const router = useRouter();
  const { account } = useSession();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<{
    key: string;
    state: ViewState;
  } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{
    tone: "success" | "danger";
    text: string;
  } | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const key = `${id}|${attempt}`;

  useEffect(() => {
    const controller = new AbortController();
    fetchMyListing(id, controller.signal)
      .then((own) => setResult({ key, state: { status: "ready", own } }))
      .catch((error: unknown) => {
        if (controller.signal.aborted) {
          return;
        }
        const missing =
          error instanceof ApiError &&
          (error.status === 404 || error.status === 422);
        setResult({
          key,
          state: missing
            ? { status: "missing" }
            : { status: "error", message: describeApiError(error) },
        });
      });
    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const state: ViewState =
    result?.key === key ? result.state : { status: "loading" };

  if (state.status === "loading") {
    return <PageSkeleton />;
  }
  if (state.status === "missing") {
    return (
      <div className="mx-auto max-w-md">
        <BackLink />
        <EmptyState
          icon={Building2}
          title="Listing not found"
          description="It may have been deleted, or the link may be wrong."
          action={
            <ButtonLink href="/accommodation/mine">My listings</ButtonLink>
          }
          className="mt-4"
        />
      </div>
    );
  }
  if (state.status === "error") {
    return (
      <ErrorState
        title="This listing could not load"
        description={state.message}
        onRetry={() => setAttempt((value) => value + 1)}
        className="mx-auto max-w-md"
      />
    );
  }

  const own = state.own;
  const { listing } = own;
  const isProperty = listing.type === "EXISTING_ACCOMMODATION";
  const setOwn = (next: OwnListing) =>
    setResult({ key, state: { status: "ready", own: next } });
  // Refresh in place, keeping the page (and any message) on screen.
  const reload = () => {
    fetchMyListing(listing.id)
      .then(setOwn)
      .catch(() => undefined);
  };

  async function act(
    name: string,
    action: () => Promise<OwnListing>,
    success: string,
  ) {
    setBusy(name);
    setNotice(null);
    try {
      setOwn(await action());
      setNotice({ tone: "success", text: success });
    } catch (error) {
      setNotice({ tone: "danger", text: describeApiError(error) });
    } finally {
      setBusy(null);
    }
  }

  async function removeDraft() {
    setBusy("delete");
    try {
      await deleteDraft(listing.id);
      router.push("/accommodation/mine");
    } catch (error) {
      setConfirmDelete(false);
      setNotice({ tone: "danger", text: describeApiError(error) });
      setBusy(null);
    }
  }

  const isDraft = own.lifecycleStatus === "DRAFT";
  const neverSubmitted =
    isDraft && !own.history.some((event) => event.kind === "moderation");
  const showSubmit = own.canSubmit || own.submissionRequirements.length > 0;
  const lifecycleActions: Array<{
    status: "ACTIVE" | "FILLED" | "CLOSED";
    label: string;
    success: string;
  }> = [];
  if (own.moderationStatus !== "SUSPENDED") {
    if (own.lifecycleStatus === "ACTIVE") {
      lifecycleActions.push({
        status: "FILLED",
        label: "Mark as filled",
        success: "Marked as filled. It is no longer shown to students.",
      });
    }
    if (own.lifecycleStatus === "FILLED") {
      lifecycleActions.push({
        status: "ACTIVE",
        label: "Reopen",
        success: "Reopened.",
      });
    }
  }
  if (own.lifecycleStatus !== "CLOSED" && !neverSubmitted) {
    lifecycleActions.push({
      status: "CLOSED",
      label: "Close listing",
      success: "Closed. It will not be shown again.",
    });
  }

  return (
    <div>
      <div className="mb-4">
        <BackLink />
      </div>

      <div className="mb-6 space-y-3">
        <ListingStatusBadges
          lifecycle={own.lifecycleStatus}
          moderation={own.moderationStatus}
          isPublic={own.isPublic}
        />
        <h1 className="text-2xl font-semibold">{listing.title}</h1>
        <p className="text-muted text-sm leading-relaxed">
          {statusSummary(own)}
        </p>
        <div className="flex flex-wrap gap-3">
          {own.canEdit && (
            <ButtonLink
              href={`/accommodation/mine/${listing.id}/edit`}
              variant="secondary"
              size="sm"
            >
              <Pencil aria-hidden="true" className="size-4" />
              Edit details
            </ButtonLink>
          )}
          {own.isPublic && (
            <ButtonLink
              href={`/accommodation/${listing.id}`}
              variant="ghost"
              size="sm"
            >
              <ExternalLink aria-hidden="true" className="size-4" />
              View as students see it
            </ButtonLink>
          )}
        </div>
      </div>

      {own.moderationReason && (
        <Alert
          tone="danger"
          title={
            own.moderationStatus === "SUSPENDED"
              ? "Why it was suspended"
              : "Why it was not approved"
          }
          className="mb-5"
        >
          {own.moderationReason}
        </Alert>
      )}
      {notice && (
        <Alert
          tone={notice.tone}
          role={notice.tone === "danger" ? "alert" : "status"}
          className="mb-5"
        >
          {notice.text}
        </Alert>
      )}

      <div className="grid gap-5 lg:grid-cols-3 lg:items-start">
        <div className="space-y-5 lg:col-span-2">
          {showSubmit && (
            <Card>
              <h2 className="flex items-center gap-2 text-lg font-semibold">
                <ListChecks aria-hidden="true" className="text-subtle size-5" />
                {own.submissionRequirements.length > 0
                  ? "Before you can submit"
                  : "Ready to submit"}
              </h2>
              {own.submissionRequirements.length > 0 ? (
                <ul className="text-foreground mt-3 list-disc space-y-1.5 pl-5 text-sm">
                  {own.submissionRequirements.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-muted mt-2 flex items-start gap-2 text-sm">
                  <CircleCheck
                    aria-hidden="true"
                    className="text-success mt-0.5 size-4 shrink-0"
                  />
                  Everything Roomie needs is here. A reviewer checks it before
                  it goes live; nothing is approved automatically.
                </p>
              )}
              <Button
                className="mt-4"
                disabled={!own.canSubmit}
                isLoading={busy === "submit"}
                onClick={() =>
                  void act(
                    "submit",
                    () => submitForReview(listing.id),
                    "Submitted. You will get a notification when it has been reviewed.",
                  )
                }
              >
                <Send aria-hidden="true" className="size-4" />
                {isDraft ? "Submit for review" : "Resubmit for review"}
              </Button>
            </Card>
          )}

          {isProperty && own.authority && (
            <AuthorityEvidence
              listingId={listing.id}
              creatorType={listing.creatorType}
              authority={own.authority}
              identityApproved={
                account.verifications.identity.status === "APPROVED"
              }
              canUpload={own.canEdit}
              onUploaded={reload}
            />
          )}

          {isProperty && <ListingPhotoManager own={own} onChange={setOwn} />}

          {!isDraft && <InterestedStudents listingId={listing.id} />}

          <HistoryList own={own} />
        </div>

        <div className="space-y-5">
          <div>
            <h2 className="text-subtle mb-2 text-sm font-medium">
              How students will see it
            </h2>
            <ListingCard listing={listing} />
          </div>

          {(lifecycleActions.length > 0 || neverSubmitted) && (
            <Card>
              <h2 className="text-lg font-semibold">Listing status</h2>
              <p className="text-muted mt-1 text-sm">
                Filling or closing never changes Roomie&apos;s review.
              </p>
              <div className="mt-4 flex flex-col gap-2">
                {lifecycleActions.map((action) => (
                  <Button
                    key={action.status}
                    variant={action.status === "CLOSED" ? "ghost" : "secondary"}
                    isLoading={busy === action.status}
                    disabled={busy !== null}
                    onClick={() =>
                      void act(
                        action.status,
                        () => changeLifecycle(listing.id, action.status),
                        action.success,
                      )
                    }
                  >
                    {action.label}
                  </Button>
                ))}
                {neverSubmitted && (
                  <Button
                    variant="ghost"
                    onClick={() => setConfirmDelete(true)}
                    disabled={busy !== null}
                  >
                    <Trash2 aria-hidden="true" className="size-4" />
                    Delete draft
                  </Button>
                )}
              </div>
            </Card>
          )}
        </div>
      </div>

      <Dialog
        isOpen={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        title="Delete this draft?"
      >
        <p className="text-muted text-sm leading-relaxed">
          The draft and its photos are deleted permanently. This cannot be
          undone.
        </p>
        <div className="mt-5 flex justify-end gap-3">
          <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
            Keep it
          </Button>
          <Button
            variant="danger"
            onClick={() => void removeDraft()}
            isLoading={busy === "delete"}
          >
            Delete draft
          </Button>
        </div>
      </Dialog>
    </div>
  );
}
