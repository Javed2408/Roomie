import path from "node:path";

/*
 * Addresses and folders used only by the browser tests.
 *
 * The tests run their own copy of the frontend and backend on different
 * ports, with their own database, so they never touch the servers or the
 * data you use for development.
 */

export const FRONTEND_PORT = 3100;
export const BACKEND_PORT = 8010;

export const FRONTEND_URL = `http://localhost:${FRONTEND_PORT}`;
export const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
export const API_URL = `${BACKEND_URL}/api/v1`;

/** A separate PostgreSQL database, created automatically. */
export const DATABASE_NAME = "roomie_e2e";

const TMP_DIR = path.resolve(__dirname, ".tmp");
/** Where the test backend writes its "sent" emails. */
export const OUTBOX_DIR = path.join(TMP_DIR, "outbox");
/** Where the test backend stores uploaded documents. */
export const STORAGE_DIR = path.join(TMP_DIR, "private-storage");
