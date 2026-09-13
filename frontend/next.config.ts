import type { NextConfig } from "next";
// Public Vercel deployments are always a disconnected portfolio preview.
// Local builds retain the existing operator configuration.
const portfolio = process.env.VERCEL === "1" || process.env.NEXT_PUBLIC_PORTFOLIO_PREVIEW === "true";
const config: NextConfig = {
  output: "export", trailingSlash: true,
  env: {
    NEXT_PUBLIC_PORTFOLIO_PREVIEW: portfolio ? "true" : "false",
    ...(portfolio ? {NEXT_PUBLIC_API_URL: ""} : {}),
  },
};
export default config;
