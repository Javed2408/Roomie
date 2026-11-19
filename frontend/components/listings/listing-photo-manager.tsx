"use client";

import { ImagePlus, Trash2 } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FileField } from "@/components/ui/file-field";
import { describeApiError } from "@/services/api-client";
import { addListingPhoto, removeListingPhoto } from "@/services/listings";
import type { OwnListing } from "@/types/listing";

/**
 * Add and remove a listing's photos. The backend checks each file really
 * is an image, removes location and camera details, and stores a cleaned
 * copy that only people allowed to see the listing can load.
 */
export function ListingPhotoManager({
  own,
  onChange,
}: {
  own: OwnListing;
  onChange: (own: OwnListing) => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [resetKey, setResetKey] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const { listing } = own;

  async function run(id: string, action: () => Promise<OwnListing>) {
    setBusy(id);
    setError(null);
    try {
      onChange(await action());
      return true;
    } catch (problem) {
      setError(describeApiError(problem));
      return false;
    } finally {
      setBusy(null);
    }
  }

  async function upload() {
    if (!file) {
      setError("Choose a photo first.");
      return;
    }
    if (await run("upload", () => addListingPhoto(listing.id, file))) {
      setFile(null);
      setResetKey((value) => value + 1);
    }
  }

  return (
    <Card>
      <h2 className="text-lg font-semibold">Photos</h2>
      <p className="text-muted mt-1 text-sm leading-relaxed">
        Show the rooms and shared spaces. Avoid anything that reveals the flat
        number or exact address. Location details inside photos are removed
        automatically.
        {own.moderationStatus === "APPROVED" &&
          " Changing photos on a live listing sends it back for review."}
      </p>

      {listing.photos.length > 0 && (
        <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">
          {listing.photos.map((photo, index) => (
            <li
              key={photo.id}
              className="bg-surface-muted relative aspect-[4/3] overflow-hidden rounded-lg"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={photo.url}
                alt={`Photo ${index + 1}`}
                className="size-full object-cover"
              />
              {index === 0 && (
                <span className="absolute top-2 left-2 rounded-full bg-black/60 px-2 py-0.5 text-xs text-white">
                  Cover
                </span>
              )}
              {own.canEdit && (
                <Button
                  size="sm"
                  variant="secondary"
                  className="absolute right-2 bottom-2"
                  aria-label={`Remove photo ${index + 1}`}
                  isLoading={busy === photo.id}
                  disabled={busy !== null}
                  onClick={() =>
                    void run(photo.id, () =>
                      removeListingPhoto(listing.id, photo.id),
                    )
                  }
                >
                  <Trash2 aria-hidden="true" className="size-4" />
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}

      {own.canEdit && (
        <div className="mt-4 space-y-2">
          <FileField
            label="Add a photo"
            name="photo"
            accept="image/jpeg,image/png,image/webp"
            onChange={setFile}
            hint="JPEG, PNG or WebP. Large photos are resized."
            resetKey={resetKey}
          />
          <Button
            variant="secondary"
            onClick={() => void upload()}
            isLoading={busy === "upload"}
            disabled={busy !== null}
          >
            <ImagePlus aria-hidden="true" className="size-4" />
            Upload photo
          </Button>
        </div>
      )}
      {error && (
        <Alert tone="danger" role="alert" className="mt-3">
          {error}
        </Alert>
      )}
    </Card>
  );
}
