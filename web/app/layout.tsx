import "./globals.css";

export const metadata = {
  title: "ETEC - Achados e Perdidos",
  description: "Sistema de Achados e Perdidos da ETEC",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
