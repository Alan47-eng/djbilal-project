import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../api';
import { useAuth } from './AuthContext';

const PurchaseContext = createContext(null);

export function PurchaseProvider({ children }) {
  const { user } = useAuth();
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (user) {
      fetchPurchases();
    } else {
      setPurchases([]);
    }
  }, [user]);

  const fetchPurchases = async () => {
    try {
      setLoading(true);
      const response = await api.get('/purchases');
      setPurchases(response.data);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load purchases');
    } finally {
      setLoading(false);
    }
  };

  const addPurchase = (trackId) => {
    setPurchases(prev => [...prev, trackId]);
  };

  const hasPurchased = (trackId) => {
    return purchases.includes(trackId);
  };

  return (
    <PurchaseContext.Provider value={{ purchases, loading, error, fetchPurchases, addPurchase, hasPurchased }}>
      {children}
    </PurchaseContext.Provider>
  );
}

export function usePurchases() {
  const context = useContext(PurchaseContext);
  if (!context) {
    throw new Error('usePurchases must be used within PurchaseProvider');
  }
  return context;
}
