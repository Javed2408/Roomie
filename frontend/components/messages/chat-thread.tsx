"use client";

import { Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { formatDateTime, toLocalDateTime } from "@/lib/format";
import { MESSAGE_MAX_LENGTH, type Message } from "@/types/match";

interface ChatThreadProps {
  /** The other person's first name, used in labels. */
  recipientName: string;
  initialMessages: Message[];
}

/**
 * The message list and the box for writing a new message.
 *
 * Phase 1 shell: a sent message is added to this component's memory only.
 * It is not stored or delivered, and disappears on refresh. Persistent,
 * real-time messaging over WebSockets is built in roadmap Phase 7.
 */
export function ChatThread({
  recipientName,
  initialMessages,
}: ChatThreadProps) {
  const [messages, setMessages] = useState(initialMessages);
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const sentCount = messages.length - initialMessages.length;

  // Keep the newest message in view after sending.
  useEffect(() => {
    if (sentCount > 0) {
      endRef.current?.scrollIntoView({ block: "nearest" });
    }
  }, [sentCount]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const content = draft.trim();
    if (!content) {
      setError("Write a message first.");
      return;
    }
    if (content.length > MESSAGE_MAX_LENGTH) {
      setError(`Keep messages under ${MESSAGE_MAX_LENGTH} characters.`);
      return;
    }
    setMessages((current) => [
      ...current,
      {
        id: `local-${current.length + 1}`,
        sender: "me",
        content,
        sentAt: toLocalDateTime(new Date()),
      },
    ]);
    setDraft("");
    setError(null);
  }

  return (
    <>
      <div className="flex-1 space-y-3 px-4 py-5">
        {messages.length === 0 && (
          <p className="text-muted py-8 text-center text-sm leading-relaxed">
            You and {recipientName} matched. Say hello and compare what you are
            each looking for.
          </p>
        )}
        <ol aria-label="Messages" className="space-y-3">
          {messages.map((message) => {
            const isMine = message.sender === "me";
            return (
              <li
                key={message.id}
                className={cn(
                  "flex flex-col",
                  isMine ? "items-end" : "items-start",
                )}
              >
                <p
                  className={cn(
                    "max-w-[85%] rounded-2xl px-4 py-2.5 text-[0.9375rem] leading-relaxed break-words whitespace-pre-wrap",
                    isMine
                      ? "bg-primary text-on-primary rounded-br-md"
                      : "bg-surface-muted text-foreground rounded-bl-md",
                  )}
                >
                  <span className="sr-only">
                    {isMine ? "You: " : `${recipientName}: `}
                  </span>
                  {message.content}
                </p>
                <span className="text-subtle mt-1 px-1 text-xs">
                  {formatDateTime(message.sentAt)}
                </span>
              </li>
            );
          })}
        </ol>
        <div ref={endRef} />
      </div>

      <form
        // "post" keeps what was typed out of the page address if the browser
        // ever sends this form itself, before the page is ready.
        method="post"
        noValidate
        onSubmit={handleSubmit}
        className="border-border border-t px-4 pt-3 pb-4"
      >
        <div className="flex items-end gap-2">
          <label htmlFor="chat-draft" className="sr-only">
            Message {recipientName}
          </label>
          <input
            id="chat-draft"
            name="message"
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setError(null);
            }}
            autoComplete="off"
            placeholder="Write a message"
            aria-invalid={error ? true : undefined}
            aria-describedby="chat-draft-message"
            className="rounded-control bg-surface text-foreground placeholder:text-subtle border-border-strong hover:border-foreground h-11 min-w-0 flex-1 border px-3.5 text-base transition-colors duration-150"
          />
          <Button type="submit" aria-label="Send message" className="px-4">
            <Send aria-hidden="true" className="size-5" />
          </Button>
        </div>
        <p
          id="chat-draft-message"
          role="status"
          className={cn(
            "mt-1.5 min-h-5 text-sm",
            error ? "text-danger" : "text-subtle",
          )}
        >
          {error ?? "Preview: messages are not saved or delivered."}
        </p>
      </form>
    </>
  );
}
