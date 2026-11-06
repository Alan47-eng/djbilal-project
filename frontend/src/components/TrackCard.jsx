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
    ['#e88965', '#c95744'],
    ['#edb75f', '#dc784f'],
    ['#52a89b', '#286e70'],
    ['#8c7bd1', '#536db1'],
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
  onBuy,
  onAddToCart,
  onDownload,
  isPurchased,
  checkoutUrl,
  checkoutLoading,
}) => {
  const { lang } = useLanguage();
  const isFree = track.is_free === true;
  const canDownloadDirectly = isFree || isPurchased;
  const t = {
    playPreview: lang === 'ar' ? 'تشغيل المعاينة' : 'Play preview',
    downloadTrack: lang === 'ar' ? 'تنزيل التراك' : 'Download track',
    addToCart: lang === 'ar' ? 'أضف إلى السلة' : 'Sepete Ekle',
    preparingCheckout: lang === 'ar' ? 'جاري التحضير...' : 'Checkout preparing...',
    free: lang === 'ar' ? 'مجاني' : 'Free',
    purchased: lang === 'ar' ? 'تم الشراء' : 'Purchased',
    download: lang === 'ar' ? 'تنزيل' : 'Download',
  };

  return (
    <div className="group cursor-pointer overflow-hidden rounded-2xl border border-[#e4e0d8] bg-white shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-[#f0b39e] hover:shadow-lg">
      {/* Track Cover / Placeholder */}
      <div className="relative aspect-square overflow-hidden bg-[#f1eee8]">
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
            className="rounded-full bg-[#ed7755] p-4 text-white shadow-lg transition-all duration-200 hover:scale-105 hover:bg-[#d96343]"
            title={t.playPreview}
          >
            <Play size={24} fill="currentColor" />
          </button>
          {canDownloadDirectly ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="rounded-full bg-[#167965] p-4 text-white shadow-lg transition-all duration-200 hover:scale-105 hover:bg-[#126453]"
              title={t.downloadTrack}
            >
              <Download size={24} />
            </button>
          ) : checkoutUrl ? (
            <a
              href={checkoutUrl}
              onClick={(event) => onAddToCart(track, event)}
              className="rounded-full bg-[#ed7755] p-4 text-white shadow-lg transition-all duration-200 hover:scale-105 hover:bg-[#d96343]"
              title={t.addToCart}
            >
              <ShoppingCart size={24} />
            </a>
          ) : (
            <button
              type="button"
              onClick={() => onBuy(track)}
              disabled={checkoutLoading}
              className="rounded-full bg-[#ed7755] p-4 text-white shadow-lg transition-all duration-200 hover:scale-105 hover:bg-[#d96343] disabled:opacity-60"
              title={t.addToCart}
            >
              <ShoppingCart size={24} />
            </button>
          )}
        </div>

        {/* FREE badge */}
        {track.is_free && (
          <div className="absolute top-3 left-3">
            <span className="inline-flex items-center gap-1 rounded-lg bg-[#ed7755] px-2.5 py-1 text-xs font-extrabold text-white shadow-sm">
              <Gift size={12} />
              {t.free.toUpperCase()}
            </span>
          </div>
        )}
      </div>

      {/* Track Info */}
      <div className="p-4">
        <h3 className="truncate text-lg font-bold text-[#222831] transition-colors group-hover:text-[#b94c31]">
          {track.title}
        </h3>
        <p className="mb-3 truncate text-sm text-[#727981]">
          {track.artist}
        </p>
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-[#8a9096]">
            {new Date(track.created_at).toLocaleDateString()}
          </span>
          {isFree ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-[#e6f4f1] px-3 py-1 text-sm font-semibold text-[#167965]">
              <Gift size={16} />
              {t.free}
            </span>
          ) : isPurchased ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-[#e6f4f1] px-3 py-1 text-sm font-semibold text-[#167965]">
              <BadgeCheck size={16} />
              {t.purchased}
            </span>
          ) : (
            <span className="text-xl font-bold text-[#b94c31]">
              ${track.price.toFixed(2)}
            </span>
          )}
        </div>

        <div className="mt-4 flex items-center gap-3">
          {canDownloadDirectly ? (
            <button
              type="button"
              onClick={() => onDownload(track)}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#167965] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#126453]"
            >
              <Download size={16} />
              {t.download}
            </button>
          ) : (
            checkoutUrl ? (
              <a
                href={checkoutUrl}
                onClick={(event) => onAddToCart(track, event)}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#ed7755] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#d96343]"
              >
                <ShoppingCart size={16} />
                {t.addToCart}
              </a>
            ) : (
              <button
                type="button"
                onClick={() => onBuy(track)}
                disabled={checkoutLoading}
                className="inline-flex flex-1 items-center justify-center gap-2 rounded-lg bg-[#ed7755] px-4 py-3 text-sm font-semibold text-white transition-colors hover:bg-[#d96343] disabled:cursor-not-allowed disabled:opacity-60"
              >
                <ShoppingCart size={16} />
                {checkoutLoading ? t.preparingCheckout : t.addToCart}
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
};

export default TrackCard;
