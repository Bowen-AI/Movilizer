'use client';

import Link from 'next/link';
import { useState } from 'react';

interface MovieCardProps {
  id: string;
  title: string;
  genre: string;
  rating: number;
  thumbnail_url: string;
  synopsis?: string;
  generated_at?: string;
}

export default function MovieCard({
  id,
  title,
  genre,
  rating,
  thumbnail_url,
  synopsis,
  generated_at,
}: MovieCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <Link href={`/movie/${id}`}>
      <div
        className="movie-card relative group cursor-pointer rounded-lg overflow-hidden h-64 sm:h-72"
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
      >
        {/* Poster Image */}
        <div
          className="relative w-full h-full bg-movilizer-gray"
          style={{
            backgroundImage: `url(${thumbnail_url || '/placeholder-movie.jpg'})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        >
          {/* Overlay on hover */}
          {isHovered && (
            <div className="absolute inset-0 bg-black bg-opacity-60 transition-all duration-300 flex flex-col justify-end p-4">
              {/* Fade overlay */}
              <div className="fade-overlay" />

              {/* Info */}
              <div className="relative z-10">
                <h3 className="text-lg font-bold mb-2 line-clamp-2">
                  {title}
                </h3>
                {synopsis && (
                  <p className="text-sm text-gray-200 line-clamp-2 mb-3">
                    {synopsis}
                  </p>
                )}

                {/* Metadata */}
                <div className="flex items-center justify-between">
                  <div className="flex gap-2 items-center flex-wrap">
                    <span className="genre-badge">{genre}</span>
                    <div className="rating-display">
                      <span className="text-yellow-400">★</span>
                      <span className="text-sm font-semibold">{rating.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Play Button */}
              <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                <div className="play-button">
                  <svg
                    className="w-5 h-5 text-black"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                  </svg>
                </div>
              </div>
            </div>
          )}

          {/* Static info (shown always) */}
          <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black via-black to-transparent">
            <h3 className="text-sm font-bold truncate">{title}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-xs text-gray-400">{genre}</span>
              <div className="rating-display text-xs">
                <span className="text-yellow-400">★</span>
                <span>{rating.toFixed(1)}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
