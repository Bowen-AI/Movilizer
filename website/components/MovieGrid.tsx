'use client';

import MovieCard from './MovieCard';

interface Movie {
  id: string;
  title: string;
  genre: string;
  rating: number;
  thumbnail_url: string;
  synopsis?: string;
  generated_at?: string;
}

interface MovieGridProps {
  movies: Movie[];
  title?: string;
  className?: string;
}

export default function MovieGrid({
  movies,
  title,
  className = '',
}: MovieGridProps) {
  if (!movies || movies.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-400">No movies available</p>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      {title && (
        <h2 className="text-2xl font-bold mb-6 text-white">
          {title}
          <div className="row-separator mt-4" />
        </h2>
      )}

      <div className="movie-grid grid gap-4 sm:gap-6">
        {movies.map((movie) => (
          <MovieCard
            key={movie.id}
            id={movie.id}
            title={movie.title}
            genre={movie.genre}
            rating={movie.rating}
            thumbnail_url={movie.thumbnail_url}
            synopsis={movie.synopsis}
            generated_at={movie.generated_at}
          />
        ))}
      </div>
    </div>
  );
}
