import React from 'react';
import { Play, ShoppingCart, Music, Download, BadgeCheck } from 'lucide-react';

const TrackCard = ({ track, onPlay, onBuy, onDownload, isPurchased }) => {
  return (
    <div className="bg-slate-800 rounded-lg overflow-hidden hover:bg-slate-700 transition-colors duration-300 group cursor-pointer">
      {/* Track Cover / Placeholder */}
      <div className="aspect-square bg-gradient-to-br from-purple-600 to-blue-600 relative overflow-hidden">
        {track.cover_image_url ? (
          <img
            src={track.cover_image_url}
            alt={`${track.title} cover`}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center">
            <Music size={64} className="text-slate-300 opacity-50" />
          </div>
        )}

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
            onClick={() => (isPurchased ? onDownload(track) : onBuy(track))}
            className={`text-white p-4 rounded-full transition-all duration-200 transform hover:scale-110 ${
              isPurchased ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-blue-600 hover:bg-blue-700'
            }`}
            title={isPurchased ? 'Download track' : 'Buy track'}
          >
            {isPurchased ? <Download size={24} /> : <ShoppingCart size={24} />}
          </button>
        </div>
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
          {isPurchased ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-600/20 px-3 py-1 text-sm font-semibold text-emerald-400">
              <BadgeCheck size={16} />
              Satın Alındı
            </span>
          ) : (
            <span className="text-xl font-bold text-purple-400">
              ${track.price.toFixed(2)}
            </span>
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          {isPurchased ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-3 text-sm font-semibold text-white hover:bg-emerald-700"
            >
              <Download size={16} />
              İndir
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onBuy(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 text-sm font-semibold text-white hover:bg-purple-700"
            >
              <ShoppingCart size={16} />
              Satın Al
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackCard;
