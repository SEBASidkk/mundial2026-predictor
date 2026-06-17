/**
 * Country flags for World Cup teams.
 *
 * The API ships FIFA 3-letter codes (BRA, FRA, KSA…). Emoji flags are built
 * from ISO-3166 alpha-2 regional indicator pairs, so we map FIFA→ISO2 first,
 * then convert. England/Scotland/Wales have no ISO2 country, so they use the
 * special subdivision tag-sequence emojis directly.
 */

const FIFA_TO_ISO2: Record<string, string> = {
  MEX: 'MX', KOR: 'KR', CAN: 'CA', USA: 'US', QAT: 'QA', BRA: 'BR', HAI: 'HT',
  AUS: 'AU', GER: 'DE', NED: 'NL', CIV: 'CI', SWE: 'SE', ESP: 'ES', BEL: 'BE',
  KSA: 'SA', IRN: 'IR', FRA: 'FR', IRQ: 'IQ', ARG: 'AR', AUT: 'AT', POR: 'PT',
  GHA: 'GH', UZB: 'UZ', CZE: 'CZ', SUI: 'CH', TUR: 'TR', ECU: 'EC', TUN: 'TN',
  URU: 'UY', NZL: 'NZ', NOR: 'NO', JOR: 'JO', PAN: 'PA', COL: 'CO', BIH: 'BA',
  MAR: 'MA', RSA: 'ZA', CUW: 'CW', JPN: 'JP', PAR: 'PY', SEN: 'SN', CPV: 'CV',
  EGY: 'EG', CRO: 'HR', COD: 'CD', ALG: 'DZ', COL2: 'CO',
};

// Subdivisions with their own emoji flags (UK home nations).
const SPECIAL: Record<string, string> = {
  ENG: '🏴\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}',
  SCO: '🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}',
  WAL: '🏴\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}',
};

function iso2ToEmoji(iso2: string): string {
  return iso2
    .toUpperCase()
    .replace(/./g, c => String.fromCodePoint(127397 + c.charCodeAt(0)));
}

/** Emoji flag for a FIFA 3-letter code; falls back to 🏳️ if unknown. */
export function flagEmoji(code: string | null | undefined): string {
  if (!code) return '🏳️';
  const up = code.toUpperCase();
  if (SPECIAL[up]) return SPECIAL[up];
  const iso2 = FIFA_TO_ISO2[up];
  return iso2 ? iso2ToEmoji(iso2) : '🏳️';
}

/** Mexico Central time (CDMX) is UTC-6 year-round (no DST since 2022). */
export const MX_TZ = '-0600';
