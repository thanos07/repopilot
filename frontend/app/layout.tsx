import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'RepoPilot — Coding workspace', description: 'Inspect the plan, code changes and verification behind every task.' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en"><body>{children}</body></html>; }
