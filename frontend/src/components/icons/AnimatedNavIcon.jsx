/**
 * Ikon navigasi & aksi PNL OBE dengan varian duotone fill + scale ringan.
 * Mendukung permukaan terang (default) dan gelap (`surface="dark"`).
 */
export default function AnimatedNavIcon({
  name = 'dashboard',
  active = false,
  surface = 'light',
  size = 18,
  className = '',
}) {
  return (
    <span
      className={`obe-nav-icon shrink-0 ${className}`.trim()}
      data-active={active ? 'true' : 'false'}
      data-surface={surface}
      aria-hidden="true"
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        {renderIconGlyph(name)}
      </svg>
    </span>
  );
}

function renderIconGlyph(name) {
  switch (name) {
    case 'dashboard':
      return (
        <>
          <rect className="obe-duotone-fill" x="3" y="3" width="7.5" height="8.5" rx="2" />
          <rect x="3" y="3" width="7.5" height="8.5" rx="2" />
          <rect x="13.5" y="3" width="7.5" height="5.5" rx="2" />
          <rect className="obe-duotone-fill" x="13.5" y="11.5" width="7.5" height="9.5" rx="2" />
          <rect x="13.5" y="11.5" width="7.5" height="9.5" rx="2" />
          <rect x="3" y="14.5" width="7.5" height="6.5" rx="2" />
        </>
      );

    case 'kurikulum':
      return (
        <>
          <polygon className="obe-duotone-fill" points="12 3 21 7.5 12 12 3 7.5 12 3" />
          <polygon points="12 3 21 7.5 12 12 3 7.5 12 3" />
          <polyline points="3 12 12 16.5 21 12" />
          <polyline points="3 16.5 12 21 21 16.5" />
        </>
      );

    case 'profil-lulusan':
      return (
        <>
          <polygon className="obe-duotone-fill" points="12 4 21 8.5 12 13 3 8.5 12 4" />
          <polygon points="12 4 21 8.5 12 13 3 8.5 12 4" />
          <path d="M6.5 10.6v4.6c0 1.7 2.5 3.3 5.5 3.3s5.5-1.6 5.5-3.3v-4.6" />
          <line x1="20" y1="9" x2="20" y2="15" />
        </>
      );

    case 'cpl':
      return (
        <>
          <circle className="obe-duotone-fill" cx="12" cy="9.5" r="6" />
          <circle cx="12" cy="9.5" r="6" />
          <polyline points="9.2 14.8 8 21 12 18.8 16 21 14.8 14.8" />
          <polyline points="9.5 9.6 11.2 11.3 14.6 7.9" />
        </>
      );

    case 'mata-kuliah':
      return (
        <>
          <path
            className="obe-duotone-fill"
            d="M4 5.5A2.5 2.5 0 0 1 6.5 3H12v16.5H6.5A2.5 2.5 0 0 0 4 21V5.5Z"
          />
          <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H12v16.5H6.5A2.5 2.5 0 0 0 4 21V5.5Z" />
          <path d="M20 5.5A2.5 2.5 0 0 0 17.5 3H12v16.5h5.5A2.5 2.5 0 0 1 20 21V5.5Z" />
        </>
      );

    case 'matriks':
      return (
        <>
          <rect className="obe-duotone-fill" x="3.5" y="3.5" width="17" height="5" rx="1.5" />
          <rect x="3.5" y="3.5" width="17" height="17" rx="2.5" />
          <line x1="3.5" y1="9" x2="20.5" y2="9" />
          <line x1="3.5" y1="14.5" x2="20.5" y2="14.5" />
          <line x1="9.5" y1="3.5" x2="9.5" y2="20.5" />
          <line x1="15" y1="3.5" x2="15" y2="20.5" />
        </>
      );

    case 'periode':
      return (
        <>
          <rect className="obe-duotone-fill" x="3.5" y="5" width="17" height="5" rx="1.5" />
          <rect x="3.5" y="5" width="17" height="15.5" rx="2.5" />
          <line x1="8" y1="3" x2="8" y2="6.5" />
          <line x1="16" y1="3" x2="16" y2="6.5" />
          <line x1="3.5" y1="10" x2="20.5" y2="10" />
          <circle cx="8.5" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
          <circle cx="12" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
          <circle cx="15.5" cy="14.5" r="0.9" fill="currentColor" stroke="none" />
        </>
      );

    case 'roster':
      return (
        <>
          <circle className="obe-duotone-fill" cx="9.5" cy="8" r="3.5" />
          <circle cx="9.5" cy="8" r="3.5" />
          <path d="M3.5 19.5c0-3.1 2.7-5 6-5s6 1.9 6 5" />
          <path d="M16.2 8.2a2.8 2.8 0 0 1 0 5.4" />
          <path d="M17.8 14.9c1.9.6 3.2 2 3.2 4.6" />
        </>
      );

    case 'paket':
      /* Library-style books on shelf (bukan ikon kardus/package box) */
      return (
        <>
          <rect className="obe-duotone-fill" x="4" y="5" width="4" height="15" rx="1" />
          <rect className="obe-duotone-fill" x="10" y="7" width="4" height="13" rx="1" />
          <rect x="4" y="5" width="4" height="15" rx="1" />
          <rect x="10" y="7" width="4" height="13" rx="1" />
          <path d="M16 6.2l3.8 1-2.5 12.6-3.8-1L16 6.2Z" />
          <line x1="2.5" y1="20.5" x2="21.5" y2="20.5" />
        </>
      );

    case 'laporan':
      return (
        <>
          <path
            className="obe-duotone-fill"
            d="M6 3.5h8.2L18.5 7.8V20a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 20V5A1.5 1.5 0 0 1 6 3.5Z"
          />
          <path d="M6 3.5h8.2L18.5 7.8V20a1.5 1.5 0 0 1-1.5 1.5H6A1.5 1.5 0 0 1 4.5 20V5A1.5 1.5 0 0 1 6 3.5Z" />
          <polyline points="14 3.5 14 8 18.5 8" />
          <line x1="8.5" y1="16.8" x2="8.5" y2="14" />
          <line x1="11.5" y1="16.8" x2="11.5" y2="11.8" />
          <line x1="14.5" y1="16.8" x2="14.5" y2="13.2" />
        </>
      );

    case 'rancangan':
      return (
        <>
          <rect className="obe-duotone-fill" x="5" y="4.5" width="14" height="16.5" rx="2" />
          <rect x="5" y="4.5" width="14" height="16.5" rx="2" />
          <rect x="9" y="2.5" width="6" height="3.5" rx="1" />
          <line x1="8.5" y1="10" x2="15.5" y2="10" />
          <line x1="8.5" y1="13.8" x2="15.5" y2="13.8" />
          <line x1="8.5" y1="17.5" x2="12.5" y2="17.5" />
        </>
      );

    case 'nilai':
      return (
        <>
          <path
            className="obe-duotone-fill"
            d="M15.8 4.2a2.1 2.1 0 0 1 3 3L8.5 17.5 4.5 18.5l1-4L15.8 4.2Z"
          />
          <path d="M15.8 4.2a2.1 2.1 0 0 1 3 3L8.5 17.5 4.5 18.5l1-4L15.8 4.2Z" />
          <line x1="13.5" y1="6.5" x2="16.5" y2="9.5" />
          <line x1="4.5" y1="21" x2="19.5" y2="21" />
        </>
      );

    case 'capaian':
      return (
        <>
          <polygon
            className="obe-duotone-fill"
            points="12 3 20 7.6 20 16.4 12 21 4 16.4 4 7.6 12 3"
          />
          <polygon points="12 3 20 7.6 20 16.4 12 21 4 16.4 4 7.6 12 3" />
          <polygon points="12 7.5 16.2 10 16.2 14.5 12 16.8 7.8 14.5 7.8 10 12 7.5" />
        </>
      );

    case 'rincian':
      return (
        <>
          <rect className="obe-duotone-fill" x="4" y="4" width="16" height="16" rx="2.5" />
          <rect x="4" y="4" width="16" height="16" rx="2.5" />
          <polyline points="7.5 9.5 8.8 10.8 11 8.5" />
          <line x1="13" y1="9.8" x2="16.8" y2="9.8" />
          <polyline points="7.5 14.5 8.8 15.8 11 13.5" />
          <line x1="13" y1="14.8" x2="16.8" y2="14.8" />
        </>
      );

    case 'logout':
      return (
        <>
          <path className="obe-duotone-fill" d="M4.5 5.5A2 2 0 0 1 6.5 3.5H11v17H6.5a2 2 0 0 1-2-2v-13Z" />
          <path d="M11 3.5H6.5a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2H11" />
          <polyline points="15.5 8.5 19.5 12 15.5 15.5" />
          <line x1="9.5" y1="12" x2="19.5" y2="12" />
        </>
      );

    case 'download':
      return (
        <>
          <rect className="obe-duotone-fill" x="4.5" y="15" width="15" height="5" rx="1.5" />
          <path d="M4.5 15.5v2.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-2.5" />
          <polyline points="8.5 10.5 12 14 15.5 10.5" />
          <line x1="12" y1="4" x2="12" y2="14" />
        </>
      );

    case 'lock':
      return (
        <>
          <rect className="obe-duotone-fill" x="5" y="10.5" width="14" height="9.5" rx="2.5" />
          <rect x="5" y="10.5" width="14" height="9.5" rx="2.5" />
          <path d="M8 10.5V7.8a4 4 0 0 1 8 0v2.7" />
          <circle cx="12" cy="15.2" r="1" fill="currentColor" stroke="none" />
        </>
      );

    case 'audit':
      return (
        <>
          <path
            className="obe-duotone-fill"
            d="M12 3.2 19 6v5.7c0 4.5-3 8.1-7 9.3-4-1.2-7-4.8-7-9.3V6l7-2.8Z"
          />
          <path d="M12 3.2 19 6v5.7c0 4.5-3 8.1-7 9.3-4-1.2-7-4.8-7-9.3V6l7-2.8Z" />
          <polyline points="9.2 12 11.2 14 15 10" />
        </>
      );

    case 'pengguna':
      return (
        <>
          <circle className="obe-duotone-fill" cx="12" cy="8" r="3.6" />
          <circle cx="12" cy="8" r="3.6" />
          <path d="M5 19.5c0-3.3 3.1-5.2 7-5.2s7 1.9 7 5.2" />
        </>
      );

    case 'key':
      return (
        <>
          <circle className="obe-duotone-fill" cx="8.5" cy="14.5" r="4" />
          <circle cx="8.5" cy="14.5" r="4" />
          <path d="m11.5 11.5 7.5-7.5" />
          <path d="m16.5 6.5 2.5 2.5" />
          <path d="m14.2 8.8 2 2" />
        </>
      );

    case 'info':
    default:
      return (
        <>
          <circle className="obe-duotone-fill" cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="9" />
          <line x1="12" y1="11.2" x2="12" y2="16" />
          <circle cx="12" cy="8.2" r="0.9" fill="currentColor" stroke="none" />
        </>
      );
  }
}
