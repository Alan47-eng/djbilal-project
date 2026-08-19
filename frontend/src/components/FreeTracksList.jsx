import React, { useState } from 'react';
import { Download, Play, Gift } from 'lucide-react';
import api, { resolveAssetUrl } from '../api';

const FreeTracksList = ({ tracks, onPlay }) => {
  const freeTracks = tracks.filter((t) => t.is_free);
  const [activeCategory, setActiveCategory] = useState('all');
  const [downloading, setDownloading] = useState(null);
  const [error, setError] = useState(null);

  const belongsToCategory = (track, category) => {
    if (category === 'all') return true;
    const normalizedCategory = (track.category || '').toLowerCase();
    if (normalizedCategory) {
      if (category === 'remix') return normalizedCategory === 'remix';
      if (category === 'simple-pack') return normalizedCategory === 'simple-pack';
      if (category === 'vst') return normalizedCategory === 'vst';
    }
    const text = `${track.title} ${track.artist}`.toLowerCase();

    if (category === 'remix') return text.includes('remix');
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
      const fileResponse = await api.get(`/tracks/${track.id}/free-download-file`, { responseType: 'blob' });
      const contentType = (fileResponse.headers && fileResponse.headers['content-type']) || '';
      if (contentType.includes('text/html')) {
        throw new Error('Received HTML instead of media file');
      }
      const blobUrl = window.URL.createObjectURL(fileResponse.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = buildDownloadName(track, sourceRef);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      setError(err.response?.data?.detail || 'Download failed.');
    } finally {
      setDownloading(null);
    }
  };

  if (freeTracks.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-10 text-center text-slate-500">
        <Gift size={36} className="mx-auto mb-3 opacity-40" />
        <p>No free tracks have been added yet.</p>
      </div>
    );
  }

  return (
    <div>
      <p className="mb-4 text-sm text-slate-400">
        Download the files below for free — one click, no signup required.
      </p>

      <div className="mb-5 flex flex-wrap gap-2">
        {[
          { id: 'all', label: 'All' },
          { id: 'remix', label: 'Remix' },
          { id: 'simple-pack', label: 'Simple Pack' },
          { id: 'vst', label: 'VST' },
        ].map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => setActiveCategory(item.id)}
            className={`rounded-lg px-3 py-1.5 text-sm font-semibold transition-colors ${
              activeCategory === item.id
                ? 'bg-emerald-600 text-white'
                : 'bg-slate-800 text-slate-300 hover:bg-slate-700'
            }`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-600/20 border border-red-500 text-red-300 px-4 py-2 text-sm">
          {error}
        </div>
      )}

      {filteredTracks.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-8 text-center text-slate-500">
          No free files in this category yet.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {filteredTracks.map((track) => (
          <div
            key={track.id}
            className="flex items-center gap-4 rounded-2xl border border-emerald-700/30 bg-gradient-to-r from-slate-800 to-slate-900 p-4 hover:border-emerald-600/60 transition-all duration-200"
          >
            {/* Cover */}
            <div className="relative w-16 h-16 flex-shrink-0 rounded-xl overflow-hidden bg-gradient-to-br from-emerald-800 to-teal-700">
              {track.cover_image_url ? (
                <img
                  src={resolveAssetUrl(track.cover_image_url)}
                  alt={track.title}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center">
                  <Gift size={24} className="text-emerald-300" />
                </div>
              )}
              {/* FREE badge */}
              <span className="absolute top-1 left-1 rounded-md bg-emerald-500 px-1.5 py-0.5 text-[10px] font-extrabold text-white leading-none shadow">
                FREE
              </span>
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-white truncate">{track.title}</p>
              <p className="text-sm text-slate-400 truncate">{track.artist}</p>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={() => onPlay(track)}
                className="rounded-lg border border-slate-700 bg-slate-800 p-2 text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
                title="Preview"
              >
                <Play size={16} fill="currentColor" />
              </button>
              <button
                type="button"
                onClick={() => handleFreeDownload(track)}
                disabled={downloading === track.id}
                className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-60 transition-colors"
              >
                <Download size={15} />
                {downloading === track.id ? 'Downloading...' : 'Download'}
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
