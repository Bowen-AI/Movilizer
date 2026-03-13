'use client';

import { useEffect, useRef } from 'react';
import videojs, { VideoJsPlayer } from 'video.js';
import 'video.js/dist/video-js.css';

interface VideoPlayerProps {
  videoUrl: string;
  posterUrl?: string;
  title: string;
  controls?: boolean;
  autoplay?: boolean;
  onPlay?: () => void;
  onPause?: () => void;
  onEnded?: () => void;
}

export default function VideoPlayer({
  videoUrl,
  posterUrl,
  title,
  controls = true,
  autoplay = false,
  onPlay,
  onPause,
  onEnded,
}: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const playerRef = useRef<VideoJsPlayer | null>(null);

  useEffect(() => {
    if (!videoRef.current) return;

    // Initialize video.js player
    const player = videojs(videoRef.current, {
      controls: controls,
      autoplay: autoplay,
      preload: 'auto',
      responsive: true,
      fluid: true,
      poster: posterUrl,
      sources: [
        {
          src: videoUrl,
          type: getVideoType(videoUrl),
        },
      ],
    });

    playerRef.current = player;

    // Handle events
    if (onPlay) player.on('play', onPlay);
    if (onPause) player.on('pause', onPause);
    if (onEnded) player.on('ended', onEnded);

    // Cleanup
    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
      }
    };
  }, [videoUrl, posterUrl, controls, autoplay, onPlay, onPause, onEnded]);

  return (
    <div className="video-player-container">
      <video
        ref={videoRef}
        className="video-js vjs-default-skin"
        controlsList="nodownload"
      >
        <source src={videoUrl} type={getVideoType(videoUrl)} />
        <p className="vjs-no-js">
          To view this video please enable JavaScript, and consider upgrading to a
          web browser that
          <a href="https://videojs.com/html5-video-support/" target="_blank" rel="noreferrer">
            supports HTML5 video
          </a>
        </p>
      </video>
    </div>
  );
}

function getVideoType(url: string): string {
  if (url.includes('.m3u8')) {
    return 'application/x-mpegURL';
  }
  if (url.includes('.mp4')) {
    return 'video/mp4';
  }
  if (url.includes('.webm')) {
    return 'video/webm';
  }
  return 'video/mp4';
}
