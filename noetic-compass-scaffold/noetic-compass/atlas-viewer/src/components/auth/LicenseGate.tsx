import type { ReactNode } from 'react';

export default function LicenseGate({ children }: { children?: ReactNode }) {
  return (
    <section>
      <h2>LicenseGate</h2>
      <p>v0.0 placeholder</p>
      {children}
    </section>
  );
}
