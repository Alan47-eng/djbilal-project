import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, ShoppingCart, Trash2, X } from 'lucide-react';
import { useLanguage } from '../context/LanguageContext';
import { getApiErrorMessage } from '../utils/errors';

export default function ShopierCheckoutModal({
  isOpen,
  tracks,
  busy,
  onClose,
  onRemoveTrack,
  onCheckout,
}) {
  const { lang } = useLanguage();
  const isArabic = lang === 'ar';
  const [error, setError] = useState('');
  const [checkoutForm, setCheckoutForm] = useState(null);
  const paymentFormRef = useRef(null);

  const text = {
    title: isArabic ? 'سلة التسوق' : 'Your cart',
    empty: isArabic ? 'سلتك فارغة.' : 'Your cart is empty.',
    total: isArabic ? 'الإجمالي' : 'Total',
    checkout: isArabic ? 'ادفع عبر Shopier' : 'Pay with Shopier',
    working: isArabic ? 'جارٍ التحضير...' : 'Preparing checkout...',
    close: isArabic ? 'إغلاق' : 'Close',
    secureNote: isArabic
      ? 'سيتم إرسال بيانات الطلب إلى Shopier لإتمام الدفع.'
      : 'Order details will be sent to Shopier to complete payment.',
    currency: 'USD',
  };

  useEffect(() => {
    if (checkoutForm && paymentFormRef.current) {
      paymentFormRef.current.submit();
      setCheckoutForm(null);
    }
  }, [checkoutForm]);

  const total = useMemo(
    () => tracks.reduce((sum, track) => sum + Number(track.price || 0), 0),
    [tracks],
  );

  if (!isOpen) return null;

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    const payload = {
      track_ids: tracks.map((track) => track.id),
      current_language: lang === 'ar' ? 'en' : lang,
    };

    try {
      const result = await onCheckout(payload);
      setCheckoutForm(result);
    } catch (checkoutError) {
      setError(getApiErrorMessage(checkoutError, 'Could not start Shopier checkout.'));
    }
  };

  return (
    <>
      <div className="fixed inset-0 z-[70] flex items-end justify-center bg-black/70 p-0 backdrop-blur-sm sm:items-center sm:p-4">
        <section
          role="dialog"
          aria-modal="true"
          aria-labelledby="shopier-cart-title"
          className="max-h-[94vh] w-full max-w-xl overflow-y-auto rounded-t-2xl border border-white/10 bg-[#18181e] p-4 shadow-2xl sm:rounded-2xl sm:p-6"
          dir={isArabic ? 'rtl' : 'ltr'}
        >
          <div className="mb-5 flex items-center justify-between gap-3">
            <h2 id="shopier-cart-title" className="flex items-center gap-2 text-xl font-bold text-white">
              <ShoppingCart size={21} /> {text.title}
            </h2>
            <button type="button" onClick={onClose} aria-label={text.close} className="rounded-lg p-2 text-slate-300 hover:bg-white/10 hover:text-white">
              <X size={20} />
            </button>
          </div>

          {tracks.length === 0 ? (
            <p className="rounded-xl bg-white/[0.04] p-5 text-center text-slate-300">{text.empty}</p>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                {tracks.map((track) => (
                  <div key={track.id} className="flex items-center justify-between gap-3 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-white">{track.title}</p>
                      <p className="truncate text-xs text-slate-400">{track.artist}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-3">
                      <span className="text-sm font-semibold text-violet-200">${Number(track.price).toFixed(2)}</span>
                      <button type="button" onClick={() => onRemoveTrack(track.id)} aria-label={`Remove ${track.title}`} className="rounded-lg p-2 text-slate-400 hover:bg-red-500/10 hover:text-red-300">
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
                <div className="flex justify-between border-t border-white/10 pt-3 text-base font-bold text-white">
                  <span>{text.total}</span>
                  <span>${total.toFixed(2)} {text.currency}</span>
                </div>
                <p className="text-xs text-slate-500">{text.secureNote}</p>
              </div>

              {error && <p role="alert" className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">{error}</p>}
              <div className="flex flex-col-reverse gap-2 border-t border-white/10 pt-4 sm:flex-row sm:justify-end">
                <button type="button" onClick={onClose} className="rounded-lg border border-white/10 px-4 py-2.5 text-sm font-semibold text-slate-300 hover:bg-white/[0.06]">{text.close}</button>
                <button type="submit" disabled={busy || tracks.length === 0} className="inline-flex items-center justify-center gap-2 rounded-lg bg-violet-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-60">
                  {busy ? <Loader2 size={16} className="animate-spin" /> : <ShoppingCart size={16} />}
                  {busy ? text.working : text.checkout}
                </button>
              </div>
            </form>
          )}
        </section>
      </div>

      {checkoutForm && (
        <form ref={paymentFormRef} action={checkoutForm.action_url} method={checkoutForm.method} className="hidden" aria-hidden="true">
          {Object.entries(checkoutForm.fields).map(([name, value]) => (
            <input key={name} type="hidden" name={name} value={value} />
          ))}
        </form>
      )}
    </>
  );
}
