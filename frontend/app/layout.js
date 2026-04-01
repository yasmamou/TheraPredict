import './globals.css'

export const metadata = {
  title: 'TheraPredict — Mechanistic Theranostic Simulation Platform',
  description:
    'Predict biodistribution, radiation dosimetry, and biological effects of theranostic agents. ' +
    '7-module mechanistic pipeline validated on PSMA, SSTR2, HER2, FAP, CD20. ' +
    'Built on PBPK modeling, MIRD dosimetry, and peer-reviewed pharmacokinetic science.',
  keywords: [
    'theranostics', 'PBPK', 'biodistribution', 'dosimetry', 'nuclear medicine',
    'PSMA', 'Lu-177', 'radioligand therapy', 'simulation', 'pharmacokinetics',
  ],
  openGraph: {
    title: 'TheraPredict — Mechanistic Theranostic Simulation',
    description: 'Simulate biodistribution, dosimetry, and biological effects for theranostic agents.',
    type: 'website',
  },
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body style={{
        margin: 0,
        padding: 0,
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
        WebkitFontSmoothing: 'antialiased',
        MozOsxFontSmoothing: 'grayscale',
        textRendering: 'optimizeLegibility',
      }}>
        {children}
      </body>
    </html>
  )
}
