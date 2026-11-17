"use client";

import { FileText } from "lucide-react";
import { useState, type FormEvent, type ReactNode } from "react";

import { useSession } from "@/components/session/session-provider";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { FileField } from "@/components/ui/file-field";
import { SelectField } from "@/components/ui/select-field";
import { TextField } from "@/components/ui/text-field";
import { OWN_VERIFICATION_TEXT } from "@/lib/account-display";
import {
  documentDownloadUrl,
  submitIdentityDocument,
  submitStudentDocument,
} from "@/services/account";
import { describeApiError } from "@/services/api-client";
import type {
  OwnVerification,
  VerificationDocumentType,
} from "@/types/account";

// These limits are repeated by the backend, which is the real check. Here
// they only save someone from waiting for an upload that would be refused.
const MAX_FILE_BYTES = 5 * 1024 * 1024;
const ACCEPTED_TYPES = ["application/pdf", "image/jpeg", "image/png"];
const ACCEPT_ATTRIBUTE = ".pdf,.jpg,.jpeg,.png";
const FILE_HINT = "PDF, JPEG or PNG, up to 5 MB.";

const DOCUMENT_LABELS: Record<VerificationDocumentType, string> = {
  GOVERNMENT_ID: "Government ID",
  STUDENT_ID: "Student ID card",
  ENROLMENT_PROOF: "Proof of enrolment",
  OWNERSHIP_PROOF: "Proof of ownership",
  RENTAL_AGREEMENT: "Rental agreement",
  LANDLORD_PERMISSION: "Landlord's permission",
  OWNER_AUTHORIZATION: "Owner's authorisation",
};

const STATUS_NOTES: Record<OwnVerification["status"], string> = {
  NOT_SUBMITTED: "Nothing has been submitted yet.",
  PENDING:
    "Your documents are waiting for a person to review them. You can add another document if you need to.",
  APPROVED: "This check is complete.",
  REJECTED:
    "This was not approved. You can submit a different document to be reviewed again.",
  NEEDS_RESUBMISSION:
    "The reviewer needs a clearer or different document. Please submit one to be reviewed again.",
};

function fileProblem(file: File | null): string | undefined {
  if (!file) {
    return "Choose a file to upload.";
  }
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return "Choose a PDF, JPEG or PNG file.";
  }
  if (file.size > MAX_FILE_BYTES) {
    return "This file is larger than 5 MB.";
  }
  return undefined;
}

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

interface VerificationCardProps {
  title: string;
  /** What this check confirms, in one sentence. */
  description: string;
  verification: OwnVerification;
  /** The form's extra fields (besides the file itself). */
  children?: (showErrors: boolean) => ReactNode;
  /** Problems with the extra fields; a non-empty list blocks the upload. */
  extraProblems?: string[];
  onUpload: (file: File) => Promise<unknown>;
}

function VerificationCard({
  title,
  description,
  verification,
  children,
  extraProblems = [],
  onUpload,
}: VerificationCardProps) {
  const { refreshAccount } = useSession();
  const [file, setFile] = useState<File | null>(null);
  const [showErrors, setShowErrors] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [justUploaded, setJustUploaded] = useState(false);
  const [resetKey, setResetKey] = useState(0);

  const { label, tone } = OWN_VERIFICATION_TEXT[verification.status];
  const canUpload = verification.status !== "APPROVED";
  const problem = fileProblem(file);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowErrors(true);
    setJustUploaded(false);
    if (problem || extraProblems.length > 0 || !file || isUploading) {
      return;
    }
    setIsUploading(true);
    setUploadError(null);
    try {
      await onUpload(file);
      await refreshAccount();
      setFile(null);
      setShowErrors(false);
      setResetKey((current) => current + 1);
      setJustUploaded(true);
    } catch (error) {
      setUploadError(describeApiError(error));
    } finally {
      setIsUploading(false);
    }
  }

  return (
    <Card padding="lg">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-lg font-semibold">{title}</h2>
        <Badge tone={tone}>{label}</Badge>
      </div>
      <p className="text-muted mt-1 text-sm leading-relaxed">{description}</p>
      <p className="text-foreground mt-3 text-sm leading-relaxed">
        {STATUS_NOTES[verification.status]}
      </p>

      {verification.documents.length > 0 && (
        <ul
          aria-label={`${title} documents you have uploaded`}
          className="border-border divide-border rounded-control mt-4 divide-y border"
        >
          {verification.documents.map((document) => (
            <li
              key={document.id}
              className="flex items-center gap-3 px-3.5 py-3"
            >
              <FileText
                aria-hidden="true"
                className="text-subtle size-5 shrink-0"
              />
              <span className="min-w-0 flex-1">
                <span className="text-foreground block truncate text-sm font-medium">
                  {document.originalFilename ?? "Document"}
                </span>
                <span className="text-subtle block text-xs">
                  {DOCUMENT_LABELS[document.documentType]} ·{" "}
                  {formatSize(document.sizeBytes)}
                </span>
              </span>
              {/* Only you and Roomie's administrators can open this. */}
              <a
                href={documentDownloadUrl(document.id)}
                className="text-primary hover:text-primary-hover shrink-0 py-2 text-sm font-medium underline-offset-4 hover:underline"
              >
                Download
              </a>
            </li>
          ))}
        </ul>
      )}

      {canUpload && (
        <form
          // "post" keeps the form out of the page address if the browser
          // ever sends it itself, before the page is ready.
          method="post"
          noValidate
          onSubmit={(event) => void handleSubmit(event)}
          className="mt-5 space-y-2"
        >
          {children?.(showErrors)}
          <FileField
            label="Document"
            name="file"
            accept={ACCEPT_ATTRIBUTE}
            onChange={(chosen) => {
              setFile(chosen);
              setUploadError(null);
              setJustUploaded(false);
            }}
            hint={FILE_HINT}
            error={showErrors ? problem : undefined}
            resetKey={resetKey}
          />
          {uploadError && (
            <Alert tone="danger" role="alert" title="The upload did not work">
              {uploadError}
            </Alert>
          )}
          {justUploaded && (
            <Alert tone="success" role="status" title="Document received">
              It is now waiting for review. Uploading does not verify you
              automatically.
            </Alert>
          )}
          <Button type="submit" isLoading={isUploading}>
            Upload for review
          </Button>
        </form>
      )}
    </Card>
  );
}

const STUDENT_DOCUMENT_OPTIONS = [
  { value: "STUDENT_ID", label: DOCUMENT_LABELS.STUDENT_ID },
  { value: "ENROLMENT_PROOF", label: DOCUMENT_LABELS.ENROLMENT_PROOF },
];

/**
 * Where a person submits evidence for the two checks that belong to them.
 *
 * Identity and student status are separate: each has its own documents,
 * its own review and its own result. (Listing authority, the third check,
 * belongs to a listing and is submitted from the listing once listings
 * can be created.)
 */
export function VerificationCenter() {
  const { account } = useSession();
  const { identity, student } = account.verifications;
  const [institution, setInstitution] = useState(
    account.profile?.collegeName ?? "",
  );
  const [documentType, setDocumentType] =
    useState<VerificationDocumentType>("STUDENT_ID");
  const institutionProblem = institution.trim()
    ? undefined
    : "Enter your college or university.";

  return (
    <div className="space-y-5">
      <Alert tone="info" title="How verification works">
        A person at Roomie reviews every document. Nothing is approved
        automatically, and a valid-looking file is not treated as proof by
        itself. Your documents are private: only you and authorised
        administrators can open them.
      </Alert>

      <VerificationCard
        title="Identity"
        description="Confirms that you are who you say you are. Upload a government-issued photo ID."
        verification={identity}
        onUpload={submitIdentityDocument}
      />

      <VerificationCard
        title="Student status"
        description="Confirms that you are currently enrolled at a college or university. This is separate from identity."
        verification={student}
        extraProblems={institutionProblem ? [institutionProblem] : []}
        onUpload={(file) =>
          submitStudentDocument(file, institution.trim(), documentType)
        }
      >
        {(showErrors) => (
          <>
            <TextField
              label="College or university"
              name="institution"
              value={institution}
              onChange={(event) => setInstitution(event.target.value)}
              error={showErrors ? institutionProblem : undefined}
            />
            <SelectField
              label="Kind of document"
              name="documentType"
              options={STUDENT_DOCUMENT_OPTIONS}
              value={documentType}
              onChange={(event) =>
                setDocumentType(event.target.value as VerificationDocumentType)
              }
            />
          </>
        )}
      </VerificationCard>
    </div>
  );
}
