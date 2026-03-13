import { readFileSync, writeFileSync, existsSync } from 'fs';
import { join } from 'path';
import { NextRequest, NextResponse } from 'next/server';

const ANALYTICS_EVENTS = join(process.cwd(), 'public', 'data', 'analytics_events.jsonl');
const ANALYTICS_SUMMARY = join(process.cwd(), 'public', 'data', 'analytics_summary.json');

interface AnalyticsEvent {
  timestamp: string;
  event_type: string;
  movie_id: string;
  user_id?: string;
  metadata?: Record<string, any>;
}

interface AnalyticsSummary {
  total_events: number;
  events_by_type: Record<string, number>;
  events_by_movie: Record<string, number>;
  last_updated: string;
}

function ensureFilesExist(): void {
  const dataDir = join(process.cwd(), 'public', 'data');

  if (!existsSync(dataDir)) {
    const fs = require('fs');
    fs.mkdirSync(dataDir, { recursive: true });
  }

  if (!existsSync(ANALYTICS_EVENTS)) {
    writeFileSync(ANALYTICS_EVENTS, '');
  }

  if (!existsSync(ANALYTICS_SUMMARY)) {
    const summary: AnalyticsSummary = {
      total_events: 0,
      events_by_type: {},
      events_by_movie: {},
      last_updated: new Date().toISOString(),
    };
    writeFileSync(ANALYTICS_SUMMARY, JSON.stringify(summary, null, 2));
  }
}

function getSummary(): AnalyticsSummary {
  try {
    const data = readFileSync(ANALYTICS_SUMMARY, 'utf-8');
    return JSON.parse(data);
  } catch {
    return {
      total_events: 0,
      events_by_type: {},
      events_by_movie: {},
      last_updated: new Date().toISOString(),
    };
  }
}

function recordEvent(event: AnalyticsEvent): void {
  writeFileSync(ANALYTICS_EVENTS, JSON.stringify(event) + '\n', {
    flag: 'a',
  });

  // Update summary
  const summary = getSummary();
  summary.total_events += 1;

  // Count by type
  if (!summary.events_by_type[event.event_type]) {
    summary.events_by_type[event.event_type] = 0;
  }
  summary.events_by_type[event.event_type] += 1;

  // Count by movie
  if (!summary.events_by_movie[event.movie_id]) {
    summary.events_by_movie[event.movie_id] = 0;
  }
  summary.events_by_movie[event.movie_id] += 1;

  summary.last_updated = new Date().toISOString();
  writeFileSync(ANALYTICS_SUMMARY, JSON.stringify(summary, null, 2));
}

export async function GET(request: NextRequest) {
  try {
    ensureFilesExist();
    const summary = getSummary();

    return NextResponse.json({
      success: true,
      analytics: {
        summary,
        aggregates: {
          by_type: summary.events_by_type,
          by_movie: summary.events_by_movie,
        },
      },
    });
  } catch (error) {
    console.error('Error fetching analytics:', error);
    return NextResponse.json(
      { error: 'Failed to fetch analytics', analytics: {} },
      { status: 500 }
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    ensureFilesExist();
    const body = await request.json();

    // Validate required fields
    if (!body.event_type || !body.movie_id) {
      return NextResponse.json(
        { error: 'Missing event_type or movie_id' },
        { status: 400 }
      );
    }

    // Create event record
    const event: AnalyticsEvent = {
      timestamp: new Date().toISOString(),
      event_type: body.event_type,
      movie_id: body.movie_id,
      user_id: body.user_id || 'anonymous',
      metadata: body.metadata || {},
    };

    recordEvent(event);

    return NextResponse.json(
      { success: true, event },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error recording analytics:', error);
    return NextResponse.json(
      { error: 'Failed to record event' },
      { status: 500 }
    );
  }
}
