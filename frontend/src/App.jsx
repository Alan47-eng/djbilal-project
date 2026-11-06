import React, { useEffect, useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck, Gift, Library, Info } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { PurchaseProvider, usePurchases } from './context/PurchaseContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import { useCheckout } from './hooks/useTrackOperations';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import AdminDrawer from './components/AdminDrawer';
import AboutSection from './components/AboutSection';
import FreeTracksList from './components/FreeTracksList';
import UserPurchases from './components/UserPurchases';
import ResetPassword from './components/ResetPassword';
import './index.css';
import { getApiErrorMessage } from './utils/errors';
import { downloadTrackFile } from './utils/downloads';
import api, { resolveAssetUrl } from './api';

function buildGumroadOverlayUrl(checkoutUrl) {
  const url = new URL(checkoutUrl);
  // Gumroad's embed script intercepts links without wanted=true; that flag bypasses its overlay.
  url.searchParams.delete('wanted');
  url.searchParams.delete('overlay');
  return url.toString();
}

function AppContent() {
  const { lang, setLang, isRTL } = useLanguage();
  const { user, logout, loading: authLoading } = useAuth();
  const { tracks, loading: tracksLoading, error: tracksError } = useTracks();
  const { purchases } = usePurchases();
  const { checkoutCart, loading: checkoutLoading, error: checkoutError } = useCheckout();
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState(() =>
    typeof window !== 'undefined' && window.location.pathname.replace(/\/+$/, '') === '/purchases'
      ? 'library'
      : 'albums'
  ); // 'albums' | 'free' | 'library' | 'about'
  const [gumroadCheckoutItems, setGumroadCheckoutItems] = useState([]);
  const [checkoutPollNonce, setCheckoutPollNonce] = useState(0);
  const [albums, setAlbums] = useState([]);
  const [albumsError, setAlbumsError] = useState('');
  const [selectedAlbumId, setSelectedAlbumId] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const t = {
    free: lang === 'ar' ? 'مجاني' : 'Free',
    myLibrary: lang === 'ar' ? 'مكتبتي' : 'My Library',
    signIn: lang === 'ar' ? 'تسجيل الدخول' : 'Sign In',
    signUp: lang === 'ar' ? 'إنشاء حساب' : 'Sign Up',
    logout: lang === 'ar' ? 'تسجيل الخروج' : 'Logout',
    openAdmin: lang === 'ar' ? 'فتح لوحة الإدارة' : 'Open Admin Panel',
    aboutMe: lang === 'ar' ? 'من أنا' : 'About Me',
    home: lang === 'ar' ? 'الرئيسية' : 'Home',
    freeDownloads: lang === 'ar' ? 'تنزيلات مجانية' : 'Free Downloads',
    freeDesc: lang === 'ar' ? 'تصفح المقاطع والملفات المجانية.' : 'Browse free tracks and downloads.',
    myPurchases: lang === 'ar' ? 'مشترياتي' : 'My Purchases',
    myPurchasesDesc: lang === 'ar' ? 'أعد تنزيل كل التراكات المشتراة في أي وقت.' : 'Re-download all licensed tracks you have purchased anytime from here.',
    albums: lang === 'ar' ? 'الألبومات' : 'Albums',
    albumsDesc: lang === 'ar' ? 'تصفح الألبومات واستمع إلى المقاطع داخل كل ألبوم.' : 'Browse albums and discover the tracks inside each release.',
    albumTracks: lang === 'ar' ? 'مقاطع الألبوم' : 'Album tracks',
    backToAlbums: lang === 'ar' ? 'العودة إلى الألبومات' : 'Back to albums',
    noAlbums: lang === 'ar' ? 'لا توجد ألبومات بعد.' : 'No albums available yet.',
    noAlbumTracks: lang === 'ar' ? 'لا توجد مقاطع في هذا الألبوم بعد.' : 'This album has no tracks yet.',
    albumsLoadFailed: lang === 'ar' ? 'تعذر تحميل الألبومات.' : 'Could not load albums.',
    previewMissing: lang === 'ar' ? 'ملف المعاينة غير متوفر لهذا التراك.' : 'Preview file is missing for this track.',
    fileMissing: lang === 'ar' ? 'الملف غير موجود. يرجى إعادة رفع التراك.' : 'File not found. Please upload the track again.',
    downloadFailed: lang === 'ar' ? 'فشل التنزيل.' : 'Download failed.',
    privacy: lang === 'ar' ? 'سياسة الخصوصية' : 'Privacy Policy',
    terms: lang === 'ar' ? 'شروط الاستخدام' : 'Terms of Service',
    refund: lang === 'ar' ? 'سياسة الاسترجاع' : 'Refund Policy',
    contact: lang === 'ar' ? 'اتصل بنا' : 'Contact Us',
  };

  const isAdmin = user?.is_admin === true;
  const loading = authLoading || tracksLoading;
  const paidTracks = tracks.filter((track) => !track.is_free);
  useEffect(() => {
    if (!user) return undefined;

    let expectedTrackIds;
    try {
      expectedTrackIds = JSON.parse(
        window.sessionStorage.getItem('gumroadCheckoutTrackIds') || '[]'
      );
    } catch {
      window.sessionStorage.removeItem('gumroadCheckoutTrackIds');
      return undefined;
    }

    if (
      !Array.isArray(expectedTrackIds) ||
      expectedTrackIds.length === 0 ||
      expectedTrackIds.some((trackId) => !Number.isInteger(trackId))
    ) {
      window.sessionStorage.removeItem('gumroadCheckoutTrackIds');
      return undefined;
    }

    let cancelled = false;
    let timeoutId;
    const expiresAt = Date.now() + 15 * 60 * 1000;
    const checkPurchase = async () => {
      if (cancelled) return;
      try {
        const response = await api.get('/purchases');
        if (expectedTrackIds.every((trackId) => response.data.includes(trackId))) {
          window.sessionStorage.removeItem('gumroadCheckoutTrackIds');
          if (window.location.pathname.replace(/\/+$/, '') !== '/purchases') {
            window.location.assign('/purchases');
          }
          return;
        }
      } catch (error) {
        console.error('Could not check Gumroad purchase status.', error);
      }

      if (Date.now() >= expiresAt) {
        window.sessionStorage.removeItem('gumroadCheckoutTrackIds');
        return;
      }
      timeoutId = window.setTimeout(checkPurchase, 5000);
    };

    void checkPurchase();
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [user, checkoutPollNonce]);

  useEffect(() => {
    let cancelled = false;
    api.get('/albums')
      .then((response) => {
        if (!cancelled) setAlbums(response.data);
      })
      .catch((error) => {
        if (!cancelled) {
          setAlbumsError(getApiErrorMessage(error, t.albumsLoadFailed));
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    if (!user) {
      setGumroadCheckoutItems([]);
      return;
    }

    const trackIds = paidTracks
      .filter((track) => !purchases.includes(track.id))
      .map((track) => track.id);
    if (trackIds.length === 0) {
      setGumroadCheckoutItems([]);
      return;
    }

    let cancelled = false;
    checkoutCart(trackIds).then((items) => {
      if (!cancelled) setGumroadCheckoutItems(items || []);
    });

    return () => {
      cancelled = true;
    };
  }, [user, tracks, purchases, checkoutCart]);

  const renderTrackGrid = (tracksToRender, emptyMessage) => {
    if (tracksToRender.length === 0) {
      return (
        <div className="rounded-2xl border border-dashed border-[#ddd8ce] bg-white p-8 text-center text-[#626a72]">
          {emptyMessage}
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-32">
        {tracksToRender.map((track) => {
          const checkoutItem = gumroadCheckoutItems.find(
            (item) => item.track_id === track.id
          );
          return (
            <TrackCard
              key={track.id}
              track={track}
              isPurchased={purchases.includes(track.id)}
              checkoutUrl={
                checkoutItem
                  ? buildGumroadOverlayUrl(checkoutItem.checkout_url)
                  : null
              }
              checkoutLoading={checkoutLoading}
              onPlay={handlePlayPreview}
              onBuy={handleBuyTrack}
              onAddToCart={rememberTrackForCheckout}
              onDownload={handleDownloadTrack}
            />
          );
        })}
      </div>
    );
  };

  const handlePlayPreview = (track) => {
    if (!track?.preview_url) {
      setDownloadError(t.previewMissing);
      return;
    }
    setDownloadError(null);
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const handleBuyTrack = async (track) => {
    if (!user) {
      setAuthModal({ isOpen: true, mode: 'login' });
      return;
    }

    const items = await checkoutCart([track.id]);
    if (!items?.length) return;
    setGumroadCheckoutItems((current) => [
      ...current.filter((item) => item.track_id !== track.id),
      ...items,
    ]);
  };

  function rememberTrackForCheckout(track, event) {
    if (!user) {
      event.preventDefault();
      setAuthModal({ isOpen: true, mode: 'login' });
      return;
    }

    try {
      window.sessionStorage.setItem(
        'gumroadCheckoutTrackIds',
        JSON.stringify([track.id])
      );
      setCheckoutPollNonce((current) => current + 1);
    } catch (error) {
      console.error('Could not save Gumroad checkout tracking data.', error);
    }
  }

  const handleDownloadTrack = async (track) => {
    try {
      setDownloadError(null);

      if (!track.is_free && !user) {
        setAuthModal({ isOpen: true, mode: 'login' });
        return;
      }

      await downloadTrackFile({
        id: track.id,
        isFree: track.is_free,
        title: track.title,
        artist: track.artist,
      });
    } catch (err) {
      setDownloadError(getApiErrorMessage(err, t.downloadFailed));
    }
  };

  const handleLogout = () => {
    logout();
    window.sessionStorage.removeItem('gumroadCheckoutTrackIds');
    setIsPlaying(false);
    setCurrentTrack(null);
    setGumroadCheckoutItems([]);
    setDownloadError(null);
    setMenuOpen(false);
  };

  return (
    <div className={`min-h-screen bg-[#f7f5f0] text-[#222831] ${isRTL ? 'text-right' : ''}`}>
      {/* Header */}
      <header className="sticky top-0 z-40 border-b border-[#e5e1d9] bg-white/95 shadow-sm backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="rounded-lg border border-[#dedbd4] p-2 text-[#4c535b] transition-colors hover:bg-[#f1eee8] hover:text-[#222831]"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="rounded-xl bg-[#ed7755] p-2 shadow-sm">
              <Music size={28} className="text-white" />
            </div>
            <button
              type="button"
              onClick={() => {
                setActiveTab('albums');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className="text-left"
            >
              <h1 className="text-lg font-bold tracking-tight text-[#222831] sm:text-2xl">
                DJ Bilal Music Store
              </h1>
            </button>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center rounded-lg border border-[#dedbd4] bg-[#f7f5f0] p-1 text-xs">
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'en' ? 'bg-[#222831] text-white' : 'text-[#626970] hover:text-[#222831]'}`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang('ar')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'ar' ? 'bg-[#222831] text-white' : 'text-[#626970] hover:text-[#222831]'}`}
              >
                AR
              </button>
            </div>
            {user ? (
              <>
                <div className="hidden md:flex items-center gap-2 text-[#555d65]">
                  <User size={18} className="text-[#ed7755]" />
                  <span>{user.email}</span>
                  {isAdmin && (
                    <span className="rounded-full bg-[#fff0e9] px-2.5 py-1 text-xs font-semibold text-[#b94c31]">
                      <span className="inline-flex items-center gap-1"><ShieldCheck size={12} /> Admin</span>
                    </span>
                  )}
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 rounded-lg bg-[#222831] px-3 py-2 text-sm font-semibold text-white transition-colors duration-200 hover:bg-[#39414b] sm:px-4 sm:text-base"
                >
                  <LogOut size={18} />
                  <span className="hidden sm:inline">{t.logout}</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'login' })}
                  className="flex items-center gap-2 rounded-lg border border-[#dedbd4] bg-white px-3 py-2 text-sm font-semibold text-[#303740] transition-colors duration-200 hover:bg-[#f3f1ec] sm:px-4 sm:text-base"
                >
                  <LogIn size={18} />
                  <span className="hidden sm:inline">{t.signIn}</span>
                </button>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'register' })}
                  className="flex items-center gap-2 rounded-lg bg-[#ed7755] px-3 py-2 text-sm font-semibold text-white shadow-sm transition-colors duration-200 hover:bg-[#d96343] sm:px-4 sm:text-base"
                >
                  <UserPlus size={18} />
                  <span className="hidden sm:inline">{t.signUp}</span>
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">
        {downloadError && (
            <div className="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {downloadError}
          </div>
        )}

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
               setActiveTab('albums');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
             className="inline-flex items-center gap-2 rounded-lg border border-[#dedbd4] bg-white px-3 py-2 text-sm font-semibold text-[#343b43] shadow-sm transition hover:border-[#ed7755]"
          >
            <LayoutGrid size={15} />
            {t.home}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('about')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
              activeTab === 'about'
                ? 'border-[#ed7755] bg-[#fff0e9] text-[#b94c31]'
                : 'border-[#dedbd4] bg-white text-[#4e5660] hover:bg-[#f3f1ec]'
            }`}
          >
            <Info size={15} />
            {t.aboutMe}
          </button>
          {user && (
            <button
              type="button"
              onClick={() => setActiveTab('library')}
              className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
                activeTab === 'library'
                ? 'border-[#ed7755] bg-[#fff0e9] text-[#b94c31]'
                : 'border-[#dedbd4] bg-white text-[#4e5660] hover:bg-[#f3f1ec]'
              }`}
            >
              <Library size={15} />
              {t.myLibrary}
            </button>
          )}
        </div>

        {/* Tab Navigation */}
        <nav className="mb-6 sm:mb-8 flex max-w-full items-center gap-1 overflow-x-auto rounded-xl border border-[#e4e0d8] bg-white p-1 shadow-sm">
          {[
             { id: 'albums', label: t.albums, icon: <Library size={15} /> },
             { id: 'free', label: t.free, icon: <Gift size={15} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                if (tab.id === 'library' && !user) {
                  setAuthModal({ isOpen: true, mode: 'login' });
                  return;
                }
                setActiveTab(tab.id);
              }}
              className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-3 sm:px-4 py-2 text-sm font-semibold transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-[#ed7755] text-white shadow-sm'
                  : 'text-[#646b72] hover:bg-[#f3f1ec] hover:text-[#222831]'
              }`}
            >
              {tab.icon}
              {tab.label}
            </button>
          ))}
        </nav>

        {loading ? (
          <div className="flex justify-center items-center h-96">
            <div className="animate-spin">
              <Music size={48} className="text-[#ed7755]" />
            </div>
          </div>
        ) : tracksError ? (
          <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
            {tracksError}
          </div>
        ) : (
          <>
            {isAdmin && activeTab !== 'library' && activeTab !== 'about' && (
              <section className="mb-8 flex justify-end">
                <button
                  type="button"
                  onClick={() => setMenuOpen(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-[#ed7755] px-4 py-3 font-semibold text-white shadow-sm transition hover:bg-[#d96343]"
                >
                  <ShieldCheck size={16} />
                  {t.openAdmin}
                </button>
              </section>
            )}

            {activeTab === 'albums' && (
              <section className="pb-32">
                {selectedAlbumId ? (() => {
                  const album = albums.find((item) => item.id === selectedAlbumId);
                  const albumTracks = tracks.filter((track) => track.album_id === selectedAlbumId);
                  return (
                    <>
                      <button
                        type="button"
                        onClick={() => setSelectedAlbumId(null)}
                         className="mb-5 rounded-lg border border-[#dedbd4] bg-white px-4 py-2 text-sm text-[#3d454e] transition hover:bg-[#f1eee8]"
                      >
                        {t.backToAlbums}
                      </button>
                      <div className="mb-6 flex items-center gap-5">
                        {album?.cover_image_url && (
                          <img
                            src={resolveAssetUrl(album.cover_image_url)}
                            alt={`${album.title} cover`}
                            className="h-24 w-24 rounded-xl object-cover shadow-sm ring-1 ring-black/5"
                          />
                        )}
                        <div>
                           <p className="text-sm font-semibold text-[#c65a3d]">{t.albumTracks}</p>
                          <h2 className="mt-1 text-2xl font-bold text-[#222831]">{album?.title}</h2>
                          {album?.release_date && (
                            <p className="mt-1 text-sm text-slate-400">
                              {new Date(album.release_date).toLocaleDateString(lang === 'ar' ? 'ar' : 'en')}
                            </p>
                          )}
                        </div>
                      </div>
                      {renderTrackGrid(albumTracks, t.noAlbumTracks)}
                    </>
                  );
                })() : (
                  <>
                    <div className="mb-6">
                      <h2 className="text-2xl font-bold tracking-tight text-[#222831]">{t.albums}</h2>
                      <p className="mt-1 text-sm text-[#68717a]">{t.albumsDesc}</p>
                    </div>
                    {albumsError ? (
                      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
                        {albumsError}
                      </div>
                    ) : albums.length ? (
                      <div className="grid grid-cols-1 gap-6 pb-32 sm:grid-cols-2 lg:grid-cols-3">
                        {albums.map((album) => {
                          const albumTrackCount = tracks.filter((track) => track.album_id === album.id).length;
                          return (
                            <button
                              key={album.id}
                              type="button"
                              onClick={() => setSelectedAlbumId(album.id)}
                                className="group overflow-hidden rounded-xl border border-[#e4e0d8] bg-white text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-[#f0b39e] hover:shadow-md"
                            >
                              {album.cover_image_url ? (
                                <img
                                  src={resolveAssetUrl(album.cover_image_url)}
                                  alt={`${album.title} cover`}
                                  className="aspect-square w-full object-cover"
                                  loading="lazy"
                                />
                              ) : (
                                <div className="flex aspect-square items-center justify-center bg-[#f1eee8]">
                                  <Music size={48} className="text-[#d17b5c]" />
                                </div>
                              )}
                              <div className="p-4">
                                <h3 className="truncate text-lg font-bold text-[#222831] group-hover:text-[#b94c31]">{album.title}</h3>
                                <p className="mt-1 text-sm text-[#727981]">
                                  {albumTrackCount} · {album.release_date
                                    ? new Date(album.release_date).toLocaleDateString(lang === 'ar' ? 'ar' : 'en')
                                    : t.albums}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-dashed border-[#ddd8ce] bg-white p-8 text-center text-[#626a72]">
                        {t.noAlbums}
                      </div>
                    )}
                  </>
                )}
              </section>
            )}

            {/* Free tab */}
            {activeTab === 'free' && (
              <section>
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-[#fff0e9] px-3 py-1 text-xs font-semibold text-[#b94c31]">
                    <Gift size={12} />
                    {t.free}
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-[#222831]">{t.freeDownloads}</h2>
                  <p className="mt-1 max-w-xl text-sm text-[#68717a]">
                    {t.freeDesc}
                  </p>
                </div>
                <FreeTracksList tracks={tracks} onPlay={handlePlayPreview} />
              </section>
            )}

            {/* About tab */}
            {activeTab === 'about' && (
              <section className="pb-32">
                <AboutSection />
              </section>
            )}

            {/* My Library tab */}
            {activeTab === 'library' && (
              <section className="pb-32">
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-[#e6f4f1] px-3 py-1 text-xs font-semibold text-[#167965]">
                    <Library size={12} />
                    {t.myLibrary}
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-[#222831]">{t.myPurchases}</h2>
                  <p className="mt-1 max-w-xl text-sm text-[#68717a]">
                    {t.myPurchasesDesc}
                  </p>
                </div>
                <UserPurchases />
              </section>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-[#e5e1d9] bg-white">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 px-4 sm:px-6 py-6 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
          <p>© {new Date().getFullYear()} DJ Bilal Music Store</p>
          <div className="flex flex-wrap items-center gap-4">
            <a
              href="/privacy-policy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t.privacy}
            </a>
            <a
              href="/terms-of-use.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t.terms}
            </a>
            <a
              href="/refund-policy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t.refund}
            </a>
            <a
              href="/contact-us.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              {t.contact}
            </a>
          </div>
        </div>
      </footer>

      {/* Player */}
      {currentTrack && (
        <div className="fixed bottom-0 left-0 right-0 border-t border-[#e0dcd4] bg-white shadow-[0_-8px_24px_rgba(34,40,49,0.08)]">
          <AudioPlayer track={currentTrack} isPlaying={isPlaying} onPlayPause={setIsPlaying} />
        </div>
      )}

      {checkoutError && (
        <div className="fixed bottom-4 left-4 right-4 z-40 rounded-lg border border-red-600 bg-red-900/90 px-4 py-3 text-sm text-red-100 md:left-auto md:max-w-md">
          {checkoutError}
        </div>
      )}

      {/* Modals */}
      <AuthModal
        isOpen={authModal.isOpen}
        mode={authModal.mode}
        onClose={() => setAuthModal({ ...authModal, isOpen: false })}
        onSuccess={() => setAuthModal({ isOpen: false, mode: 'login' })}
      />
      <AdminDrawer
        isOpen={menuOpen}
        onClose={() => setMenuOpen(false)}
        activeTab={activeTab}
        onNavigate={(tabId) => {
          setActiveTab(tabId);
          setMenuOpen(false);
        }}
        onOpenAuth={(mode) => {
          setMenuOpen(false);
          setAuthModal({ isOpen: true, mode });
        }}
        onLogout={handleLogout}
      />
    </div>
  );
}

export default function App() {
  // If user opened /reset-password, render just the reset page within providers
  if (typeof window !== 'undefined' && window.location.pathname.startsWith('/reset-password')) {
    return (
      <LanguageProvider>
        <AuthProvider>
          <ResetPassword />
        </AuthProvider>
      </LanguageProvider>
    );
  }

  return (
    <LanguageProvider>
      <AuthProvider>
        <TrackProvider>
          <PurchaseProvider>
            <AppContent />
          </PurchaseProvider>
        </TrackProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}
