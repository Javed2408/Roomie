import { ArrowLeft } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { PageSkeleton } from "@/components/app-shell/page-skeleton";

import { ChatThread } from "@/components/messages/chat-thread";
import { SafetyActions } from "@/components/safety/safety-actions";
import { Avatar } from "@/components/ui/avatar";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { CONVERSATIONS } from "@/lib/mock/matches";

export const metadata: Metadata = { title: "Conversation" };

/** Lists the conversations that exist, so their pages can be pre-built. */
export function generateStaticParams() {
  return CONVERSATIONS.map((conversation) => ({ id: conversation.id }));
}

/**
 * One conversation. In the real app the backend checks, on every read and
 * write, that the signed-in student is a participant of an active match.
 */
export default function ConversationPage({
  params,
}: PageProps<"/messages/[id]">) {
  return (
    <Suspense fallback={<PageSkeleton />}>
      {params.then(({ id }) => (
        <ConversationView id={id} />
      ))}
    </Suspense>
  );
}

/*
 * The id comes from the page address, which is only known when someone
 * actually visits. Next.js asks for that to happen inside <Suspense>, so
 * the page frame can appear instantly with a placeholder while the id is
 * read. params.then(...) hands the id to the real content once ready.
 */
function ConversationView({ id }: { id: string }) {
  const conversation = CONVERSATIONS.find((item) => item.id === id);
  if (!conversation) {
    notFound();
  }
  const { profile } = conversation.match.candidate;
  const firstName = profile.fullName.split(" ")[0] ?? profile.fullName;

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Link
          href="/messages"
          className="text-muted hover:text-foreground -ml-2 inline-flex h-10 items-center gap-1.5 rounded-lg px-2 text-sm font-medium transition-colors duration-150"
        >
          <ArrowLeft aria-hidden="true" className="size-4" />
          All messages
        </Link>
        <SampleDataBadge />
      </div>

      <section className="border-border bg-surface rounded-card flex min-h-[28rem] flex-col border">
        <header className="border-border flex flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <div className="flex min-w-0 items-center gap-3">
            <Avatar name={profile.fullName} />
            <div className="min-w-0">
              <h1 className="truncate text-lg font-semibold">
                {profile.fullName}
              </h1>
              <Link
                href={`/students/${profile.id}`}
                className="text-primary hover:text-primary-hover text-sm font-medium underline-offset-4 hover:underline"
              >
                View profile
              </Link>
            </div>
          </div>
          <SafetyActions targetName={profile.fullName} kind="person" />
        </header>

        <ChatThread
          recipientName={firstName}
          initialMessages={conversation.messages}
        />
      </section>
    </div>
  );
}
