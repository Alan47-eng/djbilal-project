import React from 'react';
import {
  Gift,
  Library,
  LogIn,
  LogOut,
  UserPlus,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import AdminDashboard from './AdminDashboard';

const AdminDrawer = ({ isOpen, onClose, activeTab, onNavigate, onOpenAuth, onLogout }) => {
  const { user } = useAuth();

  if (!isOpen) return null;

  if (user?.is_admin) {
    return (
      <AdminDashboard
        onClose={onClose}
        onNavigate={onNavigate}
        onLogout={onLogout}
      />
    );
  }

  const menuItems = [
    { id: 'albums', label: 'Albums', icon: <Library size={16} /> },
    { id: 'free', label: 'Free', icon: <Gift size={16} /> },
    ...(user ? [{ id: 'library', label: 'My Library', icon: <Library size={16} /> }] : []),
  ];

  return (
    <div className="fixed inset-0 z-50 bg-black/60" onClick={onClose}>
      <aside
        className="absolute left-0 top-0 flex h-full w-full max-w-sm flex-col border-r border-violet-300/10 bg-gradient-to-b from-[#292635] via-[#20212b] to-[#191a23] text-slate-100 shadow-2xl shadow-black/40"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">Menu</h2>
            <p className="text-sm text-slate-400">{user ? user.email : 'DJ Bilal Music Store'}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close menu" className="rounded-full p-2 hover:bg-slate-800">
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
                    ? 'border-violet-500 bg-violet-500/15 text-violet-200'
                    : 'border-[#41464b] bg-[#292d31] text-slate-200 hover:bg-[#363b40]'
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {!user ? (
          <div className="space-y-2 border-b border-slate-800 px-5 py-4">
            <button
              type="button"
              onClick={() => onOpenAuth?.('login')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#383c40] px-4 py-2.5 font-semibold text-white hover:bg-[#484d52]"
            >
              <LogIn size={16} />
              Sign In
            </button>
            <button
              type="button"
              onClick={() => onOpenAuth?.('register')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 font-semibold text-white hover:bg-violet-700"
            >
              <UserPlus size={16} />
              Sign Up
            </button>
          </div>
        ) : (
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

        <div className="px-5 py-4 text-sm text-slate-400">
          Quickly browse albums and free tracks from here.
        </div>
      </aside>
    </div>
  );
};

export default AdminDrawer;
