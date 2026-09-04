import type { Metadata } from 'next';
import { IBM_Plex_Mono, Manrope } from 'next/font/google';
import './globals.css';

const manrope = Manrope({
  variable: '--font-manrope',
  subsets: ['latin'],
});

const plexMono = IBM_Plex_Mono({
  variable: '--font-plex-mono',
  subsets: ['latin'],
  weight: ['400', '500', '600'],
});

export const metadata: Metadata = {
  title: 'CNCM-RRK Playground',
  description:
    'Chat, run exact math, inspect CAS reasoning traces, and explore a whole-machine CAS-Ohm attention design simulation in your browser.',
  metadataBase: new URL('https://cncm-rrk-native-playground.wakil.chatgpt.site'),
  openGraph: {
    title: 'CNCM-RRK Playground',
    description: 'Chat • Reason • Inspect • Simulate CAS-Ohm flow • Verify.',
    images: [{ url: '/og.png', width: 1200, height: 630 }],
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CNCM-RRK Playground',
    description: 'Chat • Reason • Inspect • Simulate CAS-Ohm flow • Verify.',
    images: ['/og.png'],
  },
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className="dark">
      <body className={`${manrope.variable} ${plexMono.variable} antialiased`}>{children}</body>
    </html>
  );
}
