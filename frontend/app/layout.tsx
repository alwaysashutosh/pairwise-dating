import type { Metadata } from 'next';
import './styles.css';

export const metadata: Metadata = { title: 'AI Compatibility Simulation', description: 'An AI-generated compatibility simulation using fixture or public-profile data.' };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
