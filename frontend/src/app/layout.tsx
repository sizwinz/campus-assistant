import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { LanguageProvider } from '@/hooks/useLanguage'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Campus Assistant - Multilingual Chatbot',
  description: 'A multilingual AI assistant for campus queries. Ask questions in Hindi, English, Gujarati, Marathi, Punjabi, Tamil, and more.',
  keywords: ['chatbot', 'campus', 'assistant', 'multilingual', 'education', 'college'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <LanguageProvider>{children}</LanguageProvider>
      </body>
    </html>
  )
}
