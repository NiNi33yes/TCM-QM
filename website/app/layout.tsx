import type { Metadata } from "next";
import "./globals.css";
import "./graph-v2.css";
import "./structure-viewers.css";
import "./downloads.css";
import "./readability.css";
export const metadata: Metadata = {
  title: {
    default: "TCM-QM Atlas · 可追溯量子化学数据集",
    template: "%s · TCM-QM Atlas",
  },
  description:
    "探索 3,196 个具有经裁决 TCMSP 来源关系的分子及其电子结构、热化学、振动性质和质量记录。",
  icons: { icon: "/favicon.svg" },
  openGraph: {
    title: "TCM-QM Atlas · 可追溯量子化学数据集",
    description:
      "3,196 个 PubChem 分子、495 味 TCMSP 药材与 16,918 条直接来源关系。",
    images: [{ url: "/og.png", width: 1536, height: 1024 }],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "TCM-QM Atlas · 可追溯量子化学数据集",
    description:
      "3,196 个 PubChem 分子、495 味 TCMSP 药材与 16,918 条直接来源关系。",
    images: ["/og.png"],
  },
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
