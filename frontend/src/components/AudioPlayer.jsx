import React, { useRef, useState, useEffect } from 'react';
import { Play, Pause, Volume2, VolumeX } from 'lucide-react';
import { resolveAssetUrl } from '../api';
import { useLanguage } from '../context/LanguageContext';

const AudioPlayer = ({ track, isPlaying, onPlayPause }) => {
  const { lang } = useLanguage();
  const audioRef = useRef(null);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [volume, setVolume] = useState(0.7);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackError, setPlaybackError] = useState(null);
  const t = {
    playbackError: lang === 'ar' ? 'تعذر تشغيل المعاينة. حاول مرة أخرى.' : 'Preview could not be played. Please try again.',
    loadError: lang === 'ar' ? 'تعذر تحميل ملف المعاينة.' : 'Preview file could not be loaded.',
    selectTrack: lang === 'ar' ? 'اختر تراكًا للمعاينة' : 'Select a track to preview',
  };

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
    };

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);

    return () => {
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, []);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio || !track) return;

    audio.currentTime = 0;
    setCurrentTime(0);
    setPlaybackError(null);

    if (isPlaying) {
      audio.play().catch(() => {
        setPlaybackError(t.playbackError);
        onPlayPause(false);
      });
    } else {
      audio.pause();
    }
  }, [isPlaying, track]);

  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  const handleProgressClick = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const percentage = (e.clientX - rect.left) / rect.width;
    const newTime = percentage * duration;
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  if (!track) {
    return (
      <div className="fixed bottom-0 left-0 right-0 border-t border-[#e4e0d8] bg-white p-4 text-center text-[#727981]">
        {t.selectTrack}
      </div>
    );
  }

  return (
    <div
      className="fixed bottom-0 left-0 right-0 z-50 border-t border-[#e4e0d8] bg-white shadow-[0_-8px_24px_rgba(34,40,49,0.08)]"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      {/* Progress Bar */}
      <div
        onClick={handleProgressClick}
        className="h-1 cursor-pointer bg-[#e6e2da] transition-all duration-200 hover:h-2"
        style={{
          background: `linear-gradient(to right, #ed7755 0%, #ed7755 ${
            duration ? (currentTime / duration) * 100 : 0
          }%, #e6e2da ${duration ? (currentTime / duration) * 100 : 0}%, #e6e2da 100%)`,
        }}
      />

      {/* Player Content */}
      <div className="flex flex-col gap-3 px-4 sm:px-6 py-3 sm:py-4 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
        {/* Track Info */}
        <div className="w-full sm:flex-1 min-w-0">
          <h4 className="truncate font-semibold text-[#222831]">{track.title}</h4>
          <p className="truncate text-sm text-[#727981]">{track.artist}</p>
        </div>

        {/* Controls */}
        <div className="flex w-full items-center justify-between gap-3 sm:w-auto sm:justify-start sm:gap-4">
          {/* Play/Pause Button */}
          <button
            onClick={() => onPlayPause(!isPlaying)}
            className="flex-shrink-0 rounded-full bg-[#ed7755] p-3 text-white transition-all duration-200 hover:bg-[#d96343]"
          >
            {isPlaying ? (
              <Pause size={20} fill="currentColor" />
            ) : (
              <Play size={20} fill="currentColor" />
            )}
          </button>

          {/* Time Display */}
          <div className="whitespace-nowrap text-xs text-[#59616a] sm:text-sm">
            {formatTime(currentTime)} / {formatTime(duration)}
          </div>

          {/* Volume Control */}
          <div className="hidden sm:flex items-center gap-2">
            <button
              onClick={() => setIsMuted(!isMuted)}
              className="text-[#737b83] transition-colors hover:text-[#222831]"
            >
              {isMuted || volume === 0 ? (
                <VolumeX size={20} />
              ) : (
                <Volume2 size={20} />
              )}
            </button>
            <input
              type="range"
              min="0"
              max="100"
              value={isMuted ? 0 : volume * 100}
              onChange={(e) => {
                const newVolume = parseInt(e.target.value) / 100;
                setVolume(newVolume);
                setIsMuted(newVolume === 0);
              }}
              className="h-1 w-20 cursor-pointer appearance-none rounded-lg bg-[#e6e2da] accent-[#ed7755]"
            />
          </div>
        </div>
      </div>
      {playbackError && (
        <div className="px-6 pb-3 text-sm text-red-700">{playbackError}</div>
      )}

      {/* Hidden Audio Element */}
      <audio
        key={track?.id}
        ref={audioRef}
        src={resolveAssetUrl(track?.preview_url)}
        autoPlay={isPlaying}
        preload="metadata"
        onCanPlay={() => {
          if (!isPlaying || !audioRef.current) return;
          audioRef.current.play().catch(() => {
            setPlaybackError(t.playbackError);
            onPlayPause(false);
          });
        }}
        onError={() => {
          setPlaybackError(t.loadError);
          onPlayPause(false);
        }}
        onEnded={() => onPlayPause(false)}
      />
    </div>
  );
};

export default AudioPlayer;
