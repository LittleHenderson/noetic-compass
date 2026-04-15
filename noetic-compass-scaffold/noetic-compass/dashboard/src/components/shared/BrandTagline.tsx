interface BrandTaglineProps {
  variant?: 'header' | 'hero' | 'intro';
  align?: 'left' | 'center';
  showCompass?: boolean;
}

export function BrandTagline({
  variant = 'header',
  align = 'left',
  showCompass = true,
}: BrandTaglineProps) {
  const alignmentClass = align === 'center' ? 'items-center text-center' : 'items-start text-left';
  const taglineClass = variant === 'header'
    ? 'brand-tagline brand-tagline-header'
    : variant === 'intro'
      ? 'brand-tagline brand-tagline-intro'
      : 'brand-tagline brand-tagline-hero';
  const compassClass = variant === 'header'
    ? 'brand-compass brand-compass-header'
    : variant === 'intro'
      ? 'brand-compass brand-compass-intro'
      : 'brand-compass brand-compass-hero';

  return (
    <div className={`flex flex-col ${alignmentClass}`}>
      <p className={taglineClass}>
        <span>Measure How </span>
        <span className="brand-tagline-ai">Ai</span>
        <span> Thinks</span>
      </p>
      {showCompass && (
        <div className={compassClass}>
          <img src="/icon-192.svg" alt="" className="brand-compass-icon" />
          <span>Noetic Compass</span>
        </div>
      )}
    </div>
  );
}
