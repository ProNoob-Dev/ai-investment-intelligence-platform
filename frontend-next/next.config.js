/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "export",
  // Pretty URLs on static hosts (GitHub Pages): /analyze serves analyze/index.html.
  trailingSlash: true,
  images: { unoptimized: true },
};

module.exports = nextConfig;
