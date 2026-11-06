import React, { useEffect, useState } from 'react';
import {
  Album as AlbumIcon,
  Music,
  Settings,
  ShieldCheck,
  Trash2,
  Users,
  X,
  Plus,
} from 'lucide-react';
import api from '../api';
import { useAuth } from '../context/AuthContext';
import { useTracks } from '../context/TrackContext';
import { useLanguage } from '../context/LanguageContext';
import { getApiErrorMessage } from '../utils/errors';

const initialTrackForm = {
  title: '',
  artist: '',
  category: 'edit',
  price: '',
  gumroad_url: '',
  gumroad_product_id: '',
  album_id: '',
  is_free: false,
  track_file: null,
  preview_file: null,
  cover_file: null,
};

const fieldClass =
  'w-full rounded-lg border border-[#45463f] bg-[#1f201d] px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-[#858a70] focus:outline-none';
const buttonClass =
  'inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50';

const AdminDashboard = ({ onClose, onNavigate, onLogout }) => {
  const { user } = useAuth();
  const { lang, isRTL } = useLanguage();
  const { tracks, fetchTracks, updateTrack, removeTrack } = useTracks();
  const t = lang === 'ar' ? {
    dashboard: 'لوحة الإدارة', users: 'إدارة المستخدمين', albums: 'الألبومات', tracks: 'المقاطع', settings: 'الإعدادات',
    siteSections: 'أقسام الموقع', free: 'مجاني', library: 'مكتبتي',
    logout: 'تسجيل الخروج', close: 'إغلاق', loading: 'جارٍ تحميل البيانات...', email: 'البريد الإلكتروني',
    name: 'الاسم', role: 'الدور', action: 'الإجراء', admin: 'مسؤول', user: 'مستخدم', saving: 'جارٍ الحفظ...',
    demote: 'إزالة صلاحية المسؤول', promote: 'ترقية إلى مسؤول', noUsers: 'لم يتم العثور على مستخدمين.',
    albumTitle: 'عنوان الألبوم', coverUrl: 'رابط الغلاف', coverFile: 'تحميل صورة الغلاف',
    releaseDate: 'تاريخ الإصدار', creating: 'جارٍ الإنشاء...', createAlbum: 'إنشاء ألبوم', save: 'حفظ',
    albumCover: 'غلاف الألبوم', noAlbums: 'لا توجد ألبومات بعد.', trackName: 'اسم المقطع', artist: 'الفنان',
    selectAlbum: 'اختر ألبومًا', single: 'منفرد', price: 'السعر', freeCheckbox: 'مجاني',
    productUrl: 'رابط منتج Gumroad', productId: 'معرّف المنتج', trackFile: 'ملف المقطع',
    previewFile: 'ملف المعاينة', addTrack: 'إضافة مقطع', adding: 'جارٍ الإضافة...', track: 'المقطع',
    operations: 'الإجراءات', noTracks: 'لا توجد مقاطع بعد.', adminAccount: 'حساب المسؤول', addTrackToAlbum: 'إضافة أغنية', paid: 'مدفوع',
    settingsDescription: 'تتم إدارة إعدادات الدفع والبريد الإلكتروني والتخزين من متغيرات بيئة الخادم لأسباب أمنية، ولا تظهر هنا.',
    invalidPrice: 'يجب أن يكون سعر المقطع رقمًا صالحًا أكبر من صفر.',
    requiredTrackFiles: 'ملف المقطع وملف المعاينة مطلوبان.',
    paidTrackFields: 'السعر ورابط Gumroad مطلوبان للمقاطع المدفوعة.',
    deleteAlbumConfirm: (title) => `هل تريد حذف الألبوم "${title}"؟ ستبقى المقاطع كإصدارات منفردة.`,
    deleteTrackConfirm: (title) => `هل تريد حذف المقطع "${title}"؟`,
    roleAdmin: 'تمت ترقية المستخدم إلى مسؤول.', roleUser: 'تمت إزالة صلاحية المسؤول.',
    roleError: 'تعذر تحديث دور المستخدم.', loadError: 'تعذر تحميل البيانات.',
    albumCreated: 'تم إنشاء الألبوم.', albumCreateError: 'تعذر إنشاء الألبوم.',
    albumUpdated: 'تم تحديث الألبوم.', albumUpdateError: 'تعذر تحديث الألبوم.',
    albumDeleted: 'تم حذف الألبوم؛ وحُفظت المقاطع كإصدارات منفردة.', albumDeleteError: 'تعذر حذف الألبوم.',
    trackUpdated: 'تم تحديث معلومات المقطع.', trackUpdateError: 'تعذر تحديث المقطع.',
    trackDeleted: 'تم حذف المقطع.', trackDeleteError: 'تعذر حذف المقطع.',
    trackAdded: 'تمت إضافة المقطع إلى المكتبة.', trackAddError: 'تعذر إضافة المقطع.',
  } : {
    dashboard: 'Admin Dashboard', users: 'User Management', albums: 'Albums', tracks: 'Tracks', settings: 'Settings',
    siteSections: 'Site sections', free: 'Free', library: 'My Library',
    logout: 'Log out', close: 'Close', loading: 'Loading data...', email: 'Email', name: 'Name', role: 'Role',
    action: 'Action', admin: 'Admin', user: 'User', saving: 'Saving...', demote: 'Remove admin role',
    promote: 'Promote to admin', noUsers: 'No users found.', albumTitle: 'Album title',
    coverUrl: 'Cover image URL', coverFile: 'Upload cover image', releaseDate: 'Release date',
    creating: 'Creating...', createAlbum: 'Create album', save: 'Save', albumCover: 'Album cover',
    noAlbums: 'No albums yet.', trackName: 'Track title', artist: 'Artist', selectAlbum: 'Select album',
    single: 'Single', price: 'Price', freeCheckbox: 'Free',
    productUrl: 'Gumroad product URL', productId: 'Product ID', trackFile: 'Track file',
    previewFile: 'Preview file', addTrack: 'Add track', adding: 'Adding...', track: 'Track',
    operations: 'Actions', noTracks: 'No tracks yet.', adminAccount: 'Administrator account', addTrackToAlbum: 'Add song', paid: 'Paid',
    settingsDescription: 'Payment, email, and storage settings are managed through server environment variables for security and are not displayed here.',
    invalidPrice: 'Track price must be a valid number greater than zero.',
    requiredTrackFiles: 'Track and preview files are required.',
    paidTrackFields: 'Paid tracks require a price and Gumroad URL.',
    deleteAlbumConfirm: (title) => `Delete album "${title}"? Its tracks will remain as singles.`,
    deleteTrackConfirm: (title) => `Delete track "${title}"?`,
    roleAdmin: 'User promoted to admin.', roleUser: 'Admin role removed.',
    roleError: 'Could not update user role.', loadError: 'Could not load data.',
    albumCreated: 'Album created.', albumCreateError: 'Could not create album.',
    albumUpdated: 'Album updated.', albumUpdateError: 'Could not update album.',
    albumDeleted: 'Album deleted; its tracks were kept as singles.', albumDeleteError: 'Could not delete album.',
    trackUpdated: 'Track information updated.', trackUpdateError: 'Could not update track.',
    trackDeleted: 'Track deleted.', trackDeleteError: 'Could not delete track.',
    trackAdded: 'Track added to the catalog.', trackAddError: 'Could not add track.',
  };
  const [tab, setTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [albums, setAlbums] = useState([]);
  const [albumDrafts, setAlbumDrafts] = useState({});
  const [trackDrafts, setTrackDrafts] = useState({});
  const [trackForm, setTrackForm] = useState(initialTrackForm);
  const [newAlbum, setNewAlbum] = useState({ title: '', cover_image_url: '', cover_file: null, release_date: '' });
  const [loading, setLoading] = useState(false);
  const [savingKey, setSavingKey] = useState('');
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [userResponse, albumResponse] = await Promise.all([
        api.get('/users'),
        api.get('/albums'),
      ]);
      setUsers(userResponse.data);
      setAlbums(albumResponse.data);
      setAlbumDrafts(Object.fromEntries(
        albumResponse.data.map((album) => [album.id, {
          title: album.title,
          cover_image_url: album.cover_image_url || '',
          release_date: album.release_date || '',
        }]),
      ));
    } catch (requestError) {
      setError(getApiErrorMessage(requestError, t.loadError));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadData();
    void fetchTracks();
  }, []);

  const showError = (requestError, fallback) => {
    setNotice('');
    setError(getApiErrorMessage(requestError, fallback));
  };

  const saveRole = async (target, role) => {
    setSavingKey(`user-${target.id}`);
    setError('');
    setNotice('');
    try {
      const response = await api.put(`/api/v1/users/${target.id}/role`, { role });
      setUsers((current) => current.map((item) => item.id === target.id ? response.data : item));
      setNotice(role === 'admin' ? t.roleAdmin : t.roleUser);
    } catch (requestError) {
      showError(requestError, t.roleError);
    } finally {
      setSavingKey('');
    }
  };

  const createAlbum = async (event) => {
    event.preventDefault();
    setSavingKey('new-album');
    setError('');
    setNotice('');
    try {
      let coverImageUrl = newAlbum.cover_image_url.trim() || null;
      if (newAlbum.cover_file) {
        const upload = new FormData();
        upload.append('cover_file', newAlbum.cover_file);
        const uploadResponse = await api.post('/albums/cover-upload', upload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        coverImageUrl = uploadResponse.data.cover_image_url;
      }
      await api.post('/albums', {
        title: newAlbum.title.trim(),
        cover_image_url: coverImageUrl,
        release_date: newAlbum.release_date || null,
      });
      setNewAlbum({ title: '', cover_image_url: '', cover_file: null, release_date: '' });
      await loadData();
      setNotice(t.albumCreated);
    } catch (requestError) {
      showError(requestError, t.albumCreateError);
    } finally {
      setSavingKey('');
    }
  };

  const saveAlbum = async (albumId) => {
    setSavingKey(`album-${albumId}`);
    setError('');
    setNotice('');
    try {
      const draft = albumDrafts[albumId];
      let coverImageUrl = draft.cover_image_url.trim() || null;
      if (draft.cover_file) {
        const upload = new FormData();
        upload.append('cover_file', draft.cover_file);
        const uploadResponse = await api.post('/albums/cover-upload', upload, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        coverImageUrl = uploadResponse.data.cover_image_url;
      }
      const response = await api.put(`/albums/${albumId}`, {
        title: draft.title.trim(),
        cover_image_url: coverImageUrl,
        release_date: draft.release_date || null,
      });
      setAlbums((current) => current.map((album) => album.id === albumId ? response.data : album));
      setAlbumDrafts((current) => ({
        ...current,
        [albumId]: { ...draft, cover_image_url: response.data.cover_image_url || '', cover_file: null },
      }));
      setNotice(t.albumUpdated);
    } catch (requestError) {
      showError(requestError, t.albumUpdateError);
    } finally {
      setSavingKey('');
    }
  };

  const deleteAlbum = async (album) => {
    if (!window.confirm(t.deleteAlbumConfirm(album.title))) return;
    setSavingKey(`album-${album.id}`);
    setError('');
    setNotice('');
    try {
      await api.delete(`/albums/${album.id}`);
      setAlbums((current) => current.filter((item) => item.id !== album.id));
      setTrackDrafts((current) => Object.fromEntries(
        Object.entries(current).map(([id, draft]) => [
          id,
          draft.album_id === String(album.id) ? { ...draft, album_id: '' } : draft,
        ]),
      ));
      await fetchTracks();
      setNotice(t.albumDeleted);
    } catch (requestError) {
      showError(requestError, t.albumDeleteError);
    } finally {
      setSavingKey('');
    }
  };

  const updateTrackDraft = (track, key, value) => {
    setTrackDrafts((current) => ({
      ...current,
      [track.id]: {
        ...current[track.id],
        album_id: String(track.album_id || ''),
        price: String(track.price),
        gumroad_url: track.gumroad_url || track.external_product_id || '',
        gumroad_product_id: track.gumroad_product_id || '',
        [key]: value,
      },
    }));
  };

  const saveTrack = async (track) => {
    const draft = trackDrafts[track.id] || {
      album_id: String(track.album_id || ''),
      price: String(track.price),
      gumroad_url: track.gumroad_url || track.external_product_id || '',
      gumroad_product_id: track.gumroad_product_id || '',
    };
    const price = Number(draft.price);
    if (!Number.isFinite(price) || price < 0 || (!track.is_free && price <= 0)) {
      setError(t.invalidPrice);
      setNotice('');
      return;
    }
    setSavingKey(`track-${track.id}`);
    setError('');
    setNotice('');
    try {
      const response = await api.put(`/tracks/${track.id}`, {
        album_id: draft.album_id ? Number(draft.album_id) : null,
        price: track.is_free ? 0 : Number(price.toFixed(2)),
        gumroad_url: draft.gumroad_url.trim() || null,
        gumroad_product_id: draft.gumroad_product_id.trim() || null,
      });
      updateTrack(response.data);
      setNotice(t.trackUpdated);
    } catch (requestError) {
      showError(requestError, t.trackUpdateError);
    } finally {
      setSavingKey('');
    }
  };

  const deleteTrack = async (track) => {
    if (!window.confirm(t.deleteTrackConfirm(track.title))) return;
    setSavingKey(`track-${track.id}`);
    setError('');
    setNotice('');
    try {
      await api.delete(`/tracks/${track.id}`);
      removeTrack(track.id);
      setNotice(t.trackDeleted);
    } catch (requestError) {
      showError(requestError, t.trackDeleteError);
    } finally {
      setSavingKey('');
    }
  };

  const submitTrack = async (event) => {
    event.preventDefault();
    if (!trackForm.track_file || !trackForm.preview_file) {
      setError(t.requiredTrackFiles);
      return;
    }
    if (!trackForm.is_free && (!trackForm.price || !trackForm.gumroad_url.trim())) {
      setError(t.paidTrackFields);
      return;
    }
    setSavingKey('new-track');
    setError('');
    setNotice('');
    try {
      const data = new FormData();
      data.append('title', trackForm.title);
      data.append('artist', trackForm.artist);
      data.append('category', trackForm.category);
      data.append('price', trackForm.is_free ? '0' : trackForm.price);
      data.append('is_free', String(trackForm.is_free));
      if (trackForm.album_id) data.append('album_id', trackForm.album_id);
      if (!trackForm.is_free) {
        data.append('gumroad_url', trackForm.gumroad_url);
        if (trackForm.gumroad_product_id) data.append('gumroad_product_id', trackForm.gumroad_product_id);
      }
      data.append('track_file', trackForm.track_file);
      data.append('preview_file', trackForm.preview_file);
      if (trackForm.cover_file) data.append('cover_file', trackForm.cover_file);
      await api.post('/tracks/upload', data, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setTrackForm(initialTrackForm);
      await fetchTracks();
      setNotice(t.trackAdded);
    } catch (requestError) {
      showError(requestError, t.trackAddError);
    } finally {
      setSavingKey('');
    }
  };

  const tabs = [
    { id: 'users', label: t.users, icon: Users },
    { id: 'albums', label: t.albums, icon: AlbumIcon },
    { id: 'tracks', label: t.tracks, icon: Music },
    { id: 'settings', label: t.settings, icon: Settings },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-2 sm:p-5" onClick={onClose}>
      <section
        className="flex h-[min(94vh,960px)] w-full max-w-7xl overflow-hidden rounded-2xl border border-[#45463f] bg-[#1d1e1b] text-slate-100 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        aria-label={t.dashboard}
        dir={isRTL ? 'rtl' : 'ltr'}
      >
        <aside className="hidden w-64 shrink-0 flex-col border-r border-[#393a35] bg-[#242521] p-5 md:flex">
          <div className="mb-9">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#c3b898]">DJ Bilal</p>
            <h1 className="mt-2 text-xl font-bold">{t.dashboard}</h1>
          </div>
          <nav className="space-y-2" aria-label={t.dashboard}>
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => { setTab(id); setError(''); setNotice(''); }}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-start text-sm font-semibold transition-colors ${
                  tab === id ? 'bg-[#59604c] text-white' : 'text-slate-300 hover:bg-[#34352f]'
                }`}
              >
                <Icon size={18} />
                {label}
              </button>
            ))}
          </nav>
          <div className="mt-8 border-t border-slate-800 pt-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-slate-500">{t.siteSections}</p>
            {[
              ['albums', t.albums],
              ['free', t.free],
              ['library', t.library],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => { onNavigate?.(id); onClose?.(); }}
                className="block w-full rounded-lg px-3 py-2 text-start text-sm text-slate-400 hover:bg-[#34352f] hover:text-white"
              >
                {label}
              </button>
            ))}
          </div>
          <div className="mt-auto border-t border-slate-800 pt-4">
            <p className="truncate text-xs text-slate-400">{user?.email}</p>
            <button type="button" onClick={onLogout} className={`${buttonClass} mt-3 w-full bg-slate-800 text-slate-200 hover:bg-slate-700`}>
              {t.logout}
            </button>
          </div>
        </aside>

        <main className="flex min-w-0 flex-1 flex-col">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-4 py-4 sm:px-7">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-[#c3b898]">{t.dashboard}</p>
              <h2 className="mt-1 text-xl font-bold sm:text-2xl">{tabs.find((item) => item.id === tab)?.label}</h2>
            </div>
            <button type="button" onClick={onClose} aria-label={t.close} className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white">
              <X size={20} />
            </button>
            <nav className="flex w-full gap-2 overflow-x-auto md:hidden" aria-label={t.dashboard}>
              {tabs.map(({ id, label, icon: Icon }) => (
                <button key={id} type="button" onClick={() => { setTab(id); setError(''); setNotice(''); }}
                  className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold ${
                    tab === id ? 'bg-[#59604c] text-white' : 'bg-[#34352f] text-slate-300'
                  }`}>
                  <Icon size={15} />{label}
                </button>
              ))}
            </nav>
          </header>

          <div className="flex-1 overflow-y-auto p-4 sm:p-7">
            {notice && <p role="status" className="mb-4 rounded-lg border border-emerald-700/60 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-300">{notice}</p>}
            {error && <p role="alert" className="mb-4 rounded-lg border border-red-700/60 bg-red-950/50 px-4 py-3 text-sm text-red-300">{error}</p>}
            {loading ? (
              <p className="py-12 text-center text-sm text-slate-400">{t.loading}</p>
            ) : (
              <>
                {tab === 'users' && (
                  <div className="overflow-hidden rounded-xl border border-slate-800">
                    <div className="overflow-x-auto">
                      <table className="w-full min-w-[680px] text-left text-sm">
                        <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                          <tr><th className="px-5 py-4">{t.email}</th><th className="px-5 py-4">{t.name}</th><th className="px-5 py-4">{t.role}</th><th className="px-5 py-4 text-end">{t.action}</th></tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                          {users.map((item) => (
                            <tr key={item.id} className="bg-slate-950 hover:bg-slate-900/70">
                              <td className="px-5 py-4 font-medium text-white">{item.email}</td>
                              <td className="px-5 py-4 text-slate-300">{item.full_name || '—'}</td>
                              <td className="px-5 py-4"><span className="rounded-full bg-slate-800 px-2.5 py-1 text-xs">{item.is_admin ? t.admin : t.user}</span></td>
                              <td className="px-5 py-4 text-end">
                                <button type="button" disabled={savingKey === `user-${item.id}` || (item.is_admin && item.id === user?.id)}
                                  onClick={() => saveRole(item, item.is_admin ? 'user' : 'admin')}
                                  className={`${buttonClass} ${item.is_admin ? 'bg-amber-700 hover:bg-amber-600' : 'bg-emerald-700 hover:bg-emerald-600'}`}>
                                  <ShieldCheck size={15} />
                                  {savingKey === `user-${item.id}` ? t.saving : item.is_admin ? t.demote : t.promote}
                                </button>
                              </td>
                            </tr>
                          ))}
                          {!users.length && <tr><td colSpan="4" className="px-5 py-10 text-center text-slate-400">{t.noUsers}</td></tr>}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {tab === 'albums' && (
                  <div className="space-y-6">
                    <form onSubmit={createAlbum} className="grid gap-3 rounded-xl border border-[#41423c] bg-[#252622] p-4 md:grid-cols-[1.2fr_1.5fr_1fr_auto] md:items-end">
                      <label className="text-xs font-semibold text-slate-400">{t.albumTitle}<input className={`${fieldClass} mt-2`} required value={newAlbum.title} onChange={(event) => setNewAlbum({ ...newAlbum, title: event.target.value })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.coverUrl}<input type="url" className={`${fieldClass} mt-2`} value={newAlbum.cover_image_url} onChange={(event) => setNewAlbum({ ...newAlbum, cover_image_url: event.target.value })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.coverFile}<input type="file" accept="image/png,image/jpeg,image/webp" className="mt-2 block w-full text-sm" onChange={(event) => setNewAlbum({ ...newAlbum, cover_file: event.target.files?.[0] || null })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.releaseDate}<input type="date" className={`${fieldClass} mt-2`} value={newAlbum.release_date} onChange={(event) => setNewAlbum({ ...newAlbum, release_date: event.target.value })} /></label>
                      <button disabled={savingKey === 'new-album'} className={`${buttonClass} bg-[#59604c] text-white hover:bg-[#687057]`}>{savingKey === 'new-album' ? t.creating : t.createAlbum}</button>
                    </form>
                    <div className="overflow-hidden rounded-xl border border-slate-800">
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[850px] text-left text-sm">
                          <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400"><tr><th className="px-4 py-4">{t.albums}</th><th className="px-4 py-4">{t.albumCover}</th><th className="px-4 py-4">{t.releaseDate}</th><th className="px-4 py-4 text-end">{t.operations}</th></tr></thead>
                          <tbody className="divide-y divide-slate-800">
                            {albums.map((album) => {
                              const draft = albumDrafts[album.id] || { title: album.title, cover_image_url: album.cover_image_url || '', release_date: album.release_date || '', cover_file: null };
                              return <tr key={album.id} className="bg-slate-950">
                                <td className="px-4 py-3"><input className={fieldClass} value={draft.title || ''} onChange={(event) => setAlbumDrafts((current) => ({ ...current, [album.id]: { ...draft, title: event.target.value } }))} /></td>
                                <td className="px-4 py-3"><input type="url" aria-label={t.coverUrl} className={`${fieldClass} mb-2`} value={draft.cover_image_url || ''} onChange={(event) => setAlbumDrafts((current) => ({ ...current, [album.id]: { ...draft, cover_image_url: event.target.value } }))} /><input type="file" accept="image/png,image/jpeg,image/webp" aria-label={t.coverFile} className="block w-full text-xs" onChange={(event) => setAlbumDrafts((current) => ({ ...current, [album.id]: { ...draft, cover_file: event.target.files?.[0] || null } }))} /></td>
                                <td className="px-4 py-3"><input type="date" className={fieldClass} value={draft.release_date || ''} onChange={(event) => setAlbumDrafts((current) => ({ ...current, [album.id]: { ...draft, release_date: event.target.value } }))} /></td>
                                <td className="px-4 py-3"><div className="flex justify-end gap-2">
                                  <button type="button" onClick={() => { setTrackForm({ ...initialTrackForm, album_id: String(album.id) }); setTab('tracks'); setError(''); setNotice(''); }} className={`${buttonClass} bg-[#59604c] text-white hover:bg-[#687057]`}><Plus size={15} />{t.addTrackToAlbum}</button>
                                  <button type="button" disabled={savingKey === `album-${album.id}`} onClick={() => saveAlbum(album.id)} className={`${buttonClass} bg-slate-800 text-white hover:bg-slate-700`}>{t.save}</button>
                                  <button type="button" disabled={savingKey === `album-${album.id}`} onClick={() => deleteAlbum(album)} aria-label={`${t.albums}: ${album.title}`} className={`${buttonClass} bg-red-950 text-red-300 hover:bg-red-900`}><Trash2 size={16} /></button>
                                </div></td>
                              </tr>;
                            })}
                            {!albums.length && <tr><td colSpan="4" className="px-4 py-10 text-center text-slate-400">{t.noAlbums}</td></tr>}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {tab === 'tracks' && (
                  <div className="space-y-6">
                    <form onSubmit={submitTrack} className="grid gap-3 rounded-xl border border-[#41423c] bg-[#252622] p-4 sm:grid-cols-2 lg:grid-cols-3">
                      <label className="text-xs font-semibold text-slate-400">{t.trackName}<input className={`${fieldClass} mt-2`} required value={trackForm.title} onChange={(event) => setTrackForm({ ...trackForm, title: event.target.value })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.artist}<input className={`${fieldClass} mt-2`} required value={trackForm.artist} onChange={(event) => setTrackForm({ ...trackForm, artist: event.target.value })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.selectAlbum}
                        <select className={`${fieldClass} mt-2`} value={trackForm.album_id} onChange={(event) => setTrackForm({ ...trackForm, album_id: event.target.value })}>
                          <option value="">{t.single}</option>{albums.map((album) => <option key={album.id} value={album.id}>{album.title}</option>)}
                        </select>
                      </label>
                      <label className="text-xs font-semibold text-slate-400">{t.price}<input type="number" step="0.01" min="0" required={!trackForm.is_free} disabled={trackForm.is_free} className={`${fieldClass} mt-2`} value={trackForm.is_free ? '0' : trackForm.price} onChange={(event) => setTrackForm({ ...trackForm, price: event.target.value })} /></label>
                      <label className="flex items-center gap-2 self-end rounded-lg border border-slate-700 p-3 text-sm text-slate-300"><input type="checkbox" checked={trackForm.is_free} onChange={(event) => {
                        const isFree = event.target.checked;
                        setTrackForm({
                          ...trackForm,
                          is_free: isFree,
                          category: isFree && trackForm.category === 'edit'
                            ? 'remix'
                            : !isFree && ['simple-pack', 'vst'].includes(trackForm.category)
                              ? 'edit'
                              : trackForm.category,
                        });
                      }} />{t.freeCheckbox}</label>
                      {!trackForm.is_free && <>
                       <label className="text-xs font-semibold text-slate-400 sm:col-span-2">{t.productUrl}<input type="url" required className={`${fieldClass} mt-2`} value={trackForm.gumroad_url} onChange={(event) => setTrackForm({ ...trackForm, gumroad_url: event.target.value })} /></label>
                       <label className="text-xs font-semibold text-slate-400">{t.productId}<input className={`${fieldClass} mt-2`} value={trackForm.gumroad_product_id} onChange={(event) => setTrackForm({ ...trackForm, gumroad_product_id: event.target.value })} /></label>
                      </>}
                      <label className="text-xs font-semibold text-slate-400">{t.trackFile}<input type="file" accept="audio/*" required className="mt-2 block w-full text-sm" onChange={(event) => setTrackForm({ ...trackForm, track_file: event.target.files?.[0] || null })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.previewFile}<input type="file" accept="audio/*" required className="mt-2 block w-full text-sm" onChange={(event) => setTrackForm({ ...trackForm, preview_file: event.target.files?.[0] || null })} /></label>
                      <label className="text-xs font-semibold text-slate-400">{t.albumCover}<input type="file" accept="image/*" className="mt-2 block w-full text-sm" onChange={(event) => setTrackForm({ ...trackForm, cover_file: event.target.files?.[0] || null })} /></label>
                      <div className="sm:col-span-2 lg:col-span-3"><button disabled={savingKey === 'new-track'} className={`${buttonClass} bg-[#59604c] px-5 text-white hover:bg-[#687057]`}>{savingKey === 'new-track' ? t.adding : t.addTrack}</button></div>
                    </form>

                    <div className="overflow-hidden rounded-xl border border-slate-800">
                      <div className="overflow-x-auto">
                        <table className="w-full min-w-[1100px] text-left text-sm">
                          <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400"><tr><th className="px-4 py-4">{t.track}</th><th className="px-4 py-4">{t.albums}</th><th className="px-4 py-4">{t.price}</th><th className="px-4 py-4">Gumroad URL</th><th className="px-4 py-4">{t.productId}</th><th className="px-4 py-4 text-end">{t.operations}</th></tr></thead>
                          <tbody className="divide-y divide-slate-800">
                            {tracks.map((track) => {
                              const draft = trackDrafts[track.id] || {
                                album_id: String(track.album_id || ''),
                                price: String(track.price),
                                gumroad_url: track.gumroad_url || track.external_product_id || '',
                                gumroad_product_id: track.gumroad_product_id || '',
                              };
                              return <tr key={track.id} className="bg-slate-950">
                                <td className="px-4 py-3"><p className="font-semibold text-white">{track.title}</p><p className="text-xs text-slate-400">{track.artist} · {track.is_free ? t.free : t.paid}</p></td>
                                <td className="px-4 py-3"><select className={fieldClass} value={draft.album_id} onChange={(event) => updateTrackDraft(track, 'album_id', event.target.value)}><option value="">{t.single}</option>{albums.map((album) => <option key={album.id} value={album.id}>{album.title}</option>)}</select></td>
                                <td className="px-4 py-3"><input aria-label={`${track.title} ${t.price}`} type="number" step="0.01" min="0" disabled={track.is_free} className="w-24 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-sm text-white disabled:opacity-50" value={track.is_free ? '0' : draft.price} onChange={(event) => updateTrackDraft(track, 'price', event.target.value)} /></td>
                                <td className="px-4 py-3"><input aria-label={`${track.title} Gumroad URL`} className="w-56 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-xs text-white" value={draft.gumroad_url} disabled={track.is_free} onChange={(event) => updateTrackDraft(track, 'gumroad_url', event.target.value)} /></td>
                                <td className="px-4 py-3"><input aria-label={`${track.title} Gumroad ID`} className="w-32 rounded-lg border border-slate-700 bg-slate-900 px-2 py-2 text-xs text-white" value={draft.gumroad_product_id} disabled={track.is_free} onChange={(event) => updateTrackDraft(track, 'gumroad_product_id', event.target.value)} /></td>
                                <td className="px-4 py-3"><div className="flex justify-end gap-2">
                                  <button type="button" disabled={savingKey === `track-${track.id}`} onClick={() => saveTrack(track)} className={`${buttonClass} bg-slate-800 text-white hover:bg-slate-700`}>{t.save}</button>
                                  <button type="button" disabled={savingKey === `track-${track.id}`} onClick={() => deleteTrack(track)} aria-label={`${track.title} ${t.track}`} className={`${buttonClass} bg-red-950 text-red-300 hover:bg-red-900`}><Trash2 size={16} /></button>
                                </div></td>
                              </tr>;
                            })}
                            {!tracks.length && <tr><td colSpan="6" className="px-4 py-10 text-center text-slate-400">{t.noTracks}</td></tr>}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>
                )}

                {tab === 'settings' && (
                  <div className="grid gap-4 md:grid-cols-3">
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><p className="text-sm text-slate-400">{t.users}</p><p className="mt-2 text-3xl font-bold">{users.length}</p></div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><p className="text-sm text-slate-400">{t.albums}</p><p className="mt-2 text-3xl font-bold">{albums.length}</p></div>
                    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5"><p className="text-sm text-slate-400">{t.tracks}</p><p className="mt-2 text-3xl font-bold">{tracks.length}</p></div>
                    <section className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 md:col-span-3">
                      <h3 className="font-semibold">{t.adminAccount}</h3>
                      <p className="mt-2 text-sm text-slate-300">{user?.email}</p>
                      <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400">
                        {t.settingsDescription}
                      </p>
                    </section>
                  </div>
                )}
              </>
            )}
          </div>
        </main>
      </section>
    </div>
  );
};

export default AdminDashboard;
