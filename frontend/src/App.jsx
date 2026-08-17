import React, { useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck, Gift, Library, Info } from 'lucide-react';
import api from './api';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { PurchaseProvider, usePurchases } from './context/PurchaseContext';
import { useCheckout } from './hooks/useTrackOperations';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import PurchaseModal from './components/PurchaseModal';
import AdminDrawer from './components/AdminDrawer';
import AboutSection from './components/AboutSection';
import FreeTracksList from './components/FreeTracksList';
import UserPurchases from './components/UserPurchases';
import './index.css';

function AppContent() {
  const { user, logout, loading: authLoading } = useAuth();
  const { tracks, loading: tracksLoading, error: tracksError } = useTracks();
  const { purchases } = usePurchases();
  const { checkout, loading: checkoutLoading, error: checkoutError } = useCheckout();
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [purchaseModal, setPurchaseModal] = useState({ isOpen: false, track: null });
  const [pendingPurchaseTrack, setPendingPurchaseTrack] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('store'); // 'store' | 'free' | 'about' | 'library'
  const [downloadError, setDownloadError] = useState(null);

  const isAdmin = user?.is_admin === true;
  const loading = authLoading || tracksLoading;

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

  const buildDownloadCandidates = (rawUrl) => {
    if (!rawUrl) return [];
    const candidates = [];
    const add = (value) => {
      if (value && !candidates.includes(value)) {
        candidates.push(value);
      }
    };

    try {
      const parsed = new URL(rawUrl, window.location.origin);
      if (window.location.protocol === 'https:' && parsed.protocol === 'http:') {
        parsed.protocol = 'https:';
      }
      add(parsed.toString());
      if (parsed.pathname.startsWith('/media/')) {
        add(parsed.pathname);
      }
    } catch {
      add(rawUrl);
      if (rawUrl.startsWith('/media/')) {
        add(rawUrl);
      }
    }

    return candidates;
  };

  const handlePlayPreview = (track) => {
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const handleBuyTrack = (track) => {
    if (track.is_free) {
      handleDownloadTrack(track);
      return;
    }
    if (!user) {
      setPendingPurchaseTrack(track);
      setAuthModal({ isOpen: true, mode: 'login' });
      return;
    }
    setPurchaseModal({ isOpen: true, track });
  };

  const handleCheckout = async () => {
    if (!purchaseModal.track) return;
    const checkoutUrl = await checkout(purchaseModal.track.id);
    if (checkoutUrl) {
      window.location.assign(checkoutUrl);
    }
    return checkoutUrl;
  };

  const handleDownloadTrack = async (track) => {
    try {
      setDownloadError(null);
      const endpoint = track.is_free
        ? `/tracks/${track.id}/free-download`
        : `/tracks/${track.id}/download`;

      if (!track.is_free && !user) {
        setAuthModal({ isOpen: true, mode: 'login' });
        return;
      }

      const response = await api.get(endpoint);
      const downloadUrl = response.data?.download_url;
      if (!downloadUrl) {
        setDownloadError('İndirme bağlantısı bulunamadı.');
        return;
      }

      const candidates = buildDownloadCandidates(downloadUrl);
      let downloaded = false;

      for (const candidate of candidates) {
        try {
          const fileResponse = await api.get(candidate, { responseType: 'blob' });
          const blobUrl = window.URL.createObjectURL(fileResponse.data);
          const link = document.createElement('a');
          link.href = blobUrl;
          link.download = buildDownloadName(track, candidate);
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
          window.URL.revokeObjectURL(blobUrl);
          downloaded = true;
          break;
        } catch {
          // Try next candidate URL.
        }
      }

      if (!downloaded) {
        setDownloadError('Dosya bulunamadı. Lütfen parçayı yeniden yükleyin.');
      }
    } catch (err) {
      setDownloadError(err.response?.data?.detail || 'İndirme başarısız oldu.');
    }
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setPendingPurchaseTrack(null);
    setPurchaseModal({ isOpen: false, track: null });
    setDownloadError(null);
    setMenuOpen(false);
  };

  const handleAuthSuccess = () => {
    if (pendingPurchaseTrack) {
      setPurchaseModal({ isOpen: true, track: pendingPurchaseTrack });
      setPendingPurchaseTrack(null);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between gap-4">
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
            <div>
              <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                DJ Bilal Music Store
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="flex items-center gap-2 text-slate-300">
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
                  className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition-colors duration-200 font-semibold"
                >
                  <LogOut size={18} />
                  Logout
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'login' })}
                  className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors duration-200 font-semibold"
                >
                  <LogIn size={18} />
                  Sign In
                </button>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'register' })}
                  className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-lg transition-colors duration-200 font-semibold"
                >
                  <UserPlus size={18} />
                  Sign Up
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-8">
        {downloadError && (
          <div className="mb-6 rounded-lg border border-red-500 bg-red-600/20 px-4 py-3 text-sm text-red-200">
            {downloadError}
          </div>
        )}

        {/* Tab Navigation */}
        <nav className="flex items-center gap-1 mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-1 w-fit">
          {[
            { id: 'store', label: 'Mağaza', icon: <LayoutGrid size={15} /> },
            { id: 'free', label: 'Ücretsiz', icon: <Gift size={15} /> },
            { id: 'about', label: 'Hakkımda', icon: <Info size={15} /> },
            ...(user ? [{ id: 'library', label: 'Kütüphanem', icon: <Library size={15} /> }] : []),
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
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition-all duration-200 ${
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
            {/* Store tab */}
            {activeTab === 'store' && (
              <>
                {isAdmin && (
                  <section className="mb-8 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setMenuOpen(true)}
                      className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700"
                    >
                      <ShieldCheck size={16} />
                      Open Admin Panel
                    </button>
                  </section>
                )}

                {tracks.length === 0 ? (
                  <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-300">
                    Henüz parça eklenmedi. Çok yakında yeni içerikler burada olacak.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-32">
                    {tracks.map(track => (
                      <TrackCard
                        key={track.id}
                        track={track}
                        isPurchased={purchases.includes(track.id)}
                        onPlay={handlePlayPreview}
                        onBuy={handleBuyTrack}
                        onDownload={handleDownloadTrack}
                      />
                    ))}
                  </div>
                )}
              </>
            )}

            {/* Free Downloads tab */}
            {activeTab === 'free' && (
              <section>
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-emerald-600/20 px-3 py-1 text-xs font-semibold text-emerald-300">
                    <Gift size={12} />
                    Ücretsiz İndir
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Kaliteyi Ücretsiz Keşfet</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
                    Seçilmiş şarkıları herhangi bir ödeme yapmadan indir, dinle ve projende kullan.
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
                    Kütüphanem
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Satın Aldıklarım</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
                    Satın aldığın tüm lisanslı şarkıları dilediğin zaman buradan yeniden indirebilirsin.
                  </p>
                </div>
                <UserPurchases />
              </section>
            )}
          </>
        )}
      </main>

      {/* Player */}
      {currentTrack && (
        <div className="fixed bottom-0 left-0 right-0 bg-slate-800 border-t border-slate-700">
          <AudioPlayer track={currentTrack} isPlaying={isPlaying} onPlayPause={setIsPlaying} />
        </div>
      )}

      {/* Modals */}
      <AuthModal
        isOpen={authModal.isOpen}
        mode={authModal.mode}
        onClose={() => setAuthModal({ ...authModal, isOpen: false })}
        onSuccess={handleAuthSuccess}
      />
      <PurchaseModal
        isOpen={purchaseModal.isOpen}
        track={purchaseModal.track}
        onClose={() => setPurchaseModal({ isOpen: false, track: null })}
        onConfirm={handleCheckout}
        loading={checkoutLoading}
        error={checkoutError}
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
  return (
    <AuthProvider>
      <TrackProvider>
        <PurchaseProvider>
          <AppContent />
        </PurchaseProvider>
      </TrackProvider>
    </AuthProvider>
  );
}
