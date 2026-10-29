import { defineConfig } from 'vite';
import tailwindcss from '@tailwindcss/vite';
export default defineConfig({ base:'./',plugins: [tailwindcss()], server: { proxy: { '/api': 'http://127.0.0.1:8000' } } });
