import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'System Builder Hub (SBH)',
  description: 'AI-assisted platform that designs, scaffolds, deploys, and monitors complete software systems onto AWS',
  keywords: 'system builder, AI, AWS, deployment, infrastructure, software development',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  )
}
