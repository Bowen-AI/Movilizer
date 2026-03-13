# Movilizer - Netflix-like AI Movie Streaming Platform

A professional, cinematic Next.js website for streaming AI-generated movies from the Movilizer daemon.

## Features

- **Responsive Design**: Works seamlessly on desktop, tablet, and mobile
- **Dark Theme**: Netflix-inspired dark interface with red accents
- **Movie Streaming**: Full-screen video player with HLS support
- **Browse & Search**: Filter movies by genre, search by title
- **Analytics**: Real-time statistics dashboard
- **Auto-playing Trailers**: Hover effects on movie cards
- **Progressive Enhancement**: Works with or without JavaScript

## Tech Stack

- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe development
- **Tailwind CSS**: Utility-first styling
- **Video.js**: Professional video player with HLS support
- **Node.js**: Backend API routes

## Getting Started

### Prerequisites

- Node.js 18+ (with npm or yarn)
- Movilizer daemon running (for movie data)

### Installation

```bash
# Install dependencies
npm install
# or
yarn install
```

### Environment Setup

Create a `.env.local` file if needed for API configuration:

```env
NEXT_PUBLIC_API_URL=http://localhost:3000
```

### Development

```bash
npm run dev
# or
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) to view the site.

### Production Build

```bash
npm run build
npm start
```

## Project Structure

```
website/
├── app/                    # Next.js App Router
│   ├── api/               # API routes
│   │   ├── movies/        # Movie management endpoints
│   │   └── analytics/     # Analytics tracking endpoints
│   ├── browse/            # Movie browsing page
│   ├── movie/
│   │   ├── [id]/          # Movie detail page
│   │   └── [id]/watch/    # Full-screen player page
│   ├── stats/             # Analytics dashboard
│   ├── layout.tsx         # Root layout
│   ├── page.tsx           # Homepage
│   └── globals.css        # Global styles
├── components/            # Reusable React components
│   ├── Navbar.tsx        # Navigation bar
│   ├── MovieCard.tsx     # Movie card component
│   ├── MovieGrid.tsx     # Movie grid layout
│   └── VideoPlayer.tsx   # Video player wrapper
├── public/
│   └── data/             # Generated movie data (JSON)
├── tailwind.config.js    # Tailwind configuration
├── next.config.js        # Next.js configuration
└── tsconfig.json         # TypeScript configuration
```

## API Routes

### Movies API

**GET /api/movies**
- Fetch all published movies
- Query parameters:
  - `limit`: Number of movies per page (default: 50)
  - `offset`: Pagination offset (default: 0)
  - `genre`: Filter by genre

**POST /api/movies**
- Create/update a movie record
- Required fields: id, title, genre, video_url, thumbnail_url

### Analytics API

**GET /api/analytics**
- Get analytics summary and aggregates

**POST /api/analytics**
- Record an analytics event
- Event types: view, play, pause, complete, share, click

## Data Format

### Movie Record

```json
{
  "id": "uuid",
  "title": "Movie Title",
  "genre": "Action",
  "rating": 8.5,
  "duration_seconds": 5400,
  "synopsis": "Movie description...",
  "thumbnail_url": "/media/uuid/poster.jpg",
  "video_url": "/media/uuid/hls/stream.m3u8",
  "trailer_url": "/media/uuid/trailer.mp4",
  "generated_at": "2024-03-12T10:30:00Z",
  "published_at": "2024-03-12T10:35:00Z",
  "metadata": { "director_ai": "advanced-model-v2" }
}
```

## Styling

The site uses Tailwind CSS with custom Movilizer theme colors:

- **Primary Red**: `#e50914` (movilizer-red)
- **Dark BG**: `#0f0f0f` (movilizer-dark)
- **Secondary**: `#221f1f` (movilizer-gray)

Global styles and animations are in `app/globals.css`.

## Performance Optimizations

- Next.js Image optimization
- Responsive images
- Lazy loading for movie cards
- Video player with streaming support (HLS)
- Efficient state management
- CSS animations for smooth UX

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari, Chrome Mobile)

## Integration with Movilizer Daemon

The website automatically integrates with the Python Movilizer daemon:

1. Movies are published via `MoviePublisher.publish_movie()`
2. Movies database stored at `website/public/data/movies.json`
3. Videos stored at `website/public/media/[movie_id]/`
4. Analytics events are recorded and processed

## Deployment

### Vercel (Recommended)

```bash
vercel deploy
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Static Export

```bash
npm run build
```

Output will be in `out/` directory, suitable for static hosting.

## Troubleshooting

**"Movies not loading"**
- Ensure Movilizer daemon is running
- Check `public/data/movies.json` exists and has content
- Verify video files are accessible at `public/media/`

**"Video player not working"**
- Check browser console for errors
- Verify video URL is correct (HLS or MP4)
- Ensure CORS headers are set correctly

**"Build errors"**
- Clear `.next` directory: `rm -rf .next`
- Reinstall dependencies: `rm -rf node_modules && npm install`
- Check TypeScript: `npm run type-check`

## License

Part of the Movilizer project. All rights reserved.

## Support

For issues and questions, contact the Movilizer development team.
