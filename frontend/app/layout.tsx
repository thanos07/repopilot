import type { Metadata } from 'next';
import './globals.css';
export const metadata: Metadata = { title: 'RepoPilot — Your repository. Your final call.', description: 'Inspect the plan, code changes and verification behind every task.' };
export default function Layout({children}: Readonly<{children: React.ReactNode}>) { return <html lang="en" suppressHydrationWarning><head><script dangerouslySetInnerHTML={{__html: `try{document.documentElement.dataset.theme=localStorage.getItem("repopilot:theme")==="light"?"light":"dark"}catch{document.documentElement.dataset.theme="dark"}`}}/></head><body>{children}</body></html>; }

