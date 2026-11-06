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
        className="absolute left-0 top-0 flex h-full w-full max-w-sm flex-col border-r border-[#e4e0d8] bg-white text-[#222831] shadow-2xl"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[#e8e4dc] px-5 py-4">
          <div>
            <h2 className="text-xl font-bold">Menu</h2>
            <p className="text-sm text-[#727981]">{user ? user.email : 'DJ Bilal Music Store'}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close menu" className="rounded-full p-2 text-[#626a72] hover:bg-[#f1eee8]">
            <X size={18} />
          </button>
        </div>

        <div className="space-y-3 border-b border-[#e8e4dc] px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#7b8289]">Site Menu</p>
          <div className="grid grid-cols-2 gap-2">
            {menuItems.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onNavigate?.(item.id)}
                className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                  activeTab === item.id
                    ? 'border-[#ed7755] bg-[#fff0e9] text-[#b94c31]'
                    : 'border-[#dedbd4] bg-white text-[#4f5861] hover:bg-[#f4f1eb]'
                }`}
              >
                {item.icon}
                {item.label}
              </button>
            ))}
          </div>
        </div>

        {!user ? (
          <div className="space-y-2 border-b border-[#e8e4dc] px-5 py-4">
            <button
              type="button"
              onClick={() => onOpenAuth?.('login')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-[#dedbd4] bg-white px-4 py-2.5 font-semibold text-[#303740] hover:bg-[#f4f1eb]"
            >
              <LogIn size={16} />
              Sign In
            </button>
            <button
              type="button"
              onClick={() => onOpenAuth?.('register')}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#ed7755] px-4 py-2.5 font-semibold text-white hover:bg-[#d96343]"
            >
              <UserPlus size={16} />
              Sign Up
            </button>
          </div>
        ) : (
          <div className="space-y-2 border-b border-[#e8e4dc] px-5 py-4">
          <p className="text-xs font-semibold uppercase tracking-widest text-[#7b8289]">Account</p>
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

          <div className="px-5 py-4 text-sm text-[#727981]">
          Quickly browse albums and free tracks from here.
        </div>
      </aside>
    </div>
  );
};

export default AdminDrawer;
