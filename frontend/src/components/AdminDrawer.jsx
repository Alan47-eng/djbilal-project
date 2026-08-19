import React, { useEffect, useMemo, useState } from 'react';
import {
  X,
  Upload,
  Users,
  ShieldCheck,
  PlusCircle,
  LayoutGrid,
  Music,
  Gift,
  Library,
  LogIn,
  UserPlus,
  LogOut,
} from 'lucide-react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { useTracks } from '../context/TrackContext';

const emptyForm = {
  title: '',
  artist: '',
  category: 'edit',
  price: '',
  checkout_url: '',
  lemon_variant_id: '',
  is_free: false,
  track_file: null,
  preview_file: null,
  cover_file: null,
};

const AdminDrawer = ({ isOpen, onClose, activeTab, onNavigate, onOpenAuth, onLogout }) => {
  const { user } = useAuth();
  const { fetchTracks } = useTracks();
  const [users, setUsers] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);
  const [form, setForm] = useState(emptyForm);

  const isAdmin = user?.is_admin === true;

  const menuItems = useMemo(() => ([
    { id: 'edits', label: 'Edits', icon: <LayoutGrid size={16} /> },
    { id: 'remixes', label: 'Remixes', icon: <Music size={16} /> },
    { id: 'free', label: 'Free', icon: <Gift size={16} /> },
    ...(user ? [{ id: 'library', label: 'My Library', icon: <Library size={16} /> }] : []),
  ]), [user]);

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

  const handleChange = (key) => (event) => {
    if (key === 'is_free') {
      const checked = event.target.checked;
      setForm((prev) => ({
        ...prev,
        is_free: checked,
        category: checked
          ? (prev.category === 'edit' ? 'remix' : prev.category)
          : (['simple-pack', 'vst'].includes(prev.category) ? 'edit' : prev.category),
        price: checked ? '0' : prev.price === '0' ? '' : prev.price,
        checkout_url: checked ? '' : prev.checkout_url,
        lemon_variant_id: checked ? '' : prev.lemon_variant_id,
      }));
      return;
    }

    let value;
    if (event.target.type === 'file') {
      value = event.target.files?.[0] || null;
    } else if (event.target.type === 'checkbox') {
      value = event.target.checked;
    } else {
      value = event.target.value;
    }
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
    if (!form.category) {
      setError('Category is required');
      return;
    }
    if (!form.is_free && !form.price) {
      setError('Paid tracks require a price');
      return;
    }
    if (!form.is_free && !form.lemon_variant_id) {
      setError('Paid tracks require a Lemon variant ID');
      return;
    }

    try {
      setUploading(true);
      setMessage(null);
      setError(null);

      const formData = new FormData();
      formData.append('title', form.title);
      formData.append('artist', form.artist);
      formData.append('category', form.category);
      formData.append('price', form.is_free ? '0' : form.price);
      formData.append('is_free', form.is_free ? 'true' : 'false');
      if (!form.is_free && form.checkout_url) {
        formData.append('checkout_url', form.checkout_url);
      }
      if (!form.is_free && form.lemon_variant_id) {
        formData.append('lemon_variant_id', form.lemon_variant_id);
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
        className={`absolute left-0 top-0 flex h-full w-full ${isAdmin ? 'max-w-md' : 'max-w-sm'} flex-col border-r border-slate-700 bg-slate-900 text-slate-100 shadow-2xl`}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">{isAdmin ? 'Admin Panel' : 'Menu'}</h2>
            <p className="text-sm text-slate-400">{user ? user.email : 'DJ Bilal Music Store'}</p>
          </div>
          <button onClick={onClose} className="rounded-full p-2 hover:bg-slate-800">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-3 border-b border-slate-800 px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Site Menu</p>
          <div className="grid grid-cols-2 gap-2">
            {menuItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate?.(item.id)}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                  activeTab === item.id
                    ? 'border-purple-500 bg-purple-600/20 text-purple-200'
                    : 'border-slate-700 bg-slate-800 text-slate-200 hover:bg-slate-700'
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {!user && (
          <div className="space-y-2 border-b border-slate-800 px-5 py-4">
            <button
              type="button"
              onClick={() => onOpenAuth?.('login')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-slate-700 px-4 py-2.5 font-semibold text-white hover:bg-slate-600"
            >
              <LogIn size={16} />
              Sign In
            </button>
            <button
              type="button"
              onClick={() => onOpenAuth?.('register')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-purple-600 px-4 py-2.5 font-semibold text-white hover:bg-purple-700"
            >
              <UserPlus size={16} />
              Sign Up
            </button>
          </div>
        )}

        {user && !isAdmin && (
          <div className="space-y-2 border-b border-slate-800 px-5 py-4">
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500">Account</p>
            <button
              type="button"
              onClick={onLogout}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-red-600 px-4 py-2.5 font-semibold text-white hover:bg-red-700"
            >
              <LogOut size={16} />
              Logout
            </button>
          </div>
        )}

        {!isAdmin ? (
          <div className="px-5 py-4 text-sm text-slate-400">
            Quickly navigate edits, remixes, and free tracks from here.
          </div>
        ) : (
          <>
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
                  <label className="flex cursor-pointer select-none items-center gap-3 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2">
                    <input
                      type="checkbox"
                      checked={form.is_free}
                      onChange={handleChange('is_free')}
                      className="h-4 w-4 accent-emerald-500"
                    />
                    <span className="text-sm text-slate-300">Free downloadable track (FREE)</span>
                  </label>
                  <label className="block text-sm text-slate-300">
                    Category
                    <select
                      key={form.is_free ? 'free-category' : 'paid-category'}
                      value={form.category}
                      onChange={handleChange('category')}
                      className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                      required
                    >
                      {form.is_free ? (
                        <>
                          <option value="remix">Remix</option>
                          <option value="simple-pack">Simple Pack</option>
                          <option value="vst">VST</option>
                        </>
                      ) : (
                        <>
                          <option value="edit">Edit</option>
                          <option value="remix">Remix</option>
                        </>
                      )}
                    </select>
                  </label>
                  <p className={`text-xs ${form.is_free ? 'text-emerald-300' : 'text-slate-400'}`}>
                    {form.is_free
                      ? 'Free seciliyken kategori: Remix, Simple Pack veya VST.'
                      : 'Paid seciliyken kategori: Edit veya Remix.'}
                  </p>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={form.price}
                    onChange={handleChange('price')}
                    placeholder={form.is_free ? '0.00 for free tracks' : 'Price'}
                    className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                    required={!form.is_free}
                    disabled={form.is_free}
                  />
                  {!form.is_free && (
                    <>
                      <input
                        value={form.checkout_url}
                        onChange={handleChange('checkout_url')}
                        placeholder="Lemon Squeezy checkout URL"
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                      />
                      <input
                        type="number"
                        min="1"
                        step="1"
                        value={form.lemon_variant_id}
                        onChange={handleChange('lemon_variant_id')}
                        placeholder="Lemon Squeezy variant ID"
                        className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                        required={!form.is_free}
                      />
                      <p className="text-xs text-slate-400">
                        For cart checkout, each paid track should have its own Lemon variant ID.
                      </p>
                    </>
                  )}

                  {form.is_free && (
                    <p className="text-xs text-emerald-300">
                      Free tracks do not require a separate URL; the full file becomes downloadable automatically.
                    </p>
                  )}
                  <label className="block text-sm text-slate-300">
                    Track file
                    <input type="file" accept=".mp3,.wav,.m4a,.flac,.ogg,audio/*" onChange={handleChange('track_file')} className="mt-1 block w-full text-sm" required />
                  </label>
                  <label className="block text-sm text-slate-300">
                    Preview file
                    <input type="file" accept=".mp3,.wav,.m4a,.flac,.ogg,audio/*" onChange={handleChange('preview_file')} className="mt-1 block w-full text-sm" required />
                  </label>
                  <label className="block text-sm text-slate-300">
                    Cover image
                    <input type="file" accept=".png,.jpg,.jpeg,.webp,image/*" onChange={handleChange('cover_file')} className="mt-1 block w-full text-sm" />
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
          </>
        )}
      </aside>
    </div>
  );
};

export default AdminDrawer;
