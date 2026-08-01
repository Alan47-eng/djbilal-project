import React, { useState } from 'react';
import { LogOut, LogIn, UserPlus, Music, User } from 'lucide-react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { TrackProvider, useTracks } from './context/TrackContext';
import { PurchaseProvider, usePurchases } from './context/PurchaseContext';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import PurchaseModal from './components/PurchaseModal';
import './index.css';

function AppContent() {
  const { user, logout, loading: authLoading } = useAuth();
  const { tracks, loading: tracksLoading, error: tracksError } = useTracks();
  const { purchases } = usePurchases();
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });
  const [purchaseModal, setPurchaseModal] = useState({ isOpen: false, track: null });
  const [pendingPurchaseTrack, setPendingPurchaseTrack] = useState(null);

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

  const handleDownloadTrack = (track) => {
    // Download logic handled in TrackCard component
  };

  const handleLogout = () => {
    logout();
    setIsPlaying(false);
    setCurrentTrack(null);
    setPendingPurchaseTrack(null);
    setPurchaseModal({ isOpen: false, track: null });
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
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-2 rounded-lg">
              <Music size={28} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              DJ Bilal Music Store
            </h1>
          </div>

          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="flex items-center gap-2 text-slate-300">
                  <User size={18} className="text-purple-400" />
                  <span>{user.email}</span>
                  {isAdmin && (
                    <span className="rounded-full bg-purple-600/20 px-2 py-0.5 text-xs font-semibold text-purple-300">
                      Admin
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 pb-32">
            {tracks.map(track => (
              <TrackCard
                key={track.id}
                track={track}
                isPurchased={purchases.includes(track.id)}
                onPlayPreview={handlePlayPreview}
                onBuy={handleBuyTrack}
                onDownload={handleDownloadTrack}
                isAdmin={isAdmin}
              />
            ))}
          </div>
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
