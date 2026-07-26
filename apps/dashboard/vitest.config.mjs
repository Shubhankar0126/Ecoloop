import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const rootDirectory = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  esbuild: {
    jsx: "automatic"
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      reportsDirectory: "./coverage",
      include: [
        "src/components/marketing/**/*.{ts,tsx}",
        "src/components/workspace/**/*.{ts,tsx}",
        "src/components/ui/state-card.tsx",
        "src/hooks/**/*.{ts,tsx}",
        "src/lib/**/*.{ts,tsx}"
      ],
      thresholds: {
        lines: 90,
        functions: 90,
        branches: 85,
        statements: 90
      }
    }
  },
  resolve: {
    alias: {
      "@": path.resolve(rootDirectory, "./src")
    }
  }
});
