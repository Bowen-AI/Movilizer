'use client';

import Link from 'next/link';
import { useState } from 'react';

export default function Navbar() {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-gradient-to-b from-black via-black to-transparent bg-opacity-80 backdrop-blur">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 bg-movilizer-red rounded-full flex items-center justify-center">
              <span className="text-white font-bold text-lg">M</span>
            </div>
            <span className="text-xl font-bold hidden sm:inline">
              <span className="gradient-text">Movilizer</span>
            </span>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex gap-8">
            <Link
              href="/"
              className="hover:text-movilizer-red transition-colors"
            >
              Home
            </Link>
            <Link
              href="/browse"
              className="hover:text-movilizer-red transition-colors"
            >
              Browse
            </Link>
            <Link
              href="/stats"
              className="hover:text-movilizer-red transition-colors"
            >
              Stats
            </Link>
          </div>

          {/* Mobile Menu Button */}
          <button
            className="md:hidden p-2"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>
        </div>

        {/* Mobile Menu */}
        {isMenuOpen && (
          <div className="md:hidden pb-4 border-t border-movilizer-gray">
            <Link
              href="/"
              className="block py-2 hover:text-movilizer-red"
              onClick={() => setIsMenuOpen(false)}
            >
              Home
            </Link>
            <Link
              href="/browse"
              className="block py-2 hover:text-movilizer-red"
              onClick={() => setIsMenuOpen(false)}
            >
              Browse
            </Link>
            <Link
              href="/stats"
              className="block py-2 hover:text-movilizer-red"
              onClick={() => setIsMenuOpen(false)}
            >
              Stats
            </Link>
          </div>
        )}
      </div>
    </nav>
  );
}
