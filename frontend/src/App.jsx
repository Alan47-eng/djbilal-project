import React, { useEffect, useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck, Gift, Library, Info, ShoppingCart } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { LanguageProvider, useLanguage } from './context/LanguageContext';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import AdminDrawer from './components/AdminDrawer';
import AboutSection from './components/AboutSection';
import FreeTracksList from './components/FreeTracksList';
import ShopierCheckoutModal from './components/ShopierCheckoutModal';
import ResetPassword from './components/ResetPassword';
import './index.css';
import { getApiErrorMessage } from './utils/errors';
import { downloadTrackFile } from './utils/downloads';
import api, { resolveAssetUrl } from './api';

function AppContent() {
  const { lang, setLang, isRTL } = useLanguage();
  const { user, logout, loading: authLoading } = useAuth();
  const { tracks, loading: tracksLoading, error: tracksError } = useTracks();
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('albums'); // 'albums' | 'free' | 'about'
  const [albums, setAlbums] = useState([]);
  const [albumsError, setAlbumsError] = useState('');
  const [selectedAlbumId, setSelectedAlbumId] = useState(null);
  const [downloadError, setDownloadError] = useState(null);
  const [cartTracks, setCartTracks] = useState([]);
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [checkoutBusy, setCheckoutBusy] = useState(false);
  const t = {
    free: lang === 'ar' ? 'مجاني' : 'Free',
    signIn: lang === 'ar' ? 'تسجيل الدخول' : 'Sign In',
    signUp: lang === 'ar' ? 'إنشاء حساب' : 'Sign Up',
    logout: lang === 'ar' ? 'تسجيل الخروج' : 'Logout',
    openAdmin: lang === 'ar' ? 'فتح لوحة الإدارة' : 'Open Admin Panel',
    aboutMe: lang === 'ar' ? 'من أنا' : 'About Me',
    home: lang === 'ar' ? 'الرئيسية' : 'Home',
    freeDownloads: lang === 'ar' ? 'تنزيلات مجانية' : 'Free Downloads',
    freeDesc: lang === 'ar' ? 'تصفح المقاطع والملفات المجانية.' : 'Browse free tracks and downloads.',
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
    cart: lang === 'ar' ? 'سلة التسوق' : 'Cart',
    addedToCart: lang === 'ar' ? 'تمت الإضافة إلى السلة' : 'Added to cart',
  };

  const isAdmin = user?.is_admin === true;
  const loading = authLoading || tracksLoading;
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
  const renderTrackGrid = (tracksToRender, emptyMessage) => {
    if (tracksToRender.length === 0) {
      return (
        <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-300">
          {emptyMessage}
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-32">
        {tracksToRender.map((track) => {
          return (
            <TrackCard
              key={track.id}
              track={track}
              onPlay={handlePlayPreview}
              onDownload={handleDownloadTrack}
              onAddToCart={(selectedTrack) => {
                setCartTracks((current) => (
                  current.some((item) => item.id === selectedTrack.id)
                    ? current
                    : [...current, selectedTrack]
                ));
                setDownloadError(null);
              }}
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

  const handleOpenCart = () => {
    if (!user) {
      setAuthModal({ isOpen: true, mode: 'login' });
      return;
    }
    setCheckoutOpen(true);
  };

  const handleShopierCheckout = async (checkoutDetails) => {
    setCheckoutBusy(true);
    try {
      const response = await api.post('/api/v1/checkout/shopier/init', checkoutDetails);
      return response.data;
    } finally {
      setCheckoutBusy(false);
    }
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setDownloadError(null);
    setMenuOpen(false);
  };

  return (
    <div className={`store-shell text-[#f3f0e9] ${isRTL ? 'text-right' : ''}`}>
      {/* Header */}
      <header className="store-header sticky top-0 z-40 border-b border-violet-300/10 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="rounded-lg border border-[#41464b] p-2 text-[#c5c7c8] hover:bg-[#303438] hover:text-white"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="rounded-xl bg-gradient-to-br from-violet-500 to-indigo-700 p-2 shadow-lg shadow-violet-950/40 ring-1 ring-white/10">
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
              <h1 className="text-lg font-bold text-[#f3f0e9] sm:text-2xl">
                DJ Bilal Music Store
              </h1>
            </button>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center rounded-lg border border-white/10 bg-[#181821]/80 p-1 text-xs shadow-inner">
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'en' ? 'bg-violet-600 text-white' : 'text-slate-300'}`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang('ar')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'ar' ? 'bg-violet-600 text-white' : 'text-slate-300'}`}
              >
                AR
              </button>
            </div>
            {user ? (
              <>
                <div className="hidden md:flex items-center gap-2 text-slate-300">
                  <User size={18} className="text-violet-300" />
                  <span>{user.email}</span>
                  {isAdmin && (
                    <span className="rounded-full bg-violet-500/15 px-2 py-0.5 text-xs font-semibold text-violet-300">
                      <span className="inline-flex items-center gap-1"><ShieldCheck size={12} /> Admin</span>
                    </span>
                  )}
                </div>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-3 sm:px-4 py-2 rounded-lg transition-colors duration-200 font-semibold text-sm sm:text-base"
                >
                  <LogOut size={18} />
                  <span className="hidden sm:inline">{t.logout}</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'login' })}
                  className="flex items-center gap-2 rounded-lg bg-[#383c40] px-3 py-2 text-sm font-semibold text-white transition-colors duration-200 hover:bg-[#484d52] sm:px-4 sm:text-base"
                >
                  <LogIn size={18} />
                  <span className="hidden sm:inline">{t.signIn}</span>
                </button>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'register' })}
                   className="flex items-center gap-2 rounded-lg bg-gradient-to-r from-violet-600 to-purple-600 px-3 py-2 text-sm font-semibold text-white shadow-lg shadow-violet-950/30 transition-all duration-200 hover:from-violet-500 hover:to-purple-500 sm:px-4 sm:text-base"
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
          <div className="mb-6 rounded-lg border border-red-500 bg-red-600/20 px-4 py-3 text-sm text-red-200">
            {downloadError}
          </div>
        )}

        <div className="mb-5 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
               setActiveTab('albums');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
             className="inline-flex items-center gap-2 rounded-lg border border-[#41464b] bg-[#222529] px-3 py-2 text-sm font-semibold text-[#d4d2cc]"
          >
            <LayoutGrid size={15} />
            {t.home}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('about')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
              activeTab === 'about'
                ? 'border-violet-500 bg-violet-500/15 text-violet-200'
                : 'border-[#41464b] bg-[#222529] text-[#c5c7c8] hover:bg-[#303438]'
            }`}
          >
            <Info size={15} />
            {t.aboutMe}
          </button>
        </div>

        {/* Tab Navigation */}
        <nav className="mb-8 flex max-w-full items-center gap-1 overflow-x-auto rounded-2xl border border-white/[0.07] bg-gradient-to-r from-[#24232f] via-[#22222d] to-[#1d2029] p-1.5 shadow-lg shadow-black/10">
          {[
             { id: 'albums', label: t.albums, icon: <Library size={15} /> },
             { id: 'free', label: t.free, icon: <Gift size={15} /> },
          ].map((tab) => (
            <button
              key={tab.id}
              type="button"
              onClick={() => {
                setActiveTab(tab.id);
              }}
              className={`inline-flex shrink-0 items-center gap-2 rounded-xl px-3 sm:px-4 py-2 text-sm font-semibold transition-all duration-200 ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-violet-600 to-purple-600 text-white shadow-lg shadow-violet-950/40 ring-1 ring-white/10'
                  : 'text-[#b9b8c5] hover:bg-white/[0.06] hover:text-white'
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
              <Music size={48} className="text-violet-300" />
            </div>
          </div>
        ) : tracksError ? (
          <div className="bg-red-600/20 border border-red-500 text-red-200 p-4 rounded-lg">
            {tracksError}
          </div>
        ) : (
          <>
            {isAdmin && activeTab !== 'about' && (
              <section className="mb-8 flex justify-end">
                <button
                  type="button"
                  onClick={() => setMenuOpen(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-3 font-semibold text-white hover:bg-violet-700"
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
                         className="mb-5 rounded-lg border border-[#41464b] px-4 py-2 text-sm text-slate-200 hover:bg-[#303438]"
                      >
                        {t.backToAlbums}
                      </button>
                      <div className="mb-6 flex items-center gap-5">
                        {album?.cover_image_url && (
                          <img
                            src={resolveAssetUrl(album.cover_image_url)}
                            alt={`${album.title} cover`}
                            className="h-24 w-24 rounded-xl object-cover"
                          />
                        )}
                        <div>
                            <p className="text-sm font-semibold text-violet-300">{t.albumTracks}</p>
                          <h2 className="mt-1 text-2xl font-bold text-white">{album?.title}</h2>
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
                    <div className="store-section-heading mb-7 px-6 py-6 sm:px-8 sm:py-7">
                      <p className="mb-2 inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-violet-300">
                        <span className="h-1.5 w-1.5 rounded-full bg-violet-400 shadow-[0_0_12px_rgba(167,139,250,0.9)]" />
                        DJ Bilal Music
                      </p>
                      <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">{t.albums}</h2>
                      <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300/80 sm:text-base">{t.albumsDesc}</p>
                    </div>
                    {albumsError ? (
                      <div className="rounded-lg border border-red-500 bg-red-600/20 p-4 text-red-200">
                        {albumsError}
                      </div>
                    ) : albums.length ? (
                      <div className="grid grid-cols-1 gap-5 pb-32 sm:grid-cols-2 lg:grid-cols-3 xl:gap-6">
                        {albums.map((album) => {
                          const albumTrackCount = tracks.filter((track) => track.album_id === album.id).length;
                          return (
                            <button
                              key={album.id}
                              type="button"
                              onClick={() => setSelectedAlbumId(album.id)}
                              className="album-card group overflow-hidden rounded-2xl border border-white/[0.08] text-left transition-all duration-300 hover:-translate-y-1 hover:border-violet-400/40 hover:shadow-2xl hover:shadow-violet-950/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400"
                            >
                              <div className="relative aspect-square overflow-hidden">
                                {album.cover_image_url ? (
                                  <img
                                    src={resolveAssetUrl(album.cover_image_url)}
                                    alt={`${album.title} cover`}
                                    className="h-full w-full object-cover transition-transform duration-700 group-hover:scale-105"
                                    loading="lazy"
                                  />
                                ) : (
                                  <div className="album-cover-placeholder flex h-full w-full items-center justify-center">
                                    <div className="flex h-24 w-24 items-center justify-center rounded-full border border-white/20 bg-white/[0.08] shadow-2xl backdrop-blur-sm transition-transform duration-500 group-hover:scale-110">
                                      <Music size={42} className="text-white/90 drop-shadow-lg" />
                                    </div>
                                  </div>
                                )}
                                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-[#17141f]/75 via-transparent to-white/[0.04]" />
                                <div className="absolute bottom-3 left-3 inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-black/35 px-3 py-1 text-xs font-semibold text-white/90 shadow-lg backdrop-blur-md">
                                  <Music size={12} className="text-violet-200" />
                                  {albumTrackCount} {t.albumTracks}
                                </div>
                              </div>
                              <div className="p-4 sm:p-5">
                                <h3 className="truncate text-lg font-bold text-white transition-colors group-hover:text-violet-200">{album.title}</h3>
                                <p className="mt-1.5 text-sm text-slate-400">
                                  {album.release_date
                                    ? new Date(album.release_date).toLocaleDateString(lang === 'ar' ? 'ar' : 'en')
                                    : t.albums}
                                </p>
                              </div>
                            </button>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-300">
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
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-violet-500/15 px-3 py-1 text-xs font-semibold text-violet-300">
                    <Gift size={12} />
                    {t.free}
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">{t.freeDownloads}</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
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

          </>
        )}
      </main>

      <footer className="border-t border-white/[0.06] bg-gradient-to-r from-[#191922] via-[#20202b] to-[#191922]">
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
        <div className="fixed bottom-0 left-0 right-0 border-t border-violet-300/15 bg-gradient-to-r from-[#24222f]/95 via-[#242430]/95 to-[#1c202b]/95 shadow-[0_-16px_48px_rgba(8,7,18,0.38)] backdrop-blur-xl">
          <AudioPlayer track={currentTrack} isPlaying={isPlaying} onPlayPause={setIsPlaying} />
        </div>
      )}

      {cartTracks.length > 0 && (
        <button
          type="button"
          onClick={handleOpenCart}
          className="fixed bottom-24 right-4 z-50 inline-flex items-center gap-2 rounded-full border border-white/15 bg-violet-700 px-5 py-3 font-semibold text-white shadow-xl shadow-black/30 transition hover:bg-violet-600 sm:right-6"
          aria-label={`${t.cart} (${cartTracks.length})`}
        >
          <ShoppingCart size={18} />
          <span>{t.cart}</span>
          <span className="rounded-full bg-white/20 px-2 py-0.5 text-xs">{cartTracks.length}</span>
        </button>
      )}


      {/* Modals */}
      <AuthModal
        isOpen={authModal.isOpen}
        mode={authModal.mode}
        onClose={() => setAuthModal({ ...authModal, isOpen: false })}
        onSuccess={() => setAuthModal({ isOpen: false, mode: 'login' })}
      />
      <ShopierCheckoutModal
        isOpen={checkoutOpen}
        tracks={cartTracks}
        user={user}
        busy={checkoutBusy}
        onClose={() => setCheckoutOpen(false)}
        onRemoveTrack={(trackId) => setCartTracks((current) => current.filter((track) => track.id !== trackId))}
        onCheckout={handleShopierCheckout}
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
          <AppContent />
        </TrackProvider>
      </AuthProvider>
    </LanguageProvider>
  );
}
