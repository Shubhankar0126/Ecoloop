import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({
  baseDirectory: dirname(fileURLToPath(import.meta.url))
});

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: ["node_modules/**", ".next/**", "coverage/**", "next-env.d.ts"]
  },
  {
    files: ["**/*.test.ts", "**/*.test.tsx", "vitest.setup.ts"],
    languageOptions: {
      globals: {
        afterEach: "readonly",
        beforeEach: "readonly",
        describe: "readonly",
        expect: "readonly",
        it: "readonly",
        vi: "readonly"
      }
    }
  }
];

export default config;
