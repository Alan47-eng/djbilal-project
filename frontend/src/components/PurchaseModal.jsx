import React, { useEffect, useState } from 'react';
import { X, ExternalLink } from 'lucide-react';

const PurchaseModal = ({ isOpen, track, onClose, onConfirm, loading = false, error = null }) => {
  const [loadingState, setLoadingState] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoadingState(false);
  }, [isOpen, track]);

  if (!isOpen || !track) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLoadingState(true);
    const result = await onConfirm();
    if (!result) {
      setLoadingState(false);
    }
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-2xl font-bold text-white">Checkout</h3>
            <p className="text-sm text-slate-400">
              {track.title} • {track.artist}
            </p>
            <p className="text-sm text-purple-400 font-semibold">${track.price.toFixed(2)}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-full p-2 text-slate-400 hover:bg-slate-800 hover:text-white"
          >
            <X size={18} />
          </button>
        </div>

        <div className="mb-4 flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-950 p-3 text-slate-300">
          <ExternalLink size={18} className="text-purple-400" />
          <span>You&apos;ll be redirected to Lemon Squeezy’s secure checkout page.</span>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-lg border border-red-600 bg-red-900/20 p-3 text-sm text-red-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || loadingState}
            className="w-full rounded-lg bg-emerald-600 px-4 py-3 font-semibold text-white hover:bg-emerald-700 disabled:opacity-60"
          >
            {loading || loadingState ? 'Redirecting...' : 'Proceed to Checkout'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default PurchaseModal;
