import React, { useState, useEffect } from 'react';
import { LogOut, LogIn, UserPlus, Music, User } from 'lucide-react';
import api from './api';
import TrackCard from './components/TrackCard';
import AudioPlayer from './components/AudioPlayer';
import AuthModal from './components/AuthModal';
import PurchaseModal from './components/PurchaseModal';
import './index.css';

function App() {
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentTrack, setCurrentTrack] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [user, setUser] = useState(null);
  const [uploadForm, setUploadForm] = useState({
    title: '',
    artist: '',
    price: '',
    checkoutUrl: '',
    coverFile: null,
    trackFile: null,
    previewFile: null,
  });
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [uploadSuccess, setUploadSuccess] = useState(null);
  const [uploadFormKey, setUploadFormKey] = useState(0);
  const [authModal, setAuthModal] = useState({
    isOpen: false,
    mode: 'login',
  });
  const [purchaseModal, setPurchaseModal] = useState({
    isOpen: false,
    track: null,
  });
  const [purchaseIds, setPurchaseIds] = useState([]);
  const [isPurchasing, setIsPurchasing] = useState(false);
  const [purchaseError, setPurchaseError] = useState(null);
  const [pendingPurchaseTrack, setPendingPurchaseTrack] = useState(null);
  const isAdmin = user?.is_admin === true;

  const fetchTracks = async () => {
    try {
      setLoading(true);
      const response = await api.get('/tracks');
      setTracks(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching tracks:', err);
      setError('Failed to load tracks. Please try again later.');
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentUser = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setUser(null);
      return null;
    }

    const response = await api.get('/me');
    setUser(response.data);
    return response.data;
  };

  const fetchPurchases = async () => {
    const token = localStorage.getItem('accessToken');
    if (!token) {
      setPurchaseIds([]);
      return;
    }

    try {
      const response = await api.get('/purchases');
      setPurchaseIds(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Error fetching purchases:', err);
      setPurchaseIds([]);
    }
  };

  // Fetch tracks from backend
  useEffect(() => {
    fetchTracks();
  }, []);

  // Check if user is logged in
  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      fetchCurrentUser()
        .then((currentUser) => {
          if (currentUser) {
            fetchPurchases();
          }
        })
        .catch((err) => {
          console.error('Error fetching current user:', err);
          setUser(null);
          setPurchaseIds([]);
        });
    }
  }, []);

  const handlePlayPreview = (track) => {
    setCurrentTrack(track);
    setIsPlaying(true);
  };

  const handleBuyTrack = (track) => {
    if (!user) {
      setPendingPurchaseTrack(track);
      openAuthModal('login');
      return;
    }

    if (!track.checkout_url) {
      setPurchaseError('This track is not configured with a payment link yet.');
      setPurchaseModal({
        isOpen: true,
        track,
      });
      return;
    }

    setPurchaseError(null);
    setPurchaseModal({
      isOpen: true,
      track,
    });
  };

  const handleDownloadTrack = (track) => {
    api.get(`/tracks/${track.id}/download`)
      .then((response) => {
        const downloadUrl = response.data.download_url || response.data.full_file_path;
        if (!downloadUrl) {
          throw new Error('Download URL not found');
        }

        const link = document.createElement('a');
        link.href = downloadUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.download = '';
        document.body.appendChild(link);
        link.click();
        link.remove();
      })
      .catch((err) => {
        console.error('Error downloading track:', err);
      });
  };

  const closePurchaseModal = () => {
    setPurchaseModal({
      isOpen: false,
      track: null,
    });
    setPurchaseError(null);
  };

  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('userEmail');
    setUser(null);
    setIsPlaying(false);
    setCurrentTrack(null);
    setPurchaseIds([]);
    setPendingPurchaseTrack(null);
    closePurchaseModal();
  };

  const openAuthModal = (mode) => {
    setAuthModal({
      isOpen: true,
      mode,
    });
  };

  const closeAuthModal = () => {
    setAuthModal((current) => ({
      ...current,
      isOpen: false,
    }));
  };

  const handleAuthSuccess = (email) => {
    fetchCurrentUser()
      .then(() => {
        fetchPurchases();
        if (pendingPurchaseTrack) {
          setPurchaseModal({
            isOpen: true,
            track: pendingPurchaseTrack,
          });
          setPendingPurchaseTrack(null);
        }
      })
      .catch((err) => {
        console.error('Error loading user after auth:', err);
      });
  };

  const handlePurchaseConfirm = async () => {
    if (!purchaseModal.track) return;

    setIsPurchasing(true);
    setPurchaseError(null);

    try {
      const response = await api.post(`/tracks/${purchaseModal.track.id}/checkout`);
      const checkoutUrl = response.data.checkout_url;
      if (!checkoutUrl) {
        throw new Error('Checkout URL not found');
      }

      window.open(checkoutUrl, '_blank', 'noopener,noreferrer');
      closePurchaseModal();
    } catch (err) {
      console.error('Error purchasing track:', err);
      setPurchaseError(
        err.response?.data?.detail || 'Could not start checkout. Please try again.'
      );
    } finally {
      setIsPurchasing(false);
    }
  };

  const handlePlayPause = (playing) => {
    setIsPlaying(playing);
  };

  const handleUploadChange = (event) => {
    const { name, value, files } = event.target;

    setUploadForm((current) => ({
      ...current,
      [name]: files ? files[0] : value,
    }));
    setUploadError(null);
    setUploadSuccess(null);
  };

  const handleUploadSubmit = async (event) => {
    event.preventDefault();
    setIsUploading(true);
    setUploadError(null);
    setUploadSuccess(null);

    try {
      const formData = new FormData();
      formData.append('title', uploadForm.title);
      formData.append('artist', uploadForm.artist);
      formData.append('price', uploadForm.price);
      if (uploadForm.checkoutUrl) {
        formData.append('checkout_url', uploadForm.checkoutUrl);
      }
      if (uploadForm.coverFile) {
        formData.append('cover_file', uploadForm.coverFile);
      }
      formData.append('track_file', uploadForm.trackFile);
      formData.append('preview_file', uploadForm.previewFile);

      const response = await api.post('/tracks/upload', formData);
      setUploadSuccess('Track uploaded successfully.');
      setUploadForm({
        title: '',
        artist: '',
        price: '',
        checkoutUrl: '',
        coverFile: null,
        trackFile: null,
        previewFile: null,
      });
      setUploadFormKey((current) => current + 1);
      await fetchTracks();
      setCurrentTrack(response.data);
      setIsPlaying(false);
    } catch (err) {
      console.error('Error uploading track:', err);
      setUploadError('Track upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100">
      {/* Header / Navbar */}
      <header className="sticky top-0 z-40 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-purple-600 to-blue-600 p-2 rounded-lg">
              <Music size={28} className="text-white" />
            </div>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              DJ Bilal Music Store
            </h1>
          </div>

          {/* Auth Buttons */}
          <div className="flex items-center gap-4">
            {user ? (
              <>
                <div className="flex items-center gap-2 text-slate-300">
                  <User size={18} className="text-purple-400" />
                  <span>
                    Welcome, <span className="text-purple-400 font-semibold">{user.email}</span>
                  </span>
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
                  onClick={() => openAuthModal('login')}
                  className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors duration-200 font-semibold"
                >
                  <LogIn size={18} />
                  Sign In
                </button>
                <button
                  onClick={() => openAuthModal('register')}
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

      <AuthModal
        isOpen={authModal.isOpen}
        initialMode={authModal.mode}
        onClose={closeAuthModal}
        onSuccess={handleAuthSuccess}
      />

      <PurchaseModal
        isOpen={purchaseModal.isOpen}
        track={purchaseModal.track}
        onClose={closePurchaseModal}
        onConfirm={handlePurchaseConfirm}
        loading={isPurchasing}
        error={purchaseError}
      />

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-6 py-12">
        {/* Page Title */}
        <div className="mb-12">
          <h2 className="text-4xl font-bold mb-2">Available Tracks</h2>
          <p className="text-slate-400">Discover amazing music from around the world</p>
        </div>

        {isAdmin && (
          <section className="mb-12 bg-slate-800 border border-slate-700 rounded-2xl p-6">
            <div className="mb-6">
              <h3 className="text-2xl font-bold mb-2">Upload New Track</h3>
              <p className="text-slate-400">
                Full şarkı dosyasını ve ayrı bir preview dosyasını yükle.
              </p>
            </div>

            <form
              key={uploadFormKey}
              onSubmit={handleUploadSubmit}
              className="grid grid-cols-1 md:grid-cols-2 gap-4"
            >
              <input
                name="title"
                value={uploadForm.title}
                onChange={handleUploadChange}
                placeholder="Track title"
                className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500"
                required
              />
              <input
                name="artist"
                value={uploadForm.artist}
                onChange={handleUploadChange}
                placeholder="Artist"
                className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500"
                required
              />
              <input
                name="price"
                type="number"
                step="0.01"
                min="0.01"
                value={uploadForm.price}
                onChange={handleUploadChange}
                placeholder="Price"
                className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500"
                required
              />
              <input
                name="checkoutUrl"
                value={uploadForm.checkoutUrl}
                onChange={handleUploadChange}
                placeholder="Lemon Squeezy checkout URL"
                className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500 md:col-span-2"
              />
              <div className="text-slate-400 text-sm md:self-end">
                Preview dosyası ayrı yüklenir; bu dosya çalınacak dosyadır.
              </div>
              <label className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-300 cursor-pointer">
                <span className="block text-sm mb-1">Cover image (optional)</span>
                <input
                  name="coverFile"
                  type="file"
                  accept="image/*"
                  onChange={handleUploadChange}
                  className="block w-full text-sm text-slate-300"
                />
              </label>
              <label className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-300 cursor-pointer">
                <span className="block text-sm mb-1">Full track file</span>
                <input
                  name="trackFile"
                  type="file"
                  accept="audio/*"
                  onChange={handleUploadChange}
                  className="block w-full text-sm text-slate-300"
                  required
                />
              </label>
              <label className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-slate-300 cursor-pointer">
                <span className="block text-sm mb-1">Preview file</span>
                <input
                  name="previewFile"
                  type="file"
                  accept="audio/*"
                  onChange={handleUploadChange}
                  className="block w-full text-sm text-slate-300"
                  required
                />
              </label>
              <div className="md:col-span-2 flex items-center gap-4">
                <button
                  type="submit"
                  disabled={isUploading}
                  className="bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white px-5 py-3 rounded-lg font-semibold"
                >
                  {isUploading ? 'Uploading...' : 'Upload Track'}
                </button>
                {uploadSuccess && <span className="text-emerald-400">{uploadSuccess}</span>}
              </div>
              {uploadError && (
                <div className="md:col-span-2 bg-red-900/20 border border-red-600 text-red-400 p-4 rounded-lg">
                  {uploadError}
                </div>
              )}
            </form>
          </section>
        )}

        {/* Loading State */}
        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[...Array(8)].map((_, i) => (
              <div
                key={i}
                className="bg-slate-800 rounded-lg animate-pulse"
              >
                <div className="aspect-square bg-slate-700" />
                <div className="p-4 space-y-3">
                  <div className="h-4 bg-slate-700 rounded w-3/4" />
                  <div className="h-4 bg-slate-700 rounded w-1/2" />
                  <div className="h-8 bg-slate-700 rounded w-1/3" />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-900/20 border border-red-600 text-red-400 p-6 rounded-lg">
            {error}
          </div>
        )}

        {/* Tracks Grid */}
        {!loading && !error && (
          <>
            {tracks.length === 0 ? (
              <div className="text-center py-12">
                <Music size={48} className="mx-auto text-slate-500 mb-4" />
                <p className="text-slate-400 text-lg">No tracks available yet.</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 pb-32">
                {tracks.map((track) => {
                  const isPurchased = purchaseIds.includes(track.id);

                  return (
                    <TrackCard
                      key={track.id}
                      track={track}
                      onPlay={handlePlayPreview}
                      onBuy={handleBuyTrack}
                      onDownload={handleDownloadTrack}
                      isPurchased={isPurchased}
                    />
                  );
                })}
              </div>
            )}
          </>
        )}
      </main>

      {/* Bottom Audio Player */}
      <AudioPlayer
        track={currentTrack}
        isPlaying={isPlaying}
        onPlayPause={handlePlayPause}
      />
    </div>
  );
}

export default App;
