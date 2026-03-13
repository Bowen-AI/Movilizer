'use client';

import { useEffect, useState } from 'react';

interface StatsData {
  total_movies: number;
  total_views: number;
  average_rating: number;
  total_completions: number;
  engagement_rate: number;
  top_movies: Array<{
    movie_id: string;
    title?: string;
    views: number;
    rating: number;
  }>;
}

export default function StatsPage() {
  const [stats, setStats] = useState<StatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await fetch('/api/analytics');
        const data = await response.json();

        // Combine movies and analytics data
        const moviesRes = await fetch('/api/movies');
        const moviesData = await moviesRes.json();
        const movies = moviesData.movies || [];

        // Calculate stats
        const totalMovies = movies.length;
        const avgRating =
          movies.length > 0
            ? movies.reduce((sum: number, m: any) => sum + m.rating, 0) /
              movies.length
            : 0;

        const analyticsData = data.analytics || {};
        const aggregates = analyticsData.aggregates || {};
        const byMovie = aggregates.by_movie || {};

        let totalViews = 0;
        let totalCompletions = 0;

        Object.values(byMovie).forEach((m: any) => {
          totalViews += m.total_views || 0;
          totalCompletions += m.completions || 0;
        });

        const engagementRate =
          totalViews > 0 ? (totalCompletions / totalViews) * 100 : 0;

        // Get top movies
        const topMovies = movies
          .sort((a: any, b: any) => b.rating - a.rating)
          .slice(0, 5)
          .map((m: any) => ({
            movie_id: m.id,
            title: m.title,
            views: byMovie[m.id]?.total_views || 0,
            rating: m.rating,
          }));

        setStats({
          total_movies: totalMovies,
          total_views: totalViews,
          average_rating: avgRating,
          total_completions: totalCompletions,
          engagement_rate: engagementRate,
          top_movies: topMovies,
        });
      } catch (err) {
        console.error('Failed to fetch stats:', err);
        setError('Failed to load statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-2xl font-bold gradient-text">Loading stats...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-2xl font-bold text-red-500">{error}</div>
      </div>
    );
  }

  const StatCard = ({
    title,
    value,
    subtitle,
  }: {
    title: string;
    value: string | number;
    subtitle?: string;
  }) => (
    <div className="bg-movilizer-gray rounded-lg p-6 border border-movilizer-red border-opacity-20">
      <p className="text-gray-400 text-sm uppercase tracking-widest mb-2">
        {title}
      </p>
      <p className="text-4xl font-bold text-movilizer-red mb-1">{value}</p>
      {subtitle && <p className="text-gray-400 text-sm">{subtitle}</p>}
    </div>
  );

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="bg-gradient-to-b from-movilizer-gray to-movilizer-dark pt-8 pb-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h1 className="text-4xl font-bold">
            Analytics <span className="gradient-text">Dashboard</span>
          </h1>
          <p className="text-gray-400 mt-2">
            Real-time statistics from Movilizer
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        {/* Main Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-12">
          <StatCard
            title="Total Movies"
            value={stats.total_movies}
            subtitle="AI-generated"
          />
          <StatCard title="Total Views" value={stats.total_views.toLocaleString()} />
          <StatCard
            title="Avg Rating"
            value={stats.average_rating.toFixed(1)}
            subtitle="out of 10"
          />
          <StatCard
            title="Completions"
            value={stats.total_completions.toLocaleString()}
          />
          <StatCard
            title="Engagement"
            value={`${stats.engagement_rate.toFixed(1)}%`}
            subtitle="Completion rate"
          />
        </div>

        {/* Top Movies Section */}
        {stats.top_movies.length > 0 && (
          <div>
            <h2 className="text-3xl font-bold mb-6">
              Top Performing <span className="gradient-text">Movies</span>
            </h2>

            <div className="grid gap-6">
              {stats.top_movies.map((movie, index) => (
                <div
                  key={movie.movie_id}
                  className="bg-movilizer-gray rounded-lg p-6 border border-movilizer-red border-opacity-20 flex items-center gap-6"
                >
                  {/* Rank */}
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-full bg-movilizer-red flex items-center justify-center font-bold text-lg">
                      {index + 1}
                    </div>
                  </div>

                  {/* Movie Info */}
                  <div className="flex-1">
                    <h3 className="text-xl font-bold">{movie.title}</h3>
                    <div className="flex gap-6 mt-2 text-sm text-gray-400">
                      <span>
                        <span className="font-semibold">{movie.views}</span> views
                      </span>
                      <div className="rating-display">
                        <span className="text-yellow-400">★</span>
                        <span>{movie.rating.toFixed(1)}/10</span>
                      </div>
                    </div>
                  </div>

                  {/* Rating Badge */}
                  <div className="text-right">
                    <p className="text-2xl font-bold text-movilizer-red">
                      {movie.rating.toFixed(1)}
                    </p>
                    <p className="text-xs text-gray-400">Rating</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Empty state */}
        {stats.total_movies === 0 && (
          <div className="text-center py-20">
            <p className="text-gray-400 mb-4">
              No movies have been generated yet
            </p>
            <p className="text-gray-500">
              Check back soon for statistics on AI-generated movies
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
