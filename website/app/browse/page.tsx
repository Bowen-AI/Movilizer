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

export default function Browse() {
  const [movies, setMovies] = useState<Movie[]>([]);
  const [filteredMovies, setFilteredMovies] = useState<Movie[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedGenre, setSelectedGenre] = useState<string>('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState<'rating' | 'date'>('date');
  const [genres, setGenres] = useState<string[]>([]);

  useEffect(() => {
    const fetchMovies = async () => {
      try {
        const response = await fetch('/api/movies');
        const data = await response.json();
        const allMovies = data.movies || [];

        setMovies(allMovies);

        // Extract unique genres
        const uniqueGenres = Array.from(
          new Set(allMovies.map((m: Movie) => m.genre))
        ) as string[];
        setGenres(['All', ...uniqueGenres]);
      } catch (error) {
        console.error('Failed to fetch movies:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchMovies();
  }, []);

  useEffect(() => {
    let filtered = [...movies];

    // Filter by genre
    if (selectedGenre !== 'All') {
      filtered = filtered.filter((m) => m.genre === selectedGenre);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((m) =>
        m.title.toLowerCase().includes(query) ||
        m.synopsis?.toLowerCase().includes(query)
      );
    }

    // Sort
    if (sortBy === 'rating') {
      filtered.sort((a, b) => b.rating - a.rating);
    } else {
      filtered.sort((a, b) =>
        new Date(b.generated_at || 0).getTime() -
        new Date(a.generated_at || 0).getTime()
      );
    }

    setFilteredMovies(filtered);
  }, [movies, selectedGenre, searchQuery, sortBy]);

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="bg-gradient-to-b from-movilizer-gray to-movilizer-dark pt-8 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold mb-8">
            Browse <span className="gradient-text">All Movies</span>
          </h1>

          {/* Search */}
          <div className="relative mb-8">
            <input
              type="text"
              placeholder="Search movies..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full px-4 py-3 bg-movilizer-dark text-white placeholder-gray-500 rounded border border-movilizer-red border-opacity-50 focus:border-movilizer-red focus:outline-none"
            />
            <svg
              className="absolute right-3 top-3.5 w-5 h-5 text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-4 items-center">
            {/* Genre Filter */}
            <div className="flex items-center gap-2">
              <label className="font-semibold">Genre:</label>
              <select
                value={selectedGenre}
                onChange={(e) => setSelectedGenre(e.target.value)}
                className="px-3 py-2 bg-movilizer-dark text-white rounded border border-movilizer-red border-opacity-50 focus:border-movilizer-red focus:outline-none"
              >
                {genres.map((g) => (
                  <option key={g} value={g}>
                    {g}
                  </option>
                ))}
              </select>
            </div>

            {/* Sort */}
            <div className="flex items-center gap-2">
              <label className="font-semibold">Sort by:</label>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'rating' | 'date')}
                className="px-3 py-2 bg-movilizer-dark text-white rounded border border-movilizer-red border-opacity-50 focus:border-movilizer-red focus:outline-none"
              >
                <option value="date">Newest</option>
                <option value="rating">Highest Rated</option>
              </select>
            </div>

            {/* Results count */}
            <div className="ml-auto text-gray-400">
              {filteredMovies.length} {filteredMovies.length === 1 ? 'movie' : 'movies'}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {loading ? (
          <div className="text-center py-20">
            <p className="text-gray-400">Loading...</p>
          </div>
        ) : filteredMovies.length > 0 ? (
          <MovieGrid movies={filteredMovies} />
        ) : (
          <div className="text-center py-20">
            <p className="text-gray-400 mb-4">No movies found</p>
            <button
              onClick={() => {
                setSearchQuery('');
                setSelectedGenre('All');
              }}
              className="btn-secondary"
            >
              Clear Filters
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
