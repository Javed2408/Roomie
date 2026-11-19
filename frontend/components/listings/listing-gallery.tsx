"use client";

import { ChevronLeft, ChevronRight, ImageOff } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/cn";
import type { ListingPhoto } from "@/types/listing";

/**
 * A listing's photos: one large, with thumbnails to switch between them.
 * Every address is an API path that checks, on each request, that the
 * viewer may see this listing.
 */
export function ListingGallery({
  photos,
  title,
}: {
  photos: ListingPhoto[];
  title: string;
}) {
  const [index, setIndex] = useState(0);
  const current = photos[Math.min(index, photos.length - 1)];

  if (!current) {
    return (
      <div className="rounded-card bg-surface-muted text-subtle flex aspect-[16/9] flex-col items-center justify-center gap-2">
        <ImageOff aria-hidden="true" className="size-8" />
        <span className="text-sm">No photos yet</span>
      </div>
    );
  }

  const go = (step: number) =>
    setIndex((value) => (value + step + photos.length) % photos.length);

  return (
    <div className="space-y-3">
      <div className="rounded-card bg-surface-muted relative aspect-[16/9] overflow-hidden">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={current.url}
          alt={`Photo ${index + 1} of ${photos.length}: ${title}`}
          className="size-full object-cover"
        />
        {photos.length > 1 && (
          <>
            <button
              type="button"
              onClick={() => go(-1)}
              aria-label="Previous photo"
              className="absolute top-1/2 left-3 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/55 text-white transition-colors hover:bg-black/75"
            >
              <ChevronLeft aria-hidden="true" className="size-5" />
            </button>
            <button
              type="button"
              onClick={() => go(1)}
              aria-label="Next photo"
              className="absolute top-1/2 right-3 flex size-10 -translate-y-1/2 items-center justify-center rounded-full bg-black/55 text-white transition-colors hover:bg-black/75"
            >
              <ChevronRight aria-hidden="true" className="size-5" />
            </button>
            <span className="absolute right-3 bottom-3 rounded-full bg-black/60 px-2.5 py-1 text-xs text-white">
              {index + 1} / {photos.length}
            </span>
          </>
        )}
      </div>
      {photos.length > 1 && (
        <ul className="flex gap-2 overflow-x-auto pb-1">
          {photos.map((photo, position) => (
            <li key={photo.id} className="shrink-0">
              <button
                type="button"
                onClick={() => setIndex(position)}
                aria-label={`Show photo ${position + 1}`}
                aria-current={position === index ? "true" : undefined}
                className={cn(
                  "block size-16 overflow-hidden rounded-lg border-2 transition-colors sm:size-20",
                  position === index
                    ? "border-primary"
                    : "hover:border-border-strong border-transparent",
                )}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={photo.url}
                  alt=""
                  loading="lazy"
                  className="size-full object-cover"
                />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
