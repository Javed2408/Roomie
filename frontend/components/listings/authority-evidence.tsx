"use client";

import { FileCheck2, ShieldAlert, ShieldCheck, Upload } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button, ButtonLink } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FileField } from "@/components/ui/file-field";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { describeApiError } from "@/services/api-client";
import { submitAuthorityEvidence } from "@/services/listings";
import type { VerificationDocumentType } from "@/types/account";
import type { ListingCreatorType, OwnAuthority } from "@/types/listing";

const DOCUMENT_LABELS: Partial<Record<VerificationDocumentType, string>> = {
  OWNERSHIP_PROOF: "Proof of ownership",
  RENTAL_AGREEMENT: "Rental agreement",
  LANDLORD_PERMISSION: "Landlord's written permission to share",
  OWNER_AUTHORIZATION: "Owner's written authorisation",
};

/** What each kind of creator uploads. The first is the required one. */
const DOCUMENTS_FOR: Record<ListingCreatorType, VerificationDocumentType[]> = {
  PROPERTY_OWNER: ["OWNERSHIP_PROOF"],
  EXISTING_TENANT: ["RENTAL_AGREEMENT", "LANDLORD_PERMISSION"],
  AUTHORIZED_AGENT: ["OWNER_AUTHORIZATION"],
};

const GUIDANCE: Record<ListingCreatorType, string[]> = {
  PROPERTY_OWNER: [
    "A document showing you own the property, such as a sale deed, property tax receipt or society maintenance bill in your name.",
    "Your identity must also be verified, so Roomie knows the owner is really you.",
  ],
  EXISTING_TENANT: [
    "Your current rental agreement. It must still be running, and the property must match this listing.",
    "A rental agreement proves you rent the flat, not that you may take someone in. If it does not allow sharing or subletting, also upload your landlord's written permission.",
  ],
  AUTHORIZED_AGENT: [
    "The owner's written authorisation for you to offer this property.",
    "The owner's name and phone number or email. Roomie contacts the owner directly to confirm. Your own declaration is not enough.",
    "Your identity must also be verified.",
  ],
};

const STATUS_TEXT: Record<OwnAuthority["status"], string> = {
  NOT_SUBMITTED: "No evidence yet",
  PENDING: "Waiting for review",
  APPROVED: "Verified by Roomie",
  REJECTED: "Not approved",
  NEEDS_RESUBMISSION: "More evidence needed",
};

const ACCEPT = ".pdf,.jpg,.jpeg,.png";

/**
 * Evidence of the right to offer one property (the "listing authority"
 * check). Uploading never verifies anything by itself: a Roomie reviewer
 * looks at the documents, and for agents also confirms with the owner.
 */
export function AuthorityEvidence({
  listingId,
  creatorType,
  authority,
  identityApproved,
  canUpload,
  onUploaded,
}: {
  listingId: string;
  creatorType: ListingCreatorType;
  authority: OwnAuthority;
  identityApproved: boolean;
  canUpload: boolean;
  onUploaded: () => void;
}) {
  const documentTypes = DOCUMENTS_FOR[creatorType];
  const [documentType, setDocumentType] = useState<VerificationDocumentType>(
    documentTypes[0] ?? "OWNERSHIP_PROOF",
  );
  const [file, setFile] = useState<File | null>(null);
  const [ownerName, setOwnerName] = useState("");
  const [ownerContact, setOwnerContact] = useState("");
  const [resetKey, setResetKey] = useState(0);
  const [isBusy, setIsBusy] = useState(false);
  const [message, setMessage] = useState<{
    tone: "success" | "danger";
    text: string;
  } | null>(null);

  const isAgent = creatorType === "AUTHORIZED_AGENT";
  const needsIdentity = creatorType !== "EXISTING_TENANT";
  const isApproved = authority.status === "APPROVED";

  async function upload() {
    if (!file) {
      setMessage({ tone: "danger", text: "Choose a file to upload." });
      return;
    }
    if (isAgent && (!ownerName.trim() || !ownerContact.trim())) {
      setMessage({
        tone: "danger",
        text: "Give the owner's name and contact so Roomie can confirm with them.",
      });
      return;
    }
    setIsBusy(true);
    setMessage(null);
    try {
      await submitAuthorityEvidence(
        listingId,
        file,
        documentType,
        isAgent
          ? { name: ownerName.trim(), contact: ownerContact.trim() }
          : undefined,
      );
      setFile(null);
      setResetKey((value) => value + 1);
      setMessage({
        tone: "success",
        text: "Uploaded. It stays private: only you and Roomie reviewers can open it.",
      });
      onUploaded();
    } catch (error) {
      setMessage({ tone: "danger", text: describeApiError(error) });
    } finally {
      setIsBusy(false);
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-lg font-semibold">Evidence of listing authority</h2>
        <Badge
          tone={
            isApproved
              ? "success"
              : authority.status === "PENDING"
                ? "warning"
                : authority.status === "NOT_SUBMITTED"
                  ? "neutral"
                  : "danger"
          }
        >
          {isApproved ? (
            <ShieldCheck aria-hidden="true" className="size-3.5" />
          ) : (
            <ShieldAlert aria-hidden="true" className="size-3.5" />
          )}
          {STATUS_TEXT[authority.status]}
        </Badge>
      </div>

      <ul className="text-muted mt-3 list-disc space-y-1.5 pl-5 text-sm leading-relaxed">
        {GUIDANCE[creatorType].map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>

      {authority.reason && (
        <Alert tone="danger" title="Reviewer's note" className="mt-4">
          {authority.reason}
        </Alert>
      )}
      {isAgent && authority.ownerConfirmation !== "NOT_REQUIRED" && (
        <p className="text-muted mt-3 text-sm">
          Owner confirmation:{" "}
          <span className="text-foreground font-medium">
            {
              {
                PENDING: "Roomie has not reached the owner yet",
                CONFIRMED: "the owner confirmed your authority",
                DENIED: "the owner did not confirm your authority",
              }[authority.ownerConfirmation]
            }
          </span>
        </p>
      )}
      {needsIdentity && !identityApproved && (
        <Alert tone="warning" className="mt-4">
          Your identity is not verified yet. It is checked separately from this
          evidence.
          <ButtonLink
            href="/profile/verification"
            size="sm"
            variant="secondary"
            className="mt-2"
          >
            Verify your identity
          </ButtonLink>
        </Alert>
      )}

      {authority.documents.length > 0 && (
        <div className="mt-4">
          <h3 className="text-subtle text-xs">Uploaded so far</h3>
          <ul className="mt-1.5 flex flex-wrap gap-1.5">
            {authority.documents.map((type) => (
              <li key={type}>
                <Badge>
                  <FileCheck2 aria-hidden="true" className="size-3.5" />
                  {DOCUMENT_LABELS[type as VerificationDocumentType] ?? type}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
      )}

      {canUpload && !isApproved && (
        <div className="border-border mt-5 space-y-2 border-t pt-5">
          {documentTypes.length > 1 && (
            <SelectField
              label="Document"
              options={documentTypes.map((type) => ({
                value: type,
                label: DOCUMENT_LABELS[type] ?? type,
              }))}
              value={documentType}
              onChange={(event) =>
                setDocumentType(event.target.value as VerificationDocumentType)
              }
            />
          )}
          <FileField
            label={
              documentTypes.length > 1
                ? "File"
                : (DOCUMENT_LABELS[documentType] ?? "File")
            }
            name="evidence"
            accept={ACCEPT}
            onChange={setFile}
            hint="PDF, JPEG or PNG. Kept private and never shown on your listing."
            resetKey={resetKey}
          />
          {isAgent && (
            <div className="grid gap-x-4 sm:grid-cols-2">
              <TextField
                label="Owner's name"
                value={ownerName}
                onChange={(event) => setOwnerName(event.target.value)}
                maxLength={120}
              />
              <TextField
                label="Owner's phone or email"
                value={ownerContact}
                onChange={(event) => setOwnerContact(event.target.value)}
                maxLength={255}
                hint="Used only by Roomie to confirm with the owner."
              />
            </div>
          )}
          <Button onClick={upload} isLoading={isBusy} variant="secondary">
            <Upload aria-hidden="true" className="size-4" />
            Upload evidence
          </Button>
        </div>
      )}

      {message && (
        <Alert
          tone={message.tone}
          role={message.tone === "danger" ? "alert" : "status"}
          className="mt-4"
        >
          {message.text}
        </Alert>
      )}
    </Card>
  );
}
