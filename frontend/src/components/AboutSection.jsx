import React, { useEffect, useState } from 'react';
import { Camera, Music2, ExternalLink } from 'lucide-react';
import api, { resolveAssetUrl } from '../api';
import { useAuth } from '../context/AuthContext';
import { useLanguage } from '../context/LanguageContext';
import { getApiErrorMessage } from '../utils/errors';

const SOCIAL_LINKS = [

  {
    label: 'Spotify',
    href: 'https://open.spotify.com/intl-ar/artist/2ahpkP0xfNEH9PBREdhI79',
    color: 'hover:text-green-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z" />
      </svg>
    ),
  },
  {
    label: 'Anghami',
    href: 'https://play.anghami.com/artist/1491788',
    color: 'hover:text-yellow-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 2a10 10 0 100 20 10 10 0 000-20zm3.5 10.5a3.5 3.5 0 11-7 0 3.5 3.5 0 017 0z" />
      </svg>
    ),
  },

  {
    label: 'Instagram',
    href: 'https://www.instagram.com/djbilalhamsho',
    color: 'hover:text-pink-400',
    icon: (
      <svg viewBox="0 0 24 24" fill="currentColor" className="w-6 h-6">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
      </svg>
    ),
  },
  {
    label: 'YouTube',
    href: 'https://youtube.com/@djbilalhamshoo',
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
  const { user } = useAuth();
  const [profilePhotoUrl, setProfilePhotoUrl] = useState(null);
  const [photoError, setPhotoError] = useState(null);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    let isMounted = true;
    api.get('/profile/photo')
      .then(({ data }) => {
        if (isMounted) setProfilePhotoUrl(data.image_url);
      })
      .catch((error) => {
        console.error('Could not load profile photo:', error);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  const handlePhotoChange = async (event) => {
    const photo = event.target.files?.[0];
    if (!photo) return;

    const formData = new FormData();
    formData.append('photo', photo);
    setUploadingPhoto(true);
    setPhotoError(null);
    try {
      const response = await api.post('/profile/photo', formData);
      setProfilePhotoUrl(response.data.image_url);
    } catch (error) {
      setPhotoError(getApiErrorMessage(error, 'Could not upload profile photo'));
    } finally {
      setUploadingPhoto(false);
      event.target.value = '';
    }
  };

  const t = {
    role: lang === 'ar' ? 'منتج · ميكس وماستر · صانع إيقاعات' : 'Producer · Mixing & Mastering · Beat Maker',
    tagline: lang === 'ar'
      ? '🎚️ تراكات مرخصة · حلول مخصصة للميكس والماستر · إيقاعات خالية من حقوق الملكية'
      : '🎚️ Licensed instrumentals · Custom mixing/mastering solutions · Royalty-free beats',
    bio: lang === 'ar'
      ? `DJ Bilal Hamsho (دي جي بلال حمشو) هو دي جي ومنتج موسيقي سوري يتمتع بخبرة تتجاوز 20 عاماً في مجال الـDJ والـMusic Production، ويُعد من الأسماء البارزة في مجال الموسيقى الإلكترونية والـDJing في سوريا.

يتميز بلال حمشو بأسلوبه الخاص في تقديم الـRemixes والـMashups والـMixes، مع تركيز على دمج الموسيقى الشرقية والعربية مع أنماط الموسيقى الإلكترونية الحديثة، وخاصة Afro House وHouse وEDM، إلى جانب الموسيقى العربية والمهرجانات والدبكات السورية واللبنانية.

حقق DJ Bilal Hamsho مئات الملايين من المشاهدات والاستماعات عبر مختلف المنصات الرقمية، ويمتلك حضوراً واسعاً على منصات التواصل الاجتماعي والمنصات الموسيقية العالمية، حيث تتوفر أعماله وMixes الخاصة به عبر YouTube وSpotify وAnghami وApple Music وSoundCloud وغيرها.

ويُعد بلال حمشو أول DJ سوري يحصل على الدرع الفضي من YouTube (Silver Creator Award)، كإنجاز يعكس حجم حضوره وانتشاره على المنصة.

ولا يقتصر نشاط بلال حمشو على الأداء والإنتاج الموسيقي، بل يعمل أيضاً في مجال التعليم والتدريب الموسيقي، حيث يقدم دورات متخصصة في تعليم الـDJ والـMixing، بالإضافة إلى دورات Music Production وتعليم صناعة وإنتاج الموسيقى، مع تدريب عملي على تقنيات الـMixing والـMastering وبرامج الإنتاج الموسيقي.

كما يمتد نشاطه إلى الحفلات والأعراس والمناسبات الخاصة، حيث يقدم عروضاً موسيقية تجمع بين الخبرة الطويلة في مجال الـDJ والأفكار الحديثة في الإنتاج والأداء، مع القدرة على التعامل مع مختلف أنواع الجمهور والمناسبات.

DJ Bilal Hamsho هو مشروع موسيقي متكامل يجمع بين DJing، Music Production، Remixing، Performance والتعليم الموسيقي، بخبرة تتجاوز عقدين من الزمن وحضور رقمي واسع، مع توجه مستمر نحو تطوير الموسيقى العربية وتقديمها بأسلوب إلكتروني عصري.`
      : 'Hi! I am DJ Bilal — a production artist with years of experience across live stages and studio sessions. I create professional beats and instrumentals across a wide range of styles, from electronic music to hip-hop. Every track is carefully mixed and mastered to deliver top-level quality. Whether you want a ready-to-use beat or a custom offer for your project, you are in the right place.',
    howWorks: lang === 'ar' ? 'طريقة الشراء' : 'How purchase works',
    howWorksDesc: lang === 'ar'
      ? 'اختر التراك، أكمل الدفع عبر Gumroad، ثم نزّل الملف المرخّص مباشرة.'
      : 'Choose a track, complete payment via Gumroad, and instantly download your licensed audio file.',
    contact: lang === 'ar' ? 'التواصل' : 'Contact',
    years: lang === 'ar' ? 'سنوات الخبرة' : 'Years of Experience',
    released: lang === 'ar' ? 'إصدارات الإيقاعات' : 'Released Beats',
    clients: lang === 'ar' ? 'عملاء سعداء' : 'Happy Clients',
    follow: lang === 'ar' ? 'تابعني' : 'Follow Me',
  };
  return (
    <section className="max-w-4xl mx-auto">
      <div className="overflow-hidden rounded-3xl border border-[#e4e0d8] bg-white shadow-sm">
        {/* Hero banner */}
        <div className="h-32 bg-[#e8f3f0] sm:h-36" />

        <div className="px-4 sm:px-8 pb-8 sm:pb-10">
          {/* Avatar */}
          <div className="flex flex-col gap-4 -mt-14 mb-6 sm:-mt-16 sm:flex-row sm:items-end sm:gap-6">
            <div className="relative h-28 w-28 flex-shrink-0 overflow-hidden rounded-2xl border-4 border-white bg-[#ed7755] shadow-md sm:h-36 sm:w-36">
              {profilePhotoUrl ? (
                <img src={resolveAssetUrl(profilePhotoUrl)} alt="DJ Bilal" className="w-full h-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center">
                  <Music2 className="h-10 w-10 text-white" aria-hidden="true" />
                </div>
              )}
              {user?.is_admin && (
                <label
                  title={lang === 'ar' ? 'تغيير الصورة' : 'Change profile photo'}
                  className="absolute bottom-1 right-1 cursor-pointer rounded-full bg-[#222831]/90 p-2 text-white shadow hover:bg-[#39414b]"
                >
                  <Camera size={16} />
                  <input
                    type="file"
                    accept="image/png,image/jpeg,image/webp"
                    onChange={handlePhotoChange}
                    disabled={uploadingPhoto}
                    className="sr-only"
                    aria-label={lang === 'ar' ? 'تغيير الصورة' : 'Change profile photo'}
                  />
                </label>
              )}
            </div>
            <div className="pb-1 sm:pb-2">
              <h2 className="text-2xl font-extrabold text-[#222831] sm:text-3xl">DJ Bilal</h2>
              <p className="text-sm font-medium text-[#c65a3d]">{t.role}</p>
            </div>
            {photoError && (
              <p role="alert" className="mb-4 text-sm text-red-700">{photoError}</p>
            )}
          </div>

          {/* Tagline */}
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#f0c2b2] bg-[#fff0e9] px-3 py-2 text-xs font-semibold text-[#b94c31] sm:px-4 sm:text-sm">
            {t.tagline}
          </div>

          {/* Bio */}
          <p className="mb-8 max-w-2xl text-base leading-relaxed text-[#4f5861]">
            {t.bio}
          </p>

          <div className="mb-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-[#e4e0d8] bg-[#fbfaf7] p-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-[#303740]">{t.howWorks}</h3>
              <p className="mt-2 text-sm text-[#626a72]">
                {t.howWorksDesc}
              </p>
            </div>
            <div className="rounded-xl border border-[#e4e0d8] bg-[#fbfaf7] p-4">
              <h3 className="text-sm font-bold uppercase tracking-wide text-[#303740]">{t.contact}</h3>
              <p className="mt-2 text-sm text-[#626a72]">
                Support e-mail: <strong>gbilal1717@gmail.com</strong>
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
              <div key={stat.label} className="rounded-xl border border-[#e4e0d8] bg-white p-4 text-center shadow-sm">
                <div className="text-2xl font-extrabold text-[#c65a3d]">{stat.value}</div>
                <div className="mt-1 text-xs text-[#727981]">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Social links */}
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-[#7b8289]">{t.follow}</p>
            <div className="flex items-center gap-4 flex-wrap">
              {SOCIAL_LINKS.map((link) => (
                <a
                  key={link.label}
                  href={link.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`flex items-center gap-2 rounded-xl border border-[#dedbd4] bg-white px-4 py-2.5 text-[#4f5861] shadow-sm transition-all duration-200 hover:border-[#ed7755] hover:bg-[#fffaf6] ${link.color}`}
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
