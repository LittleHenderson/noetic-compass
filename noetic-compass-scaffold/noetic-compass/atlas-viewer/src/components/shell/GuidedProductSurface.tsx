import type { ReactNode } from 'react';

import { GuideChatWidget } from '../audit/GuideChatWidget';

export interface GuidedProductSurfaceProps {
  children: ReactNode;
}

export function GuidedProductSurface({
  children,
}: GuidedProductSurfaceProps): JSX.Element {
  return (
    <>
      {children}
      <GuideChatWidget />
    </>
  );
}

export default GuidedProductSurface;
