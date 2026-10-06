import api, { resolveAssetUrl } from '../api';

const buildDownloadName = (title, artist, sourceUrl) => {
  const parsed = new URL(sourceUrl, window.location.origin);
  const extension = parsed.pathname.match(/\.([a-zA-Z0-9]+)$/)?.[1]?.toLowerCase() || 'mp3';
  return `${title} - ${artist}.${extension}`;
};

export async function downloadTrackFile(track) {
  const fileRoute = track.isFree
    ? `/tracks/${track.id}/free-download-file`
    : `/tracks/${track.id}/download-file`;
  const urlRoute = track.isFree
    ? `/tracks/${track.id}/free-download`
    : `/tracks/${track.id}/download`;
  const response = await api.get(urlRoute);
  const downloadUrl = response.data.download_url;

  if (!downloadUrl.startsWith('/media/')) {
    window.location.assign(resolveAssetUrl(downloadUrl));
    return;
  }

  const fileResponse = await api.get(fileRoute, { responseType: 'blob' });
  const contentType = fileResponse.headers?.['content-type'] || '';
  if (contentType.includes('text/html')) {
    throw new Error('Received HTML instead of media file');
  }

  const blobUrl = window.URL.createObjectURL(fileResponse.data);
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = buildDownloadName(track.title, track.artist, downloadUrl);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(blobUrl);
}
