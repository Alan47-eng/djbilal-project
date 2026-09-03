import React, { useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck, Gift, Library, ShoppingCart, Info } from 'lucide-react';
import api from './api';
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

function AppContent() {
  const { lang, setLang, isRTL } = useLanguage();
  const { user, logout, loading: authLoading } = useAuth();
  const { tracks, loading: tracksLoading, error: tracksError } = useTracks();
  const { purchases } = usePurchases();
  const { checkoutCart, loading: checkoutLoading, error: checkoutError } = useCheckout();
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [pendingCartTrackId, setPendingCartTrackId] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('edits'); // 'edits' | 'remixes' | 'free' | 'library'
  const [cartTrackIds, setCartTrackIds] = useState([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [downloadError, setDownloadError] = useState(null);
  const t = {
    edits: lang === 'ar' ? 'تعديلات' : 'Edits',
    remixes: lang === 'ar' ? 'ريمكسات' : 'Remixes',
    free: lang === 'ar' ? 'مجاني' : 'Free',
    myLibrary: lang === 'ar' ? 'مكتبتي' : 'My Library',
    signIn: lang === 'ar' ? 'تسجيل الدخول' : 'Sign In',
    signUp: lang === 'ar' ? 'إنشاء حساب' : 'Sign Up',
    logout: lang === 'ar' ? 'تسجيل الخروج' : 'Logout',
    cart: lang === 'ar' ? 'السلة' : 'Cart',
    total: lang === 'ar' ? 'المجموع' : 'Total',
    checkoutCart: lang === 'ar' ? 'الدفع من السلة' : 'Checkout Cart',
    redirecting: lang === 'ar' ? 'جاري التحويل...' : 'Redirecting...',
    remove: lang === 'ar' ? 'حذف' : 'Remove',
    openAdmin: lang === 'ar' ? 'فتح لوحة الإدارة' : 'Open Admin Panel',
    editsDesc: lang === 'ar' ? 'تعديلات أصلية ونسخ مميزة.' : 'Original edits and premium versions.',
    remixesDesc: lang === 'ar' ? 'قائمة الريمكسات مع المعاينة الفورية والدفع.' : 'Remix catalog with instant preview and checkout.',
    noEdits: lang === 'ar' ? 'لا توجد تعديلات بعد.' : 'No edits added yet.',
    noRemixes: lang === 'ar' ? 'لا توجد ريمكسات بعد.' : 'No remixes added yet.',
    aboutMe: lang === 'ar' ? 'من أنا' : 'About Me',
    home: lang === 'ar' ? 'الرئيسية' : 'Home',
    freeDownloads: lang === 'ar' ? 'تنزيلات مجانية' : 'Free Downloads',
    freeDesc: lang === 'ar' ? 'تصفح ملفات الريمكس والحزم البسيطة وملفات VST المجانية.' : 'Browse free remix, simple pack, and VST files.',
    myPurchases: lang === 'ar' ? 'مشترياتي' : 'My Purchases',
    myPurchasesDesc: lang === 'ar' ? 'أعد تنزيل كل التراكات المشتراة في أي وقت.' : 'Re-download all licensed tracks you have purchased anytime from here.',
    previewMissing: lang === 'ar' ? 'ملف المعاينة غير متوفر لهذا التراك.' : 'Preview file is missing for this track.',
    fileMissing: lang === 'ar' ? 'الملف غير موجود. يرجى إعادة رفع التراك.' : 'File not found. Please upload the track again.',
    downloadFailed: lang === 'ar' ? 'فشل التنزيل.' : 'Download failed.',
    privacy: lang === 'ar' ? 'سياسة الخصوصية' : 'Privacy Policy',
    terms: lang === 'ar' ? 'شروط الاستخدام' : 'Terms of Service',
    refund: lang === 'ar' ? 'سياسة الاسترجاع' : 'Refund Policy',
    contact: lang === 'ar' ? 'اتصل بنا' : 'Contact Us',
    cartEmpty: lang === 'ar' ? 'السلة فارغة حالياً.' : 'Your cart is empty right now.',
    close: lang === 'ar' ? 'إغلاق' : 'Close',
  };

  const isAdmin = user?.is_admin === true;
  const loading = authLoading || tracksLoading;
  const normalizedCategory = (track) => (track.category || '').toLowerCase();
  const paidTracks = tracks.filter((track) => !track.is_free);
  const remixTracks = paidTracks.filter((track) => {
    const category = normalizedCategory(track);
    if (category) return category === 'remix';
    return `${track.title} ${track.artist}`.toLowerCase().includes('remix');
  });
  const editTracks = paidTracks.filter((track) => {
    const category = normalizedCategory(track);
    if (category) return category === 'edit';
    return !`${track.title} ${track.artist}`.toLowerCase().includes('remix');
  });
  const cartTracks = paidTracks.filter((track) => cartTrackIds.includes(track.id) && !purchases.includes(track.id));
  const cartTotal = cartTracks.reduce((sum, track) => sum + (track.price || 0), 0);

  const addToCart = (track) => {
    if (track.is_free) {
      handleDownloadTrack(track);
      return;
    }
    if (!user) {
      setPendingCartTrackId(track.id);
      setAuthModal({ isOpen: true, mode: 'login' });
      return;
    }
    setCartTrackIds((prev) => (prev.includes(track.id) ? prev : [...prev, track.id]));
  };

  const removeFromCart = (trackId) => {
    setCartTrackIds((prev) => prev.filter((id) => id !== trackId));
  };

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
        {tracksToRender.map((track) => (
          <TrackCard
            key={track.id}
            track={track}
            isPurchased={purchases.includes(track.id)}
            inCart={cartTrackIds.includes(track.id)}
            onPlay={handlePlayPreview}
            onBuy={handleBuyTrack}
            onAddToCart={addToCart}
            onDownload={handleDownloadTrack}
          />
        ))}
      </div>
    );
  };

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

  const handlePlayPreview = (track) => {
    if (!track?.preview_url) {
      setDownloadError(t.previewMissing);
      return;
    }
    setDownloadError(null);
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const handleBuyTrack = (track) => {
    addToCart(track);
  };

  const handleCheckout = async () => {
    if (cartTracks.length === 0) return;
    const checkoutUrl = await checkoutCart(cartTracks.map((track) => track.id));
    if (checkoutUrl) {
      window.location.assign(checkoutUrl);
    }
    return checkoutUrl;
  };

  const handleDownloadTrack = async (track) => {
    try {
      setDownloadError(null);
      const endpoint = track.is_free
        ? `/tracks/${track.id}/free-download-file`
        : `/tracks/${track.id}/download-file`;

      if (!track.is_free && !user) {
        setAuthModal({ isOpen: true, mode: 'login' });
        return;
      }

      const sourceRef = track.full_file_path || track.preview_url || '';
      const fileResponse = await api.get(endpoint, { responseType: 'blob' });
      const contentType = (fileResponse.headers && fileResponse.headers['content-type']) || '';
      if (contentType.includes('text/html')) {
        setDownloadError(t.fileMissing);
        return;
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
      setDownloadError(err.response?.data?.detail || t.downloadFailed);
    }
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setPendingCartTrackId(null);
    setCartTrackIds([]);
    setCartOpen(false);
    setDownloadError(null);
    setMenuOpen(false);
  };

  const handleAuthSuccess = () => {
    if (pendingCartTrackId) {
      const track = tracks.find((item) => item.id === pendingCartTrackId);
      if (track && !track.is_free) {
        setCartTrackIds((prev) => (prev.includes(track.id) ? prev : [...prev, track.id]));
      }
      setPendingCartTrackId(null);
    }
  };

  return (
    <div className={`min-h-screen bg-slate-900 text-slate-100 ${isRTL ? 'text-right' : ''}`}>
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuOpen(true)}
              className="rounded-lg border border-slate-700 p-2 text-slate-300 hover:bg-slate-700 hover:text-white"
              aria-label="Open menu"
            >
              <Menu size={20} />
            </button>
            <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-2 rounded-lg">
              <Music size={28} className="text-white" />
            </div>
            <button
              type="button"
              onClick={() => {
                setActiveTab('edits');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              className="text-left"
            >
              <h1 className="text-lg sm:text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                DJ Bilal Music Store
              </h1>
            </button>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="flex items-center rounded-lg border border-slate-700 bg-slate-900/80 p-1 text-xs">
              <button
                type="button"
                onClick={() => setLang('en')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'en' ? 'bg-purple-600 text-white' : 'text-slate-300'}`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setLang('ar')}
                className={`rounded px-2 py-1 font-semibold ${lang === 'ar' ? 'bg-purple-600 text-white' : 'text-slate-300'}`}
              >
                AR
              </button>
            </div>
            {user ? (
              <>
                <div className="hidden md:flex items-center gap-2 text-slate-300">
                  <User size={18} className="text-purple-400" />
                  <span>{user.email}</span>
                  {isAdmin && (
                    <span className="rounded-full bg-purple-600/20 px-2 py-0.5 text-xs font-semibold text-purple-300">
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
                  className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-3 sm:px-4 py-2 rounded-lg transition-colors duration-200 font-semibold text-sm sm:text-base"
                >
                  <LogIn size={18} />
                  <span className="hidden sm:inline">{t.signIn}</span>
                </button>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'register' })}
                  className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-3 sm:px-4 py-2 rounded-lg transition-colors duration-200 font-semibold text-sm sm:text-base"
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

        <div className="mb-4 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setActiveTab('edits');
              window.scrollTo({ top: 0, behavior: 'smooth' });
            }}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
              activeTab === 'edits' || activeTab === 'remixes' || activeTab === 'free'
                ? 'border-slate-700 bg-slate-900 text-slate-200'
                : 'border-slate-700 bg-slate-900 text-slate-400'
            }`}
          >
            <LayoutGrid size={15} />
            {t.home}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('about')}
            className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold ${
              activeTab === 'about'
                ? 'border-purple-500 bg-purple-600/20 text-purple-200'
                : 'border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800'
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
                  ? 'border-purple-500 bg-purple-600/20 text-purple-200'
                  : 'border-slate-700 bg-slate-900 text-slate-300 hover:bg-slate-800'
              }`}
            >
              <Library size={15} />
              {t.myLibrary}
            </button>
          )}
        </div>

        {/* Tab Navigation */}
        <nav className="mb-6 sm:mb-8 flex max-w-full items-center gap-1 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900 p-1">
          {[
            { id: 'edits', label: t.edits, icon: <LayoutGrid size={15} /> },
            { id: 'remixes', label: t.remixes, icon: <Music size={15} /> },
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
                  ? 'bg-purple-600 text-white shadow'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800'
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
              <Music size={48} className="text-purple-400" />
            </div>
          </div>
        ) : tracksError ? (
          <div className="bg-red-600/20 border border-red-500 text-red-200 p-4 rounded-lg">
            {tracksError}
          </div>
        ) : (
          <>
            {isAdmin && activeTab !== 'library' && activeTab !== 'about' && (
              <section className="mb-8 flex justify-end">
                <button
                  type="button"
                  onClick={() => setMenuOpen(true)}
                  className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700"
                >
                  <ShieldCheck size={16} />
                  {t.openAdmin}
                </button>
              </section>
            )}

            {/* Edits tab */}
            {activeTab === 'edits' && (
              <>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white">{t.edits}</h2>
                  <p className="mt-1 text-sm text-slate-400">{t.editsDesc}</p>
                </div>
                {renderTrackGrid(editTracks, t.noEdits)}
              </>
            )}

            {/* Remixes tab */}
            {activeTab === 'remixes' && (
              <>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white">{t.remixes}</h2>
                  <p className="mt-1 text-sm text-slate-400">{t.remixesDesc}</p>
                </div>
                {renderTrackGrid(remixTracks, t.noRemixes)}
              </>
            )}

            {/* Free tab */}
            {activeTab === 'free' && (
              <section>
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-emerald-600/20 px-3 py-1 text-xs font-semibold text-emerald-300">
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

            {/* My Library tab */}
            {activeTab === 'library' && (
              <section className="pb-32">
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-purple-600/20 px-3 py-1 text-xs font-semibold text-purple-300">
                    <Library size={12} />
                    {t.myLibrary}
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">{t.myPurchases}</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
                    {t.myPurchasesDesc}
                  </p>
                </div>
                <UserPurchases />
              </section>
            )}
          </>
        )}
      </main>

      <footer className="border-t border-slate-800 bg-slate-900">
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
        <div className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700">
          <AudioPlayer track={currentTrack} isPlaying={isPlaying} onPlayPause={setIsPlaying} />
        </div>
      )}

      {user && (
        <>
          <button
            type="button"
            onClick={() => setCartOpen(true)}
            className="fixed bottom-24 right-4 z-40 inline-flex items-center gap-2 rounded-full bg-purple-600 px-4 py-3 text-sm font-semibold text-white shadow-lg hover:bg-purple-700"
          >
            <ShoppingCart size={16} />
            {t.cart} ({cartTracks.length})
          </button>

          {cartOpen && (
            <div className="fixed inset-0 z-50 bg-black/60" onClick={() => setCartOpen(false)}>
              <aside
                className="absolute right-0 top-0 h-full w-full max-w-sm border-l border-slate-700 bg-slate-900 p-4"
                onClick={(event) => event.stopPropagation()}
              >
                <div className="mb-4 flex items-center justify-between">
                  <h3 className="text-lg font-bold text-white">{t.cart}</h3>
                  <button
                    type="button"
                    onClick={() => setCartOpen(false)}
                    className="rounded-lg bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700"
                  >
                    {t.close}
                  </button>
                </div>

                <p className="mb-3 text-sm text-slate-400">{t.total}: ${cartTotal.toFixed(2)}</p>

                {checkoutError && (
                  <div className="mb-3 rounded-lg border border-red-600 bg-red-900/20 px-3 py-2 text-sm text-red-300">
                    {checkoutError}
                  </div>
                )}

                {cartTracks.length === 0 ? (
                  <div className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-4 text-sm text-slate-300">
                    {t.cartEmpty}
                  </div>
                ) : (
                  <div className="space-y-2">
                    {cartTracks.map((track) => (
                      <div key={track.id} className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm">
                        <p className="text-slate-100">{track.title}</p>
                        <p className="text-xs text-slate-400">{track.artist}</p>
                        <div className="mt-2 flex items-center justify-between">
                          <span className="font-semibold text-purple-300">${track.price.toFixed(2)}</span>
                          <button
                            type="button"
                            onClick={() => removeFromCart(track.id)}
                            className="text-xs font-semibold text-slate-300 hover:text-white"
                          >
                            {t.remove}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                <button
                  type="button"
                  onClick={handleCheckout}
                  disabled={checkoutLoading || cartTracks.length === 0}
                  className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
                >
                  <ShoppingCart size={16} />
                  {checkoutLoading ? t.redirecting : t.checkoutCart}
                </button>
              </aside>
            </div>
          )}
        </>
      )}

      {/* Modals */}
      <AuthModal
        isOpen={authModal.isOpen}
        mode={authModal.mode}
        onClose={() => setAuthModal({ ...authModal, isOpen: false })}
        onSuccess={handleAuthSuccess}
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
