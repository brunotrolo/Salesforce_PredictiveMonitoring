export default {
  testEnvironment: "node",
  transform: {},
  extensionsToTreatAsEsm: [],
  moduleFileExtensions: ["js", "mjs"],
  testMatch: ["**/tests/**/test-*.js", "**/tests/**/*.test.js"],
  collectCoverageFrom: [
    "monitoring/**/*.js",
    "!monitoring/tests/**",
    "!**/node_modules/**"
  ],
  coverageThreshold: {
    global: {
      branches: 70,
      functions: 70,
      lines: 70,
      statements: 70
    }
  }
};
