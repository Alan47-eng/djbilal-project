import React, { useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User, Menu, LayoutGrid, ShieldCheck } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { PurchaseProvider, usePurchases } from './context/PurchaseContext';
import { useCheckout } from './hooks/useTrackOperations';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import PurchaseModal from './components/PurchaseModal';
import AdminDrawer from './components/AdminDrawer';
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

  const isAdmin = user?.is_admin === true;
  const loading = authLoading || tracksLoading;

  const handlePlayPreview = (track) => {
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const handleBuyTrack = (track) => {
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

  const handleDownloadTrack = (track) => {
    // Download logic handled in TrackCard component
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setPendingPurchaseTrack(null);
    setPurchaseModal({ isOpen: false, track: null });
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
              <p className="text-xs text-slate-400">Yeni parçalar, preview ve Lemon Squeezy ödeme</p>
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
      <main className="max-w-7xl mx-auto px-6 py-12">
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
            <section className="mb-8 rounded-3xl border border-slate-800 bg-gradient-to-r from-slate-900 to-slate-800 p-6">
              <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="mb-2 inline-flex items-center gap-2 rounded-full bg-purple-600/20 px-3 py-1 text-xs font-semibold text-purple-300">
                    <LayoutGrid size={12} />
                    Keşfet
                  </p>
                  <h2 className="text-3xl font-bold text-white">Şarkılar burada, admin araçları menüde.</h2>
                  <p className="mt-2 max-w-2xl text-slate-400">
                    Admin hesabıyla sol üst menüyü açıp yeni şarkı ekleyebilir, kullanıcıları admin yapabilir ve Lemon Squeezy checkout akışını yönetebilirsin.
                  </p>
                </div>
                {isAdmin && (
                  <button
                    type="button"
                    onClick={() => setMenuOpen(true)}
                    className="inline-flex items-center gap-2 rounded-xl bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700"
                  >
                    <ShieldCheck size={16} />
                    Admin Panelini Aç
                  </button>
                )}
              </div>
            </section>

            {tracks.length === 0 ? (
              <div className="rounded-2xl border border-slate-800 bg-slate-900 p-8 text-center text-slate-300">
                Henüz şarkı yok. Admin menüsünden ilk parçayı ekleyebilirsin.
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
      <AdminDrawer isOpen={menuOpen} onClose={() => setMenuOpen(false)} />
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
