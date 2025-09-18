import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { SimpleAuthProvider } from '@/components/SimpleAuthProvider'

const inter = Inter({ subsets: ['latin'] })

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
      <body className={inter.className}>
        <SimpleAuthProvider>
          {children}
        </SimpleAuthProvider>
      </body>
    </html>
  )
}
