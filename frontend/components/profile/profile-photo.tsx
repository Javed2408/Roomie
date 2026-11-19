"use client";

import { Camera, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { useSession } from "@/components/session/session-provider";
import { Button } from "@/components/ui/button";
import { describeApiError } from "@/services/api-client";
import { removeProfilePhoto, uploadProfilePhoto } from "@/services/account";

/**
 * Add, replace or remove your profile photo. It is shown wherever your
 * profile is shown, and to nobody who cannot see your profile.
 */
export function ProfilePhotoControls({ hasPhoto }: { hasPhoto: boolean }) {
  const { setAccount } = useSession();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState<"upload" | "remove" | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function run(kind: "upload" | "remove", action: () => Promise<void>) {
    setBusy(kind);
    setError(null);
    try {
      await action();
    } catch (problem) {
      setError(describeApiError(problem));
    } finally {
      setBusy(null);
    }
  }

  function chosen(file: File | undefined) {
    if (inputRef.current) {
      inputRef.current.value = "";
    }
    if (file) {
      void run("upload", async () =>
        setAccount(await uploadProfilePhoto(file)),
      );
    }
  }

  return (
    <div className="mt-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="sr-only"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(event) => chosen(event.target.files?.[0])}
      />
      <div className="flex flex-wrap gap-2">
        <Button
          size="sm"
          variant="secondary"
          onClick={() => inputRef.current?.click()}
          isLoading={busy === "upload"}
          disabled={busy !== null}
        >
          <Camera aria-hidden="true" className="size-4" />
          {hasPhoto ? "Change photo" : "Add a photo"}
        </Button>
        {hasPhoto && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() =>
              void run("remove", async () =>
                setAccount(await removeProfilePhoto()),
              )
            }
            isLoading={busy === "remove"}
            disabled={busy !== null}
          >
            <Trash2 aria-hidden="true" className="size-4" />
            Remove
          </Button>
        )}
      </div>
      <p className="text-subtle mt-2 text-xs">
        JPEG, PNG or WebP. Cropped square; location details are removed.
      </p>
      {error && (
        <p role="alert" className="text-danger mt-2 text-sm">
          {error}
        </p>
      )}
    </div>
  );
}
