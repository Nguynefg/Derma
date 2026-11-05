import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
// Keep source paths as supplied; avoids native realpath failures on restricted Windows checkouts.
export default defineConfig({plugins:[react()],resolve:{preserveSymlinks:true},server:{proxy:{'/api':'http://127.0.0.1:8000'}}});
