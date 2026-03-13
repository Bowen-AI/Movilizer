'use client';

import VideoPlayer from '@/components/VideoPlayer';
import Link from 'next/link';
import { useEffect, useState } from 'react';

interface Movie {
  id: string;
  title: string;
  genre: string;
  rating: number;
  video_url: string;
  thumbnail_url: string;
  trailer_url?: string;
  synopsis: string;
}

export default function WatchMovie({ params }: { params: { id: string } }) {
  const [movie, setMovie] = useState<Movie | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [watchTime, setWatchTime] = useState(0);

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

          // Record view
          await recordAnalytics('view', params.id);
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

  const recordAnalytics = async (eventType: string, movieId: string) => {
    try {
      await fetch('/api/analytics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          event_type: eventType,
          movie_id: movieId,
        }),
      });
    } catch (err) {
      console.error('Failed to record analytics:', err);
    }
  };

  const handlePlay = () => {
    recordAnalytics('play', params.id);
  };

  const handlePause = () => {
    recordAnalytics('pause', params.id);
  };

  const handleEnded = async () => {
    recordAnalytics('complete', params.id);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-black">
        <div className="text-2xl font-bold">Loading video...</div>
      </div>
    );
  }

  if (error || !movie) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-black gap-4">
        <div className="text-2xl font-bold">{error || 'Movie not found'}</div>
        <Link href="/browse" className="btn-primary">
          Back to Browse
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black">
      {/* Video Player */}
      <VideoPlayer
        videoUrl={movie.video_url}
        posterUrl={movie.thumbnail_url}
        title={movie.title}
        onPlay={handlePlay}
        onPause={handlePause}
        onEnded={handleEnded}
      />

      {/* Movie Info Below Player */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-4">{movie.title}</h1>
          <p className="text-gray-300 mb-4">{movie.synopsis}</p>

          <div className="flex flex-wrap gap-4 items-center">
            <span className="genre-badge">{movie.genre}</span>
            <div className="rating-display">
              <span className="text-yellow-400">★</span>
              <span className="font-semibold">{movie.rating.toFixed(1)}/10</span>
            </div>

            {/* Share buttons */}
            <div className="ml-auto flex gap-3">
              <button
                className="btn-ghost"
                onClick={() => recordAnalytics('share', params.id)}
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M8.684 13.342C9.017 13.447 9.5 13.5 10 13.5c4.418 0 8-1.79 8-4s-3.582-4-8-4-8 1.79-8 4c0 1.393.409 2.701 1.08 3.721m0 0l2.6 1.5m0 0l2.4-3.236m-6-3.944A7.988 7.988 0 0110 5c4.418 0 8 1.79 8 4 0 1.393-.409 2.701-1.08 3.721M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                  />
                </svg>
              </button>
            </div>
          </div>
        </div>

        {/* Back to movie */}
        <Link
          href={`/movie/${movie.id}`}
          className="inline-flex items-center gap-2 text-movilizer-red hover:text-red-700"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path
              fillRule="evenodd"
              d="M9.707 16.707a1 1 0 01-1.414 0l-6-6a1 1 0 010-1.414l6-6a1 1 0 011.414 1.414L5.414 9H17a1 1 0 110 2H5.414l4.293 4.293a1 1 0 010 1.414z"
              clipRule="evenodd"
            />
          </svg>
          Back to Details
        </Link>
      </div>
    </div>
  );
}
