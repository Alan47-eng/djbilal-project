import React from 'react';
import { Play, ShoppingCart, Download, BadgeCheck, Gift } from 'lucide-react';
import { resolveAssetUrl } from '../api';
import { useLanguage } from '../context/LanguageContext';

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
    ['#312e81', '#7c3aed'],
    ['#1d4ed8', '#6d28d9'],
    ['#4c1d95', '#2563eb'],
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

const TrackCard = ({
  track,
  onPlay,
  onAddToCart,
  onDownload,
  isPurchased,
  isInCart,
}) => {
  const { lang } = useLanguage();
  const isFree = track.is_free === true;
  const canDownloadDirectly = isFree || isPurchased;
  const t = {
    playPreview: lang === 'ar' ? 'تشغيل المعاينة' : 'Play preview',
    downloadTrack: lang === 'ar' ? 'تنزيل التراك' : 'Download track',
    addToCart: lang === 'ar' ? 'أضف إلى السلة' : 'Add to cart',
    addedToCart: lang === 'ar' ? 'أُضيف إلى السلة' : 'Added to cart',
    free: lang === 'ar' ? 'مجاني' : 'Free',
    purchased: lang === 'ar' ? 'تم الشراء' : 'Purchased',
    download: lang === 'ar' ? 'تنزيل' : 'Download',
  };

  return (
    <div className="group cursor-pointer overflow-hidden rounded-2xl border border-white/[0.08] bg-gradient-to-br from-[#302d3e] via-[#242430] to-[#1d2029] shadow-[0_12px_30px_rgba(5,5,12,0.22),inset_0_1px_rgba(255,255,255,0.04)] transition-all duration-300 hover:-translate-y-1 hover:border-violet-400/40 hover:shadow-2xl hover:shadow-violet-950/20">
      {/* Track Cover / Placeholder */}
      <div className="relative aspect-square overflow-hidden bg-[#252331]">
        <img
          src={resolveAssetUrl(track.cover_image_url) || buildCoverArt(track)}
          alt={`${track.title} cover`}
          className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
          loading="lazy"
        />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#17141f]/75 via-transparent to-white/[0.04]" />

        {/* Overlay on hover */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-center justify-center gap-4">
          <button
            onClick={() => onPlay(track)}
            className="rounded-full bg-violet-600 p-4 text-white transition-all duration-200 hover:scale-105 hover:bg-violet-700"
            title={t.playPreview}
          >
            <Play size={24} fill="currentColor" />
          </button>
          {canDownloadDirectly ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="rounded-full bg-violet-600 p-4 text-white transition-all duration-200 hover:scale-105 hover:bg-violet-700"
              title={t.downloadTrack}
            >
              <Download size={24} />
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onAddToCart(track)}
              disabled={isInCart}
              className="rounded-full bg-violet-600 p-4 text-white transition-all duration-200 hover:scale-105 hover:bg-violet-700 disabled:cursor-wait disabled:opacity-60"
              title={isInCart ? t.addedToCart : t.addToCart}
              aria-label={isInCart ? t.addedToCart : t.addToCart}
            >
              {isInCart ? <BadgeCheck size={24} /> : <ShoppingCart size={24} />}
            </button>
          )}
        </div>

        {/* FREE badge */}
        {track.is_free && (
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center gap-1 rounded-lg bg-violet-600 px-2.5 py-1 text-xs font-extrabold text-white shadow-sm">
              <Gift size={12} />
              {t.free.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* Track Info */}
      <div className="bg-gradient-to-b from-transparent to-black/[0.08] p-4 sm:p-5">
        <h3 className="truncate text-lg font-bold text-white transition-colors group-hover:text-violet-200">
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
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/15 px-3 py-1 text-sm font-semibold text-violet-300">
              <Gift size={16} />
              {t.free}
            </span>
          ) : isPurchased ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-violet-500/15 px-3 py-1 text-sm font-semibold text-violet-300">
              <BadgeCheck size={16} />
              {t.purchased}
            </span>
          ) : (
            <span className="text-xl font-bold text-violet-200">
              ${track.price.toFixed(2)}
            </span>
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          {canDownloadDirectly ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-3 text-sm font-semibold text-white hover:bg-violet-700"
            >
              <Download size={16} />
              {t.download}
            </button>
          ) : (
            <button
              type="button"
              onClick={() => onAddToCart(track)}
              disabled={isInCart}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-3 text-sm font-semibold text-white hover:bg-violet-700 disabled:cursor-wait disabled:opacity-60"
            >
              {isInCart ? <BadgeCheck size={16} /> : <ShoppingCart size={16} />}
              {isInCart ? t.addedToCart : t.addToCart}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackCard;
