import React, { useEffect, useState } from 'react';
import { Download, ShoppingBag, BadgeCheck, RefreshCw } from 'lucide-react';
import api, { resolveAssetUrl } from '../api';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';

const LICENSE_COLORS = {
  'MP3 Lease': 'bg-blue-600/20 text-blue-300 border-blue-600/40',
  'WAV Commercial': 'bg-purple-600/20 text-purple-300 border-purple-600/40',
  Exclusive: 'bg-amber-600/20 text-amber-300 border-amber-600/40',
};

const UserPurchases = () => {
  const { lang } = useLanguage();
  const { user } = useAuth();
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [downloading, setDownloading] = useState(null);
  const t = {
    couldNotLoad: lang === 'ar' ? 'تعذر تحميل المشتريات.' : 'Could not load purchases.',
    downloadFailed: lang === 'ar' ? 'فشل التنزيل.' : 'Download failed.',
    signInToView: lang === 'ar' ? 'سجّل الدخول لعرض مشترياتك.' : 'Sign in to view your purchases.',
    loading: lang === 'ar' ? 'جاري التحميل...' : 'Loading...',
    reDownload: lang === 'ar' ? 'أعد تنزيل كل التراكات المشتراة من هنا.' : 'Re-download all purchased tracks from here.',
    refresh: lang === 'ar' ? 'تحديث' : 'Refresh',
    noPurchases: lang === 'ar' ? 'لم تقم بشراء أي تراك بعد.' : 'You have not purchased any tracks yet.',
    track: lang === 'ar' ? 'التراك' : 'Track',
    purchaseDate: lang === 'ar' ? 'تاريخ الشراء' : 'Purchase Date',
    license: lang === 'ar' ? 'الرخصة' : 'License',
    download: lang === 'ar' ? 'تنزيل' : 'Download',
    standard: lang === 'ar' ? 'قياسي' : 'Standard',
  };

  const fetchDetails = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.get('/purchases/details');
      setPurchases(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || t.couldNotLoad);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) fetchDetails();
  }, [user]);

  const buildDownloadName = (purchase) => {
    const fallbackExt = 'mp3';
    let extension = fallbackExt;
    try {
      const parsed = new URL(purchase.download_url, window.location.origin);
      const match = parsed.pathname.match(/\.([a-zA-Z0-9]+)$/);
      if (match?.[1]) {
        extension = match[1].toLowerCase();
      }
    } catch {
      extension = fallbackExt;
    }
    return `${purchase.track_title} - ${purchase.track_artist}.${extension}`;
  };

  const handleDownload = async (purchase) => {
    try {
      setDownloading(purchase.track_id);
      const fileResponse = await api.get(`/tracks/${purchase.track_id}/download-file`, { responseType: 'blob' });
      const contentType = (fileResponse.headers && fileResponse.headers['content-type']) || '';
      if (contentType.includes('text/html')) {
        throw new Error('Received HTML instead of media file');
      }
      const blobUrl = window.URL.createObjectURL(fileResponse.data);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = buildDownloadName(purchase);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      setError(err.response?.data?.detail || t.downloadFailed);
    } finally {
      setDownloading(null);
    }
  };

  if (!user) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-12 text-center text-slate-500">
        <ShoppingBag size={40} className="mx-auto mb-4 opacity-40" />
        <p className="font-medium">{t.signInToView}</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-slate-400">
        <RefreshCw size={28} className="animate-spin mr-3" />
        {t.loading}
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-sm text-slate-400">
          {t.reDownload}
        </p>
        <button
          type="button"
          onClick={fetchDetails}
          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-700 transition-colors"
        >
          <RefreshCw size={14} />
          {t.refresh}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-lg bg-red-600/20 border border-red-500 text-red-300 px-4 py-2 text-sm">
          {error}
        </div>
      )}

      {purchases.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900 p-12 text-center text-slate-500">
          <ShoppingBag size={40} className="mx-auto mb-4 opacity-40" />
          <p className="font-medium">{t.noPurchases}</p>
        </div>
      ) : (
        <>
          <div className="space-y-3 md:hidden">
            {purchases.map((purchase) => {
              const licenseClass =
                LICENSE_COLORS[purchase.license_type] ||
                'bg-slate-700/40 text-slate-300 border-slate-600/40';
              return (
                <div key={purchase.id} className="rounded-xl border border-slate-700 bg-slate-900 p-4">
                  <div className="mb-3 flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg flex-shrink-0 overflow-hidden bg-gradient-to-br from-purple-700 to-blue-700">
                      {purchase.cover_image_url ? (
                        <img
                          src={resolveAssetUrl(purchase.cover_image_url)}
                          alt={purchase.track_title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <BadgeCheck size={16} className="text-white/60" />
                        </div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-white truncate text-sm">{purchase.track_title}</p>
                      <p className="text-xs text-slate-400 truncate">{purchase.track_artist}</p>
                    </div>
                  </div>
                  <div className="mb-3 text-xs text-slate-400">
                    {new Date(purchase.purchased_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span
                      className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${licenseClass}`}
                    >
                      {purchase.license_type || t.standard}
                    </span>
                    <button
                      type="button"
                      onClick={() => handleDownload(purchase)}
                      disabled={downloading === purchase.track_id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-2 text-xs font-semibold text-white hover:bg-purple-700 disabled:opacity-60 transition-colors"
                    >
                      <Download size={13} />
                      {downloading === purchase.track_id ? '...' : t.download}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="hidden rounded-2xl border border-slate-700 bg-slate-900 overflow-hidden md:block">
            <div className="grid grid-cols-12 gap-4 px-6 py-3 text-xs font-semibold uppercase tracking-widest text-slate-500 border-b border-slate-800 bg-slate-950">
              <div className="col-span-5">{t.track}</div>
              <div className="col-span-3">{t.purchaseDate}</div>
              <div className="col-span-2">{t.license}</div>
              <div className="col-span-2 text-right">{t.download}</div>
            </div>

            {purchases.map((purchase) => {
              const licenseClass =
                LICENSE_COLORS[purchase.license_type] ||
                'bg-slate-700/40 text-slate-300 border-slate-600/40';
              return (
                <div
                  key={purchase.id}
                  className="grid grid-cols-12 gap-4 px-6 py-4 items-center border-b border-slate-800 last:border-0 hover:bg-slate-800/50 transition-colors"
                >
                  <div className="col-span-5 flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-lg flex-shrink-0 overflow-hidden bg-gradient-to-br from-purple-700 to-blue-700">
                      {purchase.cover_image_url ? (
                        <img
                          src={resolveAssetUrl(purchase.cover_image_url)}
                          alt={purchase.track_title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <BadgeCheck size={16} className="text-white/60" />
                        </div>
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-white truncate text-sm">{purchase.track_title}</p>
                      <p className="text-xs text-slate-400 truncate">{purchase.track_artist}</p>
                    </div>
                  </div>

                  <div className="col-span-3 text-sm text-slate-400">
                    {new Date(purchase.purchased_at).toLocaleDateString('en-US', {
                      year: 'numeric',
                      month: 'short',
                      day: 'numeric',
                    })}
                  </div>

                  <div className="col-span-2">
                    <span
                      className={`inline-block rounded-full border px-2.5 py-0.5 text-xs font-semibold ${licenseClass}`}
                    >
                      {purchase.license_type || t.standard}
                    </span>
                  </div>

                  <div className="col-span-2 flex justify-end">
                    <button
                      type="button"
                      onClick={() => handleDownload(purchase)}
                      disabled={downloading === purchase.track_id}
                      className="inline-flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-2 text-xs font-semibold text-white hover:bg-purple-700 disabled:opacity-60 transition-colors"
                    >
                      <Download size={13} />
                      {downloading === purchase.track_id ? '...' : t.download}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default UserPurchases;
