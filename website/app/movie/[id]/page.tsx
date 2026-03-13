'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';

interface Movie {
  id: string;
  title: string;
  genre: string;
  rating: number;
  duration_seconds: number;
  synopsis: string;
  thumbnail_url: string;
  video_url: string;
  trailer_url?: string;
  generated_at: string;
  metadata?: Record<string, any>;
}

export default function MovieDetail({ params }: { params: { id: string } }) {
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchMovie = async () => {
      try {
        const response = await fetch('/api/movies');
        const data = await response.json();
        const movies = data.movies || [];
        const foundMovie = movies.find((m: Movie) => m.id === params.id);

        if (!foundMovie) {
          setError('Movie not found');
        } else {
          setMovie(foundMovie);
        }
      } catch (err) {
        setError('Failed to load movie');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchMovie();
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-2xl font-bold gradient-text">Loading...</div>
      </div>
    );
  }

  if (error || !movie) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center">
        <div className="text-2xl font-bold mb-4">{error || 'Movie not found'}</div>
        <Link href="/browse" className="btn-primary">
          Back to Browse
        </Link>
      </div>
    );
  }

  const formatDuration = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m`;
    }
    return `${minutes}m ${secs}s`;
  };

  const generatedDate = new Date(movie.generated_at).toLocaleDateString();

  return (
    <div className="min-h-screen">
      {/* Back Button */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <Link
          href="/browse"
          className="inline-flex items-center gap-2 text-movilizer-red hover:text-red-700"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
          Back
        </Link>
      </div>

      {/* Hero/Poster Section */}
      <div className="relative h-96 bg-movilizer-gray overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: `url(${movie.thumbnail_url})`,
            backgroundSize: 'cover',
            backgroundPosition: 'center',
          }}
        />
        <div className="hero-bg absolute inset-0" />

        <div className="relative h-full flex items-end p-6 sm:p-12">
          <div className="flex flex-col sm:flex-row gap-8 items-end w-full">
            {/* Poster */}
            <div
              className="hidden sm:block w-40 h-56 rounded-lg shadow-2xl flex-shrink-0"
              style={{
                backgroundImage: `url(${movie.thumbnail_url})`,
                backgroundSize: 'cover',
              }}
            />

            {/* Info */}
            <div className="flex-1">
              <h1 className="text-5xl font-bold mb-4">{movie.title}</h1>
              <div className="flex flex-wrap gap-4 mb-6">
                <span className="genre-badge text-lg">{movie.genre}</span>
                <div className="rating-display text-lg">
                  <span className="text-yellow-400 text-2xl">★</span>
                  <span className="font-bold">{movie.rating.toFixed(1)}/10</span>
                </div>
                <span className="text-gray-300">
                  {formatDuration(movie.duration_seconds)}
                </span>
                <span className="text-gray-400">{generatedDate}</span>
              </div>

              {/* Play Button */}
              <Link
                href={`/movie/${movie.id}/watch`}
                className="btn-primary inline-flex items-center gap-2 text-lg px-8 py-3"
              >
                <svg
                  className="w-6 h-6"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                </svg>
                Play Now
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Details */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-12">
          {/* Synopsis */}
          <div className="lg:col-span-2">
            <h2 className="text-2xl font-bold mb-4">Synopsis</h2>
            <p className="text-gray-300 text-lg leading-relaxed">
              {movie.synopsis}
            </p>

            {/* Metadata */}
            {movie.metadata && Object.keys(movie.metadata).length > 0 && (
              <div className="mt-12">
                <h2 className="text-2xl font-bold mb-4">Production Details</h2>
                <div className="grid grid-cols-2 gap-6">
                  {Object.entries(movie.metadata).map(([key, value]) => (
                    <div key={key}>
                      <p className="text-gray-400 text-sm uppercase tracking-widest">
                        {key.replace(/_/g, ' ')}
                      </p>
                      <p className="text-white text-lg font-semibold mt-1">
                        {String(value)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-movilizer-gray rounded-lg p-8 sticky top-20">
              <h3 className="text-xl font-bold mb-6">Details</h3>

              <div className="space-y-6">
                <div>
                  <p className="text-gray-400 text-sm">RATING</p>
                  <p className="text-2xl font-bold text-movilizer-red">
                    {movie.rating.toFixed(1)}/10
                  </p>
                </div>

                <div>
                  <p className="text-gray-400 text-sm">GENRE</p>
                  <p className="text-lg font-semibold">{movie.genre}</p>
                </div>

                <div>
                  <p className="text-gray-400 text-sm">DURATION</p>
                  <p className="text-lg font-semibold">
                    {formatDuration(movie.duration_seconds)}
                  </p>
                </div>

                <div>
                  <p className="text-gray-400 text-sm">GENERATED</p>
                  <p className="text-lg font-semibold">{generatedDate}</p>
                </div>

                <div className="pt-4 border-t border-movilizer-red border-opacity-30">
                  <p className="text-xs text-gray-400">
                    This movie was generated using advanced AI technology by Movilizer.
                  </p>
                </div>
              </div>

              {/* Share Buttons */}
              <div className="mt-8 flex gap-3">
                <button className="flex-1 btn-ghost text-center">
                  <svg
                    className="w-5 h-5 inline"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M15.898 4.045c-.893-.893-2.346-.893-3.239 0l-.711.71-.711-.71c-.893-.893-2.345-.893-3.239 0-.393.393-.643.87-.643 1.404s.25 1.011.643 1.404l4.63 4.629 4.629-4.629c.394-.393.644-.87.644-1.404s-.25-1.011-.644-1.404z" />
                  </svg>
                </button>
                <button className="flex-1 btn-ghost text-center">
                  <svg
                    className="w-5 h-5 inline"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path d="M5.5 13a3.5 3.5 0 01-.369-6.98 4 4 0 117.753-1.3A4.5 4.5 0 1113.5 13H11V9.413h1.5V8h-1.5V6.5c0-.366.146-.72.404-.972h.904c.223 0 .437.042.636.114A4.5 4.5 0 005.5 13z" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
