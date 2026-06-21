/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  eslint: { ignoreDuringBuilds: true },
  async rewrites() {
    const api = process.env.API_PROXY_TARGET;
    // Optional dev convenience: proxy /api to backend if API_PROXY_TARGET set.
    return api ? [{ source: "/api/:path*", destination: `${api}/api/:path*` }] : [];
  },
};
export default nextConfig;
