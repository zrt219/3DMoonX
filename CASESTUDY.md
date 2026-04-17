# 3DMoonX Case Study

## Overview

3DMoonX is a cinematic web adaptation of a futuristic lunar nuclear-energy outpost. The project started as a Blender scene-generation task and evolved into a complete Blender-to-web pipeline: a reproducible source scene, a lightweight exported `GLB`, and a deployed React Three Fiber experience on Vercel.

Live project:

- [3dmoonx.vercel.app](https://3dmoonx.vercel.app)

Source repository:

- [github.com/zrt219/3DMoonX](https://github.com/zrt219/3DMoonX)

## The brief

The target scene was a wide cinematic shot of a lunar industrial base:

- gray regolith terrain with craters and subtle elevation changes
- a central research and power facility
- two large cooling towers at the left-rear
- blue solar arrays spread through the foreground and midground
- astronauts, utility equipment, and service vehicles
- Earth rising above the horizon in the upper-right sky

The visual direction was realistic sci-fi rather than stylized or gamey.

## The challenge

There were really two challenges hiding inside the same brief.

### 1. Build a believable scene

The Blender output needed to read as a lunar industrial base rather than a basic gray blockout. That meant improving:

- terrain silhouette
- camera composition
- Earth placement
- material response
- lighting contrast

### 2. Make it work on the web

A direct export from Blender was too heavy and too literal for the browser. The project needed a hybrid approach:

- keep Blender as the source of truth
- export a web-friendly asset
- reintroduce some art direction in the browser
- preserve the cinematic intent instead of shipping a generic orbit-control viewer

## Goals

- Keep the scene reproducible from code
- Deliver a `.blend`, preview render, and browser asset from the same pipeline
- Preserve the reference composition in the browser
- Keep asset size manageable for a Vercel-hosted site
- Make the experience feel curated and cinematic, not purely technical

## Approach

### Blender as the source of truth

The Blender scene is generated through `tools/blender/build_lunar_base.py`. The script owns the scene layout, materials, camera setup, and export flow.

That decision made the project easier to evolve because the scene is not trapped inside a manually edited `.blend` alone. The same script can:

- regenerate the outpost
- render a preview
- save the source `.blend`
- export the browser-ready `GLB`

### A hybrid browser presentation

Rather than aiming for a one-to-one Cycles reproduction in real time, the browser version is art-directed for the web.

The exported `GLB` preserves the main base forms, towers, arrays, and props. Then the React Three Fiber app adds:

- a controlled autoplay camera drift
- a browser-side Earth treatment
- lighting tuned for readability
- foreground framing elements that strengthen the shot

This keeps the experience visually intentional while staying lightweight enough to load quickly.

## Technical stack

- Blender 5.1
- Python
- React 19
- TypeScript
- Vite
- Three.js
- React Three Fiber
- Drei
- Vercel

## Key implementation decisions

### 1. Separate source fidelity from web fidelity

The source scene and the browser scene solve different problems.

- Blender focuses on scene generation, composition, and renderable source outputs.
- The browser experience focuses on atmosphere, load performance, and presentation control.

Trying to force both into exactly the same representation would have made both worse.

### 2. Use a curated camera, not free orbit controls

The project is strongest as a staged hero shot. Free orbit controls would make it easier to inspect the asset, but they would also weaken the visual storytelling.

The final experience uses subtle autoplay motion and light pointer response so the user feels movement without losing the composition.

### 3. Keep the asset lightweight

A browser scene that looks cinematic but loads poorly is not a win.

The export pipeline trims the scene for web use by reducing unnecessary export weight and keeping the final asset manageable. The shipped `GLB` ended up dramatically smaller than the initial raw output, which made deployment and streaming practical.

### 4. Keep the pipeline in the repo

The project does not just ship the final asset. It also ships the tooling that created it.

That means the repo contains:

- the web app
- the Blender generator
- generated outputs
- the exported browser asset

This makes the project easier to audit, improve, and hand off.

## What changed during development

The early generated scene technically worked, but it read like a blockout:

- the terrain looked like a rectangular slab
- Earth looked like a placeholder sphere
- the camera framing did not fully sell the concept
- materials and lighting were too flat for the target mood

The refinement pass focused on:

- better Earth placement and visual treatment
- stronger camera composition
- more believable material tuning
- improved lunar lighting contrast
- safer Blender generation paths for background execution
- web export and deployment readiness

## Outcome

The final result is a deployed interactive landing page that preserves the original concept as a cinematic browser experience.

Deliverables include:

- a regenerated Blender source scene
- a preview render
- a lightweight exported `GLB`
- a React Three Fiber site
- a live Vercel deployment

## What worked well

- Keeping Blender as the source of truth avoided one-off export drift
- Treating the browser build as a curated presentation produced a better result than a generic viewer
- The modular scene/export split made it possible to tune fidelity and performance independently

## What I would improve next

- Push the Earth material closer to photoreal texture detail
- Add a second camera sequence or guided scene states
- Expand the atmospheric treatment with richer dust and subtle postprocessing
- Add explicit performance tiers for lower-powered devices

## Takeaway

3DMoonX shows a practical way to move from concept art direction to a deployable real-time experience without losing authorship in the handoff from Blender to web.

The most important decision was not a shader or a framework choice. It was treating the browser version as a designed experience with its own constraints while still keeping the Blender scene as the authoritative source.
