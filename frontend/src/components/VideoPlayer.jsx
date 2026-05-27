/**
 * BitFlow HLS Video Player Component
 *
 * Adaptive bitrate player using hls.js for smooth streaming.
 * Automatically selects quality tier based on available bandwidth.
 * Falls back to native <video> for Safari (native HLS support).
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import Hls from 'hls.js';
import { usePlayerStore } from '../store/playerStore';
import QualitySelector from './QualitySelector';
import VolumeControl from './VolumeControl';
import ProgressBar from './ProgressBar';

const QUALITY_LABELS = {
  '-1': 'Auto',
  '0': '360p',
  '1': '480p',
  '2': '720p',
  '3': '1080p',
};

export default function VideoPlayer({ videoId, manifestUrl, poster }) {
  const videoRef = useRef(null);
  const hlsRef = useRef(null);
  const [levels, setLevels] = useState([]);
  const [currentLevel, setCurrentLevel] = useState(-1);
  const [buffered, setBuffered] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [showControls, setShowControls] = useState(true);

  const { volume, setVolume, isMuted, setMuted } = usePlayerStore();

  const initHls = useCallback(() => {
    if (!manifestUrl || !videoRef.current) return;

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
        backBufferLength: 90,
        maxBufferLength: 30,
        maxMaxBufferLength: 600,
        startLevel: -1, // Auto quality
      });

      hls.loadSource(manifestUrl);
      hls.attachMedia(videoRef.current);

      hls.on(Hls.Events.MANIFEST_PARSED, (_, data) => {
        setLevels(data.levels);
        videoRef.current.play().catch(() => {});
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_, data) => {
        setCurrentLevel(data.level);
      });

      hls.on(Hls.Events.ERROR, (_, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
          }
        }
      });

      hlsRef.current = hls;
    } else if (videoRef.current.canPlayType('application/vnd.apple.mpegurl')) {
      // Safari native HLS
      videoRef.current.src = manifestUrl;
    }
  }, [manifestUrl]);

  useEffect(() => {
    initHls();
    return () => hlsRef.current?.destroy();
  }, [initHls]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const onTimeUpdate = () => {
      setCurrentTime(video.currentTime);
      if (video.buffered.length > 0) {
        setBuffered(video.buffered.end(video.buffered.length - 1));
      }
    };
    const onDurationChange = () => setDuration(video.duration);
    const onPlay = () => setIsPlaying(true);
    const onPause = () => setIsPlaying(false);

    video.addEventListener('timeupdate', onTimeUpdate);
    video.addEventListener('durationchange', onDurationChange);
    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate);
      video.removeEventListener('durationchange', onDurationChange);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
    };
  }, []);

  const handleQualityChange = (level) => {
    if (hlsRef.current) {
      hlsRef.current.currentLevel = level;
      setCurrentLevel(level);
    }
  };

  const handleSeek = (time) => {
    if (videoRef.current) videoRef.current.currentTime = time;
  };

  return (
    <div
      className="player-container"
      onMouseMove={() => setShowControls(true)}
      onMouseLeave={() => setShowControls(false)}
    >
      <video
        ref={videoRef}
        poster={poster}
        volume={volume}
        muted={isMuted}
        className="player-video"
        playsInline
      />

      {showControls && (
        <div className="player-controls">
          <ProgressBar
            currentTime={currentTime}
            duration={duration}
            buffered={buffered}
            onSeek={handleSeek}
          />
          <div className="player-controls__row">
            <button onClick={() => isPlaying ? videoRef.current.pause() : videoRef.current.play()}>
              {isPlaying ? '⏸' : '▶'}
            </button>
            <VolumeControl volume={volume} muted={isMuted} onChange={setVolume} onMute={setMuted} />
            <QualitySelector
              levels={levels}
              current={currentLevel}
              labels={QUALITY_LABELS}
              onChange={handleQualityChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}
