import { useState } from 'react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { usePurchases } from '../context/PurchaseContext';

export function useCheckout() {
  const { user } = useAuth();
  const { addPurchase } = usePurchases();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const checkout = async (trackId) => {
    if (!user) {
      setError('You must be logged in to purchase');
      return null;
    }

    try {
      setLoading(true);
      const response = await api.post(`/tracks/${trackId}/checkout`);
      setError(null);
      return response.data.checkout_url;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Checkout failed';
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { checkout, loading, error };
}

export function useDownload() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const download = async (trackId) => {
    if (!user) {
      setError('You must be logged in to download');
      return null;
    }

    try {
      setLoading(true);
      const response = await api.get(`/tracks/${trackId}/download`);
      setError(null);
      return response.data.download_url;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Download failed';
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { download, loading, error };
}

export function useTrackUpload() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const uploadTrack = async (formData) => {
    try {
      setLoading(true);
      const response = await api.post('/tracks/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setError(null);
      return response.data;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Upload failed';
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { uploadTrack, loading, error };
}
