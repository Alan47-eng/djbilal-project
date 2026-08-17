import React from 'react';
import { Play, ShoppingCart, Download, BadgeCheck, Gift } from 'lucide-react';
import { resolveAssetUrl } from '../api';

function hashString(value) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash);
}

function escapeSvgText(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function buildCoverArt(track) {
  const seed = hashString(`${track.title}:${track.artist}`);
  const colors = [
    ['#7c3aed', '#2563eb'],
    ['#0f172a', '#7c3aed'],
    ['#1d4ed8', '#06b6d4'],
    ['#4c1d95', '#ec4899'],
  ];
  const [start, end] = colors[seed % colors.length];
  const title = track.title || 'Track';
  const artist = track.artist || '';
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 800">
      <defs>
        <linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="${start}" />
          <stop offset="100%" stop-color="${end}" />
        </linearGradient>
      </defs>
      <rect width="800" height="800" fill="url(#g)" />
      <circle cx="640" cy="160" r="120" fill="rgba(255,255,255,0.14)" />
      <circle cx="140" cy="620" r="180" fill="rgba(255,255,255,0.1)" />
      <text x="60" y="585" fill="white" font-family="Arial, Helvetica, sans-serif" font-size="54" font-weight="700">${escapeSvgText(title)}</text>
      <text x="60" y="640" fill="rgba(255,255,255,0.8)" font-family="Arial, Helvetica, sans-serif" font-size="30">${escapeSvgText(artist)}</text>
      <text x="60" y="120" fill="rgba(255,255,255,0.7)" font-family="Arial, Helvetica, sans-serif" font-size="28" letter-spacing="3">DJ BILAL</text>
    </svg>
  `;
  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}

const TrackCard = ({ track, onPlay, onBuy, onDownload, isPurchased }) => {
  const isFree = track.is_free === true;
  const canDownloadDirectly = isFree || isPurchased;

  return (
    <div className="bg-slate-800 rounded-lg overflow-hidden hover:bg-slate-700 transition-colors duration-300 group cursor-pointer">
      {/* Track Cover / Placeholder */}
      <div className="aspect-square bg-gradient-to-br from-purple-600 to-blue-600 relative overflow-hidden">
        <img
          src={resolveAssetUrl(track.cover_image_url) || buildCoverArt(track)}
          alt={`${track.title} cover`}
          className="h-full w-full object-cover"
          loading="lazy"
        />

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center gap-4">
          <button
            onClick={() => onPlay(track)}
            className="bg-purple-600 hover:bg-purple-700 text-white p-4 rounded-full transition-all duration-200 transform hover:scale-110"
            title="Play preview"
          >
            <Play size={24} fill="currentColor" />
          </button>
          <button
            onClick={() => (canDownloadDirectly ? onDownload(track) : onBuy(track))}
            className={`text-white p-4 rounded-full transition-all duration-200 transform hover:scale-110 ${
              canDownloadDirectly ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
            title={canDownloadDirectly ? 'Download track' : 'Buy track'}
          >
            {canDownloadDirectly ? <Download size={24} /> : <ShoppingCart size={24} />}
          </button>
        </div>

        {/* FREE badge */}
        {track.is_free && (
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center gap-1 rounded-lg bg-emerald-500 px-2.5 py-1 text-xs font-extrabold text-white shadow-lg">
              <Gift size={12} />
              FREE
            </span>
          </div>
        )}
      </div>

      {/* Track Info */}
      <div className="p-4">
        <h3 className="font-bold text-lg text-white truncate group-hover:text-purple-400 transition-colors">
          {track.title}
        </h3>
        <p className="text-slate-400 text-sm truncate mb-3">
          {track.artist}
        </p>
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-slate-500">
            {new Date(track.created_at).toLocaleDateString()}
          </span>
          {isFree ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-600/20 px-3 py-1 text-sm font-semibold text-emerald-400">
              <Gift size={16} />
              Free
            </span>
          ) : isPurchased ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-600/20 px-3 py-1 text-sm font-semibold text-emerald-400">
              <BadgeCheck size={16} />
              Purchased
            </span>
          ) : (
            <span className="text-xl font-bold text-purple-400">
              ${track.price.toFixed(2)}
            </span>
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          {canDownloadDirectly ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              <Download size={16} />
              Download
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onBuy(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white hover:bg-purple-700"
            >
              <ShoppingCart size={16} />
              Buy
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackCard;
