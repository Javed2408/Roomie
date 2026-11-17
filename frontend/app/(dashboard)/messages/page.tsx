import { MessageCircle } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";

import { PageHeader } from "@/components/app-shell/page-header";
import { Avatar } from "@/components/ui/avatar";
import { ButtonLink } from "@/components/ui/button";
import { SampleDataBadge } from "@/components/ui/sample-data-badge";
import { EmptyState } from "@/components/ui/states";
import { formatDateTime } from "@/lib/format";
import { CONVERSATIONS } from "@/lib/mock/matches";

export const metadata: Metadata = { title: "Messages" };

export default function MessagesPage() {
  return (
    <>
      <PageHeader
        title="Messages"
        description="Private conversations with your matches."
        aside={<SampleDataBadge />}
      />

      {CONVERSATIONS.length === 0 ? (
        <EmptyState
          icon={MessageCircle}
          title="No conversations yet"
          description="You can message someone once you have matched with them. Conversations will appear here."
          action={<ButtonLink href="/matches">View matches</ButtonLink>}
        />
      ) : (
        <ul className="border-border bg-surface divide-border rounded-card mx-auto max-w-2xl divide-y overflow-hidden border">
          {CONVERSATIONS.map((conversation) => {
            const { profile } = conversation.match.candidate;
            const lastMessage = conversation.messages.at(-1);
            return (
              <li key={conversation.id}>
                <Link
                  href={`/messages/${conversation.id}`}
                  className="hover:bg-surface-muted flex items-center gap-4 px-4 py-4 transition-colors duration-150"
                >
                  <Avatar name={profile.fullName} />
                  <span className="min-w-0 flex-1">
                    <span className="flex items-baseline justify-between gap-3">
                      <span className="text-foreground truncate font-medium">
                        {profile.fullName}
                      </span>
                      {lastMessage && (
                        <span className="text-subtle shrink-0 text-xs">
                          {formatDateTime(lastMessage.sentAt)}
                        </span>
                      )}
                    </span>
                    <span className="text-muted block truncate text-sm">
                      {lastMessage
                        ? `${lastMessage.sender === "me" ? "You: " : ""}${lastMessage.content}`
                        : "You matched. Say hello!"}
                    </span>
                  </span>
                  {conversation.unreadCount > 0 && (
                    <span className="bg-primary text-on-primary flex h-6 min-w-6 shrink-0 items-center justify-center rounded-full px-1.5 text-xs font-semibold">
                      {conversation.unreadCount}
                      <span className="sr-only"> unread</span>
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}
