import { useState } from 'react';
import api from '../api';
import { getApiErrorMessage } from '../utils/errors';

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
      const errorMsg = getApiErrorMessage(err, 'Upload failed');
      setError(errorMsg);
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { uploadTrack, loading, error };
}
