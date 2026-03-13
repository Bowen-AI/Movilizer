import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import { NextRequest, NextResponse } from 'next/server';

const MOVIES_DB = join(process.cwd(), 'public', 'data', 'movies.json');

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
  published_at: string;
  metadata?: Record<string, any>;
}

interface MoviesDB {
  movies: Movie[];
  total_movies: number;
  last_updated: string;
}

function ensureDBExists(): MoviesDB {
  if (!existsSync(MOVIES_DB)) {
    const defaultDB: MoviesDB = {
      movies: [],
      total_movies: 0,
      last_updated: new Date().toISOString(),
    };
    writeFileSync(MOVIES_DB, JSON.stringify(defaultDB, null, 2));
    return defaultDB;
  }

  try {
    const data = readFileSync(MOVIES_DB, 'utf-8');
    return JSON.parse(data);
  } catch (error) {
    console.error('Error reading movies DB:', error);
    return {
      movies: [],
      total_movies: 0,
      last_updated: new Date().toISOString(),
    };
  }
}

function saveDB(db: MoviesDB): void {
  writeFileSync(MOVIES_DB, JSON.stringify(db, null, 2));
}

export async function GET(request: NextRequest) {
  try {
    const db = ensureDBExists();

    // Support pagination
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '50');
    const offset = parseInt(request.nextUrl.searchParams.get('offset') || '0');
    const genre = request.nextUrl.searchParams.get('genre');

    let movies = [...db.movies];

    // Filter by genre if provided
    if (genre) {
      movies = movies.filter((m) => m.genre.toLowerCase() === genre.toLowerCase());
    }

    // Apply pagination
    const paginated = movies.slice(offset, offset + limit);

    return NextResponse.json({
      movies: paginated,
      total: movies.length,
      limit,
      offset,
    });
  } catch (error) {
    console.error('Error fetching movies:', error);
    return NextResponse.json(
      { error: 'Failed to fetch movies', movies: [] },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const db = ensureDBExists();

    // Validate required fields
    if (
      !body.id ||
      !body.title ||
      !body.genre ||
      !body.video_url ||
      !body.thumbnail_url
    ) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Create movie record
    const movie: Movie = {
      id: body.id,
      title: body.title,
      genre: body.genre,
      rating: body.rating || 7.5,
      duration_seconds: body.duration_seconds || 0,
      synopsis: body.synopsis || '',
      thumbnail_url: body.thumbnail_url,
      video_url: body.video_url,
      trailer_url: body.trailer_url,
      generated_at: body.generated_at || new Date().toISOString(),
      published_at: new Date().toISOString(),
      metadata: body.metadata,
    };

    // Check if movie already exists
    const existingIndex = db.movies.findIndex((m) => m.id === body.id);
    if (existingIndex >= 0) {
      db.movies[existingIndex] = movie;
    } else {
      db.movies.push(movie);
      db.total_movies += 1;
    }

    db.last_updated = new Date().toISOString();

    // Sort by generated_at descending (newest first)
    db.movies.sort((a, b) => {
      return (
        new Date(b.generated_at).getTime() - new Date(a.generated_at).getTime()
      );
    });

    saveDB(db);

    return NextResponse.json(
      { success: true, movie },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error creating movie:', error);
    return NextResponse.json(
      { error: 'Failed to create movie' },
      { status: 500 }
    );
  }
}
