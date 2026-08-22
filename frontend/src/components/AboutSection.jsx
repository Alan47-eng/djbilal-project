import React from 'react';
import { Music2, ExternalLink } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';

const SOCIAL_LINKS = [
  {
    label: 'SoundCloud',
    href: 'https://soundcloud.com/djbilal',
    color: 'hover:text-orange-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M1.175 12.225c-.051 0-.094.046-.101.1l-.233 2.154.233 2.105c.007.058.05.098.101.098.05 0 .09-.04.099-.098l.255-2.105-.27-2.154c-.009-.06-.05-.1-.099-.1zm-.899.828c-.06 0-.091.037-.104.094L0 15.354l.172 2.154c.013.06.045.097.104.097.056 0 .09-.038.105-.097l.195-2.154-.195-2.207c-.015-.057-.05-.094-.106-.094zm1.81-.7c-.063 0-.11.05-.118.115l-.217 2.826.217 2.779c.008.066.055.114.118.114s.11-.048.12-.114l.247-2.779-.247-2.826c-.01-.065-.057-.115-.12-.115zm.908-.145c-.073 0-.128.057-.136.13l-.2 2.971.2 2.85c.008.075.063.13.136.13.072 0 .127-.055.136-.13l.227-2.85-.227-2.971c-.009-.073-.064-.13-.136-.13zm.91-.12c-.082 0-.145.065-.152.147l-.184 3.091.184 2.923c.007.082.07.148.152.148s.145-.066.153-.148l.21-2.923-.21-3.091c-.008-.082-.071-.147-.153-.147zm.908-.052c-.09 0-.16.072-.167.163l-.168 3.143.168 2.996c.007.09.077.163.167.163.09 0 .16-.073.168-.163l.19-2.996-.19-3.143c-.008-.091-.078-.163-.168-.163zm.91-.016c-.1 0-.178.08-.185.18l-.15 3.159.15 3.068c.007.1.085.18.185.18.1 0 .178-.08.186-.18l.172-3.068-.172-3.159c-.008-.1-.086-.18-.186-.18zm4.555-1.646c-.184 0-.36.035-.523.097C9.694 8.2 8.617 7.2 7.275 7.2c-.414 0-.81.102-1.154.28-.13.064-.165.13-.167.19v8.237c.002.07.055.127.124.136h7.04c.07-.008.126-.064.126-.136v-5.71c0-.905-.735-1.64-1.64-1.64zm3.638 2.38c-.19-.06-.388-.092-.593-.092-1.035 0-1.89.84-1.907 1.876 0 .023-.002.044-.002.065v3.472c0 .07.055.127.124.136h4.43c.07-.008.126-.065.126-.136V12.37c0-1.177-.953-2.13-2.13-2.13-.026 0-.05.002-.076.003z" />
      </svg>
    ),
  },
  {
    label: 'Spotify',
    href: 'https://open.spotify.com/artist/djbilal',
    color: 'hover:text-green-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    ),
  },
  {
    label: 'Instagram',
    href: 'https://instagram.com/djbilal',
    color: 'hover:text-pink-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    ),
  },
  {
    label: 'YouTube',
    href: 'https://youtube.com/@djbilal',
    color: 'hover:text-red-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M23.495 6.205a3.007 3.007 0 0 0-2.088-2.088c-1.87-.501-9.396-.501-9.396-.501s-7.507-.01-9.396.501A3.007 3.007 0 0 0 .527 6.205a31.247 31.247 0 0 0-.522 5.805 31.247 31.247 0 0 0 .522 5.783 3.007 3.007 0 0 0 2.088 2.088c1.868.502 9.396.502 9.396.502s7.506 0 9.396-.502a3.007 3.007 0 0 0 2.088-2.088 31.247 31.247 0 0 0 .5-5.783 31.247 31.247 0 0 0-.5-5.805zM9.609 15.601V8.408l6.264 3.602z" />
      </svg>
    ),
  },
];

const AboutSection = () => {
  const { lang } = useLanguage();
  const t = {
    role: lang === 'ar' ? 'منتج · ميكس وماستر · صانع إيقاعات' : 'Producer · Mixing & Mastering · Beat Maker',
    tagline: lang === 'ar'
      ? '🎚️ تراكات مرخصة · حلول مخصصة للميكس والماستر · إيقاعات خالية من حقوق الملكية'
      : '🎚️ Licensed instrumentals · Custom mixing/mastering solutions · Royalty-free beats',
    bio: lang === 'ar'
      ? 'مرحباً! أنا DJ Bilal، منتج موسيقي بخبرة سنوات في العروض الحية والاستوديو. أقدم إيقاعات وتوزيعات احترافية بأنماط متعددة مع ميكس وماستر عالي الجودة.'
      : 'Hi! I am DJ Bilal — a production artist with years of experience across live stages and studio sessions. I create professional beats and instrumentals across a wide range of styles, from electronic music to hip-hop. Every track is carefully mixed and mastered to deliver top-level quality. Whether you want a ready-to-use beat or a custom offer for your project, you are in the right place.',
    howWorks: lang === 'ar' ? 'طريقة الشراء' : 'How purchase works',
    howWorksDesc: lang === 'ar'
      ? 'اختر التراك، أكمل الدفع عبر Lemon Squeezy، ثم نزّل الملف المرخّص مباشرة.'
      : 'Choose a track, complete payment via Lemon Squeezy, and instantly download your licensed audio file.',
    contact: lang === 'ar' ? 'التواصل' : 'Contact',
    years: lang === 'ar' ? 'سنوات الخبرة' : 'Years of Experience',
    released: lang === 'ar' ? 'إصدارات الإيقاعات' : 'Released Beats',
    clients: lang === 'ar' ? 'عملاء سعداء' : 'Happy Clients',
    follow: lang === 'ar' ? 'تابعني' : 'Follow Me',
  };
  return (
    <section className="max-w-4xl mx-auto">
      <div className="rounded-3xl border border-slate-700 bg-gradient-to-br from-slate-800 to-slate-900 overflow-hidden shadow-2xl">
        {/* Hero banner */}
        <div className="h-40 bg-gradient-to-r from-purple-900 via-blue-900 to-slate-900 relative">
          <div className="absolute inset-0 opacity-20"
            style={{ backgroundImage: 'repeating-linear-gradient(45deg, #7c3aed 0, #7c3aed 1px, transparent 0, transparent 50%)', backgroundSize: '20px 20px' }}
          />
        </div>

        <div className="px-4 sm:px-8 pb-8 sm:pb-10">
          {/* Avatar */}
          <div className="flex flex-col sm:flex-row sm:items-end gap-4 sm:gap-6 -mt-12 sm:-mt-14 mb-6">
            <div className="w-20 h-20 sm:w-28 sm:h-28 rounded-2xl border-4 border-slate-800 bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-xl flex-shrink-0">
              <Music2 size={48} className="text-white" />
            </div>
            <div className="pb-1 sm:pb-2">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-white">DJ Bilal</h2>
              <p className="text-purple-400 font-medium text-sm">{t.role}</p>
            </div>
          </div>

          {/* Tagline */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-purple-500/40 bg-purple-600/10 px-3 sm:px-4 py-2 text-xs sm:text-sm font-semibold text-purple-300">
            {t.tagline}
          </div>

          {/* Bio */}
          <p className="text-slate-300 leading-relaxed text-base mb-8 max-w-2xl">
            {t.bio}
          </p>

          <div className="mb-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-200">{t.howWorks}</h3>
              <p className="mt-2 text-sm text-slate-300">
                {t.howWorksDesc}
              </p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-800 p-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-slate-200">{t.contact}</h3>
              <p className="mt-2 text-sm text-slate-300">
                Support e-mail: <strong>support@djbilal.com</strong>
              </p>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
            {[
              { label: t.years, value: '10+' },
              { label: t.released, value: '200+' },
              { label: t.clients, value: '500+' },
            ].map((stat) => (
              <div key={stat.label} className="rounded-xl bg-slate-800 p-4 text-center border border-slate-700">
                <div className="text-2xl font-extrabold text-purple-400">{stat.value}</div>
                <div className="text-xs text-slate-400 mt-1">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Social links */}
          <div>
            <p className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-3">{t.follow}</p>
            <div className="flex items-center gap-4 flex-wrap">
              {SOCIAL_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-slate-300 transition-all duration-200 hover:border-slate-500 hover:bg-slate-700 ${link.color}`}
                >
                  {link.icon}
                  <span className="text-sm font-medium">{link.label}</span>
                  <ExternalLink size={12} className="opacity-50" />
                </a>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default AboutSection;
