import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    rules: {
      // A leading underscore marks an argument as intentionally unused,
      // e.g. a function that must keep its signature but ignores a value.
      "@typescript-eslint/no-unused-vars": [
        "warn",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    ".next-e2e/**",
    "e2e/.tmp/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Playwright output:
    "test-results/**",
    "playwright-report/**",
  ]),
]);

export default eslintConfig;
