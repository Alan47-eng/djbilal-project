import React, { useState } from 'react';
import { Download, Play, Gift } from 'lucide-react';
import { resolveAssetUrl } from '../api';
import { useLanguage } from '../context/LanguageContext';
import { getApiErrorMessage } from '../utils/errors';
import { downloadTrackFile } from '../utils/downloads';

const FreeTracksList = ({ tracks, onPlay }) => {
  const { lang } = useLanguage();
  const freeTracks = tracks.filter((t) => t.is_free);
  const [activeCategory, setActiveCategory] = useState('all');
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState(null);
  const t = {
    noFreeTracks: lang === 'ar' ? 'لا توجد تراكات مجانية بعد.' : 'No free tracks have been added yet.',
    intro: lang === 'ar' ? 'نزّل الملفات المجانية بالأسفل بضغطة واحدة وبدون تسجيل.' : 'Download the files below for free — one click, no signup required.',
    all: lang === 'ar' ? 'الكل' : 'All',
    simplePack: lang === 'ar' ? 'حزمة بسيطة' : 'Simple Pack',
    noCategory: lang === 'ar' ? 'لا توجد ملفات مجانية في هذا التصنيف بعد.' : 'No free files in this category yet.',
    preview: lang === 'ar' ? 'معاينة' : 'Preview',
    downloading: lang === 'ar' ? 'جاري التنزيل...' : 'Downloading...',
    download: lang === 'ar' ? 'تنزيل' : 'Download',
    downloadFailed: lang === 'ar' ? 'فشل التنزيل.' : 'Download failed.',
    free: lang === 'ar' ? 'مجاني' : 'FREE',
    vst: 'VST',
  };

  const belongsToCategory = (track, category) => {
    if (category === 'all') return true;
    const normalizedCategory = (track.category || '').toLowerCase();
    if (normalizedCategory) {
      if (category === 'simple-pack') return normalizedCategory === 'simple-pack';
      if (category === 'vst') return normalizedCategory === 'vst';
    }
    const text = `${track.title} ${track.artist}`.toLowerCase();

    if (category === 'simple-pack') {
      return (
        text.includes('simple pack') ||
        text.includes('simple back') ||
        text.includes('backing') ||
        text.includes('back track') ||
        text.includes('backtrack')
      );
    }
    if (category === 'vst') return text.includes('vst');
    return true;
  };

  const filteredTracks = freeTracks.filter((track) => belongsToCategory(track, activeCategory));

  const buildDownloadName = (track, sourceUrl) => {
    const fallbackExt = 'mp3';
    let extension = fallbackExt;
    try {
      const parsed = new URL(sourceUrl, window.location.origin);
      const match = parsed.pathname.match(/\.([a-zA-Z0-9]+)$/);
      if (match?.[1]) {
        extension = match[1].toLowerCase();
      }
    } catch {
      extension = fallbackExt;
    }
    return `${track.title} - ${track.artist}.${extension}`;
  };

  const handleFreeDownload = async (track) => {
    try {
      setDownloading(track.id);
      setError(null);
      const sourceRef = track.full_file_path || track.preview_url || '';
      await downloadTrackFile({
        id: track.id,
        isFree: true,
        title: track.title,
        artist: track.artist,
      });
    } catch (err) {
      setError(getApiErrorMessage(err, t.downloadFailed));
    } finally {
      setDownloading(null);
    }
  };

  if (freeTracks.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-[#ddd8ce] bg-white p-10 text-center text-[#626a72]">
        <Gift size={36} className="mx-auto mb-3 opacity-40" />
        <p>{t.noFreeTracks}</p>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-4 text-sm text-[#68717a]">
        {t.intro}
      </p>

      <div className="mb-5 flex flex-wrap gap-2">
        {[
          { id: 'all', label: t.all },
          { id: 'simple-pack', label: t.simplePack },
          { id: 'vst', label: t.vst },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActiveCategory(item.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              activeCategory === item.id
                ? 'bg-[#222831] text-white'
                : 'border border-[#e4e0d8] bg-white text-[#626a72] hover:bg-[#f1eee8]'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {filteredTracks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#ddd8ce] bg-white p-8 text-center text-[#626a72]">
          {t.noCategory}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTracks.map((track) => (
          <div
            key={track.id}
            className="flex items-center gap-4 rounded-2xl border border-[#e4e0d8] bg-white p-4 shadow-sm transition-all duration-200 hover:border-[#f0b39e] hover:shadow-md"
          >
            {/* Cover */}
            <div className="relative h-16 w-16 flex-shrink-0 overflow-hidden rounded-xl bg-[#f1eee8]">
              {track.cover_image_url ? (
                <img
                  src={resolveAssetUrl(track.cover_image_url)}
                  alt={track.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Gift size={24} className="text-[#d17b5c]" />
                </div>
              )}
              {/* FREE badge */}
              <span className="absolute left-1 top-1 rounded-md bg-[#167965] px-1.5 py-0.5 text-[10px] font-extrabold leading-none text-white shadow">
                {t.free}
              </span>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="truncate font-semibold text-[#222831]">{track.title}</p>
              <p className="truncate text-sm text-[#727981]">{track.artist}</p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={() => onPlay(track)}
                className="rounded-lg border border-[#dedbd4] bg-white p-2 text-[#555d65] transition-colors hover:bg-[#f1eee8] hover:text-[#222831]"
                title={t.preview}
              >
                <Play size={16} fill="currentColor" />
              </button>
              <button
                type="button"
                onClick={() => handleFreeDownload(track)}
                disabled={downloading === track.id}
                className="inline-flex items-center gap-1.5 rounded-lg bg-[#167965] px-3 py-2 text-sm font-semibold text-white transition-colors hover:bg-[#126453] disabled:opacity-60"
              >
                <Download size={15} />
                {downloading === track.id ? t.downloading : t.download}
              </button>
            </div>
          </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default FreeTracksList;
