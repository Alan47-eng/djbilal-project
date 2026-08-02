import React, { useEffect, useMemo, useState } from 'react';
import { X, Upload, Users, ShieldCheck, PlusCircle } from 'lucide-react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { useTracks } from '../context/TrackContext';

const emptyForm = {
  title: '',
  artist: '',
  price: '',
  checkout_url: '',
  track_file: null,
  preview_file: null,
  cover_file: null,
};

const AdminDrawer = ({ isOpen, onClose }) => {
  const { user } = useAuth();
  const { fetchTracks } = useTracks();
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const isAdmin = user?.is_admin === true;

  const stats = useMemo(() => [
    { label: 'Tracks', value: 'Catalog' },
    { label: 'Sales', value: 'Lemon Squeezy' },
    { label: 'Access', value: isAdmin ? 'Admin' : 'Member' },
  ], [isAdmin]);

  useEffect(() => {
    if (!isOpen || !isAdmin) return;

    const loadUsers = async () => {
      try {
        setLoadingUsers(true);
        const response = await api.get('/users');
        setUsers(response.data);
        setError(null);
      } catch (err) {
        setError(err.response?.data?.detail || 'Could not load users');
      } finally {
        setLoadingUsers(false);
      }
    };

    loadUsers();
  }, [isOpen, isAdmin]);

  useEffect(() => {
    if (!isOpen) {
      setForm(emptyForm);
      setMessage(null);
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  if (!isAdmin) {
    return (
      <div className="fixed inset-0 z-50 bg-black/60" onClick={onClose}>
        <div
          className="absolute left-0 top-0 h-full w-full max-w-sm border-r border-slate-700 bg-slate-900 p-6 text-slate-200"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-xl font-bold">Menu</h2>
            <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-800">
              <X size={18} />
            </button>
          </div>
          <p className="text-sm text-slate-400">Admin tools are only visible for admin accounts.</p>
        </div>
      </div>
    );
  }

  const handleChange = (key) => (event) => {
    const value = event.target.type === 'file' ? event.target.files?.[0] || null : event.target.value;
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handlePromote = async (email) => {
    try {
      setMessage(null);
      setError(null);
      await api.post(`/users/${encodeURIComponent(email)}/make-admin`);
      const response = await api.get('/users');
      setUsers(response.data);
      setMessage(`${email} was promoted to admin`);
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not promote user');
    }
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!form.track_file || !form.preview_file) {
      setError('Track and preview files are required');
      return;
    }

    try {
      setUploading(true);
      setMessage(null);
      setError(null);

      const formData = new FormData();
      formData.append('title', form.title);
      formData.append('artist', form.artist);
      formData.append('price', form.price);
      if (form.checkout_url) {
        formData.append('checkout_url', form.checkout_url);
      }
      formData.append('track_file', form.track_file);
      formData.append('preview_file', form.preview_file);
      if (form.cover_file) {
        formData.append('cover_file', form.cover_file);
      }

      await api.post('/tracks/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      await fetchTracks();
      setForm(emptyForm);
      setMessage('Track added');
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not add track');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/60" onClick={onClose}>
      <aside
        className="absolute left-0 top-0 flex h-full w-full max-w-md flex-col border-r border-slate-700 bg-slate-900 text-slate-100 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">Admin Panel</h2>
            <p className="text-sm text-slate-400">{user.email}</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-800">
            <X size={18} />
          </button>
        </div>

        <div className="grid grid-cols-3 gap-3 border-b border-slate-800 px-5 py-4 text-xs">
          {stats.map((item) => (
            <div key={item.label} className="rounded-lg bg-slate-800 px-3 py-2">
              <div className="text-slate-400">{item.label}</div>
              <div className="font-semibold text-white">{item.value}</div>
            </div>
          ))}
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto px-5 py-5">
          <section className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-2">
              <Upload size={18} className="text-purple-400" />
              <h3 className="font-semibold">Add Track</h3>
            </div>
            <form className="space-y-3" onSubmit={handleSubmit}>
              <input
                value={form.title}
                onChange={handleChange('title')}
                placeholder="Title"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                required
              />
              <input
                value={form.artist}
                onChange={handleChange('artist')}
                placeholder="Artist"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                required
              />
              <input
                type="number"
                step="0.01"
                value={form.price}
                onChange={handleChange('price')}
                placeholder="Price"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                required
              />
              <input
                value={form.checkout_url}
                onChange={handleChange('checkout_url')}
                placeholder="Lemon Squeezy checkout URL"
                className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
              />
              <p className="text-xs text-slate-400">
                Add a separate checkout URL for each track. If they share the same product, you can reuse the same URL.
              </p>
              <label className="block text-sm text-slate-300">
                Track file
                <input type="file" onChange={handleChange('track_file')} className="mt-1 block w-full text-sm" required />
              </label>
              <label className="block text-sm text-slate-300">
                Preview file
                <input type="file" onChange={handleChange('preview_file')} className="mt-1 block w-full text-sm" required />
              </label>
              <label className="block text-sm text-slate-300">
                Cover image
                <input type="file" onChange={handleChange('cover_file')} className="mt-1 block w-full text-sm" />
              </label>

              {message && <p className="text-sm text-emerald-400">{message}</p>}
              {error && <p className="text-sm text-red-300">{error}</p>}

              <button
                type="submit"
                disabled={uploading}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-3 font-semibold text-white hover:bg-purple-700 disabled:opacity-60"
              >
                <PlusCircle size={16} />
                {uploading ? 'Adding...' : 'Add Track'}
              </button>
            </form>
          </section>

          <section className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-2">
              <Users size={18} className="text-purple-400" />
              <h3 className="font-semibold">Users</h3>
            </div>
            {loadingUsers ? (
              <p className="text-sm text-slate-400">Loading...</p>
            ) : (
              <div className="space-y-2">
                {users.map((item) => (
                  <div key={item.id} className="flex items-center justify-between rounded-lg border border-slate-800 px-3 py-2">
                    <div>
                      <p className="text-sm font-medium text-white">{item.email}</p>
                      <p className="text-xs text-slate-400">{item.is_admin ? 'Admin' : 'Member'}</p>
                    </div>
                    {!item.is_admin && (
                      <button
                        type="button"
                        onClick={() => handlePromote(item.email)}
                        className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700"
                      >
                        <ShieldCheck size={14} />
                        Make Admin
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </section>
        </div>
      </aside>
    </div>
  );
};

export default AdminDrawer;
