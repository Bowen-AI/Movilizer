import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';

export const metadata: Metadata = {
  title: 'Movilizer - AI-Generated Movies',
  description: 'Stream unlimited AI-generated movies powered by Movilizer',
  keywords: 'movies, AI, streaming, entertainment',
  viewport: 'width=device-width, initial-scale=1',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-movilizer-dark text-white">
        <Navbar />
        <main className="pt-16 min-h-screen">
          {children}
        </main>
        <footer className="bg-black bg-opacity-50 text-gray-400 py-8 mt-16">
          <div className="max-w-7xl mx-auto px-4 text-center">
            <p>&copy; 2024 Movilizer. AI-generated entertainment.</p>
            <p className="text-sm mt-2">Powered by advanced generative AI</p>
          </div>
        </footer>
      </body>
    </html>
  );
}
