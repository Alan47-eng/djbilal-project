import React, { useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck, Gift, Library, ShoppingCart } from 'lucide-react';
import api from './api';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { PurchaseProvider, usePurchases } from './context/PurchaseContext';
import { useCheckout } from './hooks/useTrackOperations';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import AdminDrawer from './components/AdminDrawer';
import FreeTracksList from './components/FreeTracksList';
import UserPurchases from './components/UserPurchases';
import './index.css';

function AppContent() {
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
  const [downloadError, setDownloadError] = useState(null);

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
      setDownloadError('Preview file is missing for this track.');
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
        setDownloadError('File not found. Please upload the track again.');
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
      setDownloadError(err.response?.data?.detail || 'Download failed.');
    }
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setPendingCartTrackId(null);
    setCartTrackIds([]);
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
    <div className="min-h-screen bg-slate-900 text-slate-100">
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
            <div>
              <h1 className="text-lg sm:text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                DJ Bilal Music Store
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
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
                  <span className="hidden sm:inline">Logout</span>
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'login' })}
                  className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-3 sm:px-4 py-2 rounded-lg transition-colors duration-200 font-semibold text-sm sm:text-base"
                >
                  <LogIn size={18} />
                  <span className="hidden sm:inline">Sign In</span>
                </button>
                <button
                  onClick={() => setAuthModal({ isOpen: true, mode: 'register' })}
                  className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 text-white px-3 sm:px-4 py-2 rounded-lg transition-colors duration-200 font-semibold text-sm sm:text-base"
                >
                  <UserPlus size={18} />
                  <span className="hidden sm:inline">Sign Up</span>
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

        {/* Tab Navigation */}
        <nav className="mb-6 sm:mb-8 flex max-w-full items-center gap-1 overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900 p-1">
          {[
            { id: 'edits', label: 'Edits', icon: <LayoutGrid size={15} /> },
            { id: 'remixes', label: 'Remixes', icon: <Music size={15} /> },
            { id: 'free', label: 'Free', icon: <Gift size={15} /> },
            ...(user ? [{ id: 'library', label: 'My Library', icon: <Library size={15} /> }] : []),
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

        {user && (
          <section className="mb-8 rounded-2xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="inline-flex items-center gap-2 text-sm font-semibold text-purple-300">
                  <ShoppingCart size={16} />
                  Cart ({cartTracks.length})
                </p>
                <p className="mt-1 text-sm text-slate-400">
                  Total: ${cartTotal.toFixed(2)}
                </p>
              </div>
              <button
                type="button"
                onClick={handleCheckout}
                disabled={checkoutLoading || cartTracks.length === 0}
                className="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-4 py-2.5 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
              >
                <ShoppingCart size={16} />
                {checkoutLoading ? 'Redirecting...' : 'Checkout Cart'}
              </button>
            </div>

            {checkoutError && (
              <div className="mt-3 rounded-lg border border-red-600 bg-red-900/20 px-3 py-2 text-sm text-red-300">
                {checkoutError}
              </div>
            )}

            {cartTracks.length > 0 && (
              <div className="mt-4 space-y-2">
                {cartTracks.map((track) => (
                  <div key={track.id} className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm">
                    <span className="text-slate-200 break-words">
                      {track.title} • {track.artist}
                    </span>
                    <div className="flex items-center justify-between sm:justify-end gap-3">
                      <span className="font-semibold text-purple-300">${track.price.toFixed(2)}</span>
                      <button
                        type="button"
                        onClick={() => removeFromCart(track.id)}
                        className="text-xs font-semibold text-slate-300 hover:text-white"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

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
            {isAdmin && activeTab !== 'library' && (
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

            {/* Edits tab */}
            {activeTab === 'edits' && (
              <>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white">Edits</h2>
                  <p className="mt-1 text-sm text-slate-400">Original edits and premium versions.</p>
                </div>
                {renderTrackGrid(editTracks, 'No edits added yet.')}
              </>
            )}

            {/* Remixes tab */}
            {activeTab === 'remixes' && (
              <>
                <div className="mb-6">
                  <h2 className="text-2xl font-bold text-white">Remixes</h2>
                  <p className="mt-1 text-sm text-slate-400">Remix catalog with instant preview and checkout.</p>
                </div>
                {renderTrackGrid(remixTracks, 'No remixes added yet.')}
              </>
            )}

            {/* Free tab */}
            {activeTab === 'free' && (
              <section>
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-emerald-600/20 px-3 py-1 text-xs font-semibold text-emerald-300">
                    <Gift size={12} />
                    Free
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">Free Downloads</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
                    Browse free remix, simple pack, and VST files.
                  </p>
                </div>
                <FreeTracksList tracks={tracks} onPlay={handlePlayPreview} />
              </section>
            )}

            {/* My Library tab */}
            {activeTab === 'library' && (
              <section className="pb-32">
                <div className="mb-6">
                  <p className="mb-1 inline-flex items-center gap-2 rounded-full bg-purple-600/20 px-3 py-1 text-xs font-semibold text-purple-300">
                    <Library size={12} />
                    My Library
                  </p>
                  <h2 className="mt-2 text-2xl font-bold text-white">My Purchases</h2>
                  <p className="text-slate-400 mt-1 text-sm max-w-xl">
                    Re-download all licensed tracks you have purchased anytime from here.
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
              Privacy Policy
            </a>
            <a
              href="/terms-of-use.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              Terms of Use
            </a>
            <a
              href="/refund-policy.html"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-white"
            >
              Refund Policy
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
