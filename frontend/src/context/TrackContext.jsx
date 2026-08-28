import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';

const TrackContext = createContext(null);

export function TrackProvider({ children }) {
  const [tracks, setTracks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchTracks();
  }, []);

  const fetchTracks = async () => {
    try {
      setLoading(true);
      const response = await api.get('/tracks');
      setTracks(response.data);
      setError(null);
    } catch (err) {
      if (!err.response) {
        setError(`Failed to load tracks (API unreachable: ${api.defaults.baseURL})`);
      } else {
        setError(err.response?.data?.detail || 'Failed to load tracks');
      }
    } finally {
      setLoading(false);
    }
  };

  const addTrack = (newTrack) => {
    setTracks(prev => [newTrack, ...prev]);
  };

  const updateTrack = (updatedTrack) => {
    setTracks(prev => prev.map(track => track.id === updatedTrack.id ? updatedTrack : track));
  };

  const removeTrack = (trackId) => {
    setTracks(prev => prev.filter(track => track.id !== trackId));
  };

  return (
    <TrackContext.Provider value={{ tracks, loading, error, fetchTracks, addTrack, updateTrack, removeTrack }}>
      {children}
    </TrackContext.Provider>
  );
}

export function useTracks() {
  const context = useContext(TrackContext);
  if (!context) {
    throw new Error('useTracks must be used within TrackProvider');
  }
  return context;
}
