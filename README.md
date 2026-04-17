# 3DMoonX

Cinematic lunar industrial base experience for the web, built with `React`, `Vite`, `React Three Fiber`, and a Blender-authored source scene.

## What is in the repo

- `src/`: the browser experience and autoplay cinematic camera rig
- `public/assets/lunar-base.glb`: lightweight web export of the lunar base scene
- `tools/blender/build_lunar_base.py`: Blender source-of-truth generator
- `tools/blender/generated/`: generated `.blend` and preview render outputs

## Local development

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Production build

```bash
npm run build
```

## Regenerating scene assets

The Blender workflow stays in the repo so the browser asset can be rebuilt from the scene generator.

```bash
npm run scene:build
npm run scene:sync
```

`scene:build` regenerates the preview render, `.blend`, and `GLB` into `tools/blender/generated/`.

`scene:sync` copies the exported `GLB` into `public/assets/` for the web app.

## Deployment

This project is designed for Vercel preview deployments:

```bash
vercel deploy . -y
```
