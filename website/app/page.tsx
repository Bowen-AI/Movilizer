'use client';

import { useEffect, useState } from 'react';
import MovieGrid from '@/components/MovieGrid';

interface Movie {
  id: string;
  title: string;
  genre: string;
  rating: number;
  thumbnail_url: string;
  synopsis?: string;
  generated_at?: string;
}

export default function Home() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [featured, setFeatured] = useState<Movie | null>(null);
  const [newReleases, setNewReleases] = useState<Movie[]>([]);
  const [genres, setGenres] = useState<{ [key: string]: Movie[] }>({});

  useEffect(() => {
    const fetchMovies = async () => {
      try {
        const response = await fetch('/api/movies');
        const data = await response.json();

        setMovies(data.movies || []);

        // Set featured (first/highest rated)
        if (data.movies && data.movies.length > 0) {
          setFeatured(data.movies[0]);

          // Get new releases (last 10)
          setNewReleases(data.movies.slice(0, 10));

          // Group by genre
          const groupedByGenre: { [key: string]: Movie[] } = {};
          data.movies.forEach((movie: Movie) => {
            if (!groupedByGenre[movie.genre]) {
              groupedByGenre[movie.genre] = [];
            }
            groupedByGenre[movie.genre].push(movie);
          });
          setGenres(groupedByGenre);
        }
      } catch (error) {
        console.error('Failed to fetch movies:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMovies();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-2xl font-bold gradient-text">Loading...</div>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Hero Section */}
      {featured && (
        <section className="relative h-96 sm:h-screen max-h-[600px] bg-movilizer-gray overflow-hidden">
          <div
            className="absolute inset-0"
            style={{
              backgroundImage: `url(${featured.thumbnail_url || '/placeholder-hero.jpg'})`,
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          />
          <div className="hero-bg absolute inset-0" />

          {/* Content */}
          <div className="relative h-full flex flex-col justify-end p-6 sm:p-12 max-w-3xl">
            <h1 className="text-4xl sm:text-6xl font-bold mb-4">
              {featured.title}
            </h1>

            {featured.synopsis && (
              <p className="text-gray-200 text-lg mb-6 line-clamp-3">
                {featured.synopsis}
              </p>
            )}

            <div className="flex gap-4 mb-8 flex-wrap">
              <button className="btn-primary flex items-center gap-2">
                <svg
                  className="w-5 h-5"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                </svg>
                Play
              </button>
              <button className="btn-secondary">More Info</button>
            </div>

            {/* Info bar */}
            <div className="flex gap-6 text-sm">
              <div className="rating-display">
                <span className="text-yellow-400">★</span>
                <span className="font-semibold">{featured.rating.toFixed(1)}/10</span>
              </div>
              <span className="genre-badge">{featured.genre}</span>
            </div>
          </div>
        </section>
      )}

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* New Releases */}
        {newReleases.length > 0 && (
          <section className="mb-16">
            <MovieGrid
              movies={newReleases}
              title="New Releases"
              className="mb-8"
            />
          </section>
        )}

        {/* Genre Rows */}
        {Object.entries(genres).map(([genre, genreMovies]) => (
          <section key={genre} className="mb-16">
            <MovieGrid
              movies={genreMovies.slice(0, 8)}
              title={genre}
              className="mb-8"
            />
          </section>
        ))}

        {/* Empty state */}
        {movies.length === 0 && !loading && (
          <div className="text-center py-20">
            <h2 className="text-2xl font-bold mb-4">No movies yet</h2>
            <p className="text-gray-400 mb-8">
              Check back soon for AI-generated movies from Movilizer
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
