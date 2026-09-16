module.exports = {
  root: true,
  env: { browser: true, es2022: true },
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react-hooks/recommended",
  ],
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  ignorePatterns: ["dist", "src-tauri", "*.cjs"],
  rules: {
    // DG-ADR-017 §4: no raw hex colours outside the token files.
    "no-restricted-syntax": [
      "warn",
      {
        selector: "Literal[value=/^#[0-9A-Fa-f]{3,8}$/]",
        message:
          "Raw hex colours are not allowed outside src/styles/ds.css and dgs.css — use a CSS custom property (--ds-*/--dgs-*) instead. See docs/deployguard/05-ux-principles.md §2.",
      },
    ],
  },
};
