# 3DMoonX

![3DMoonX lunar base preview](./tools/blender/generated/lunar_base_preview.png)

3DMoonX is a cinematic lunar-industrial-base experience for the web. It combines a Blender-authored source scene with a React + React Three Fiber front end so the same world can be regenerated as a polished preview render, a reusable `.blend`, and a lightweight browser-ready `GLB`.

## Live links

- Live site: [3dmoonx.vercel.app](https://3dmoonx.vercel.app)
- Repository: [github.com/zrt219/3DMoonX](https://github.com/zrt219/3DMoonX)
- Case study: [CASESTUDY.md](./CASESTUDY.md)

## What this project does

3DMoonX recreates a futuristic lunar power and research outpost as an art-directed web experience.

- A wide cinematic composition centers the base on the Moon's surface.
- Cooling towers anchor the left-rear silhouette.
- Earth appears above the horizon as a dramatic focal point.
- Solar arrays frame the foreground to pull the eye into the scene.
- The browser experience uses a lightweight exported asset, then adds a curated camera drift, browser-side Earth treatment, and atmosphere-focused lighting to preserve the intended shot.

## Why it exists

The goal was not to ship a generic model viewer. The goal was to turn a Blender-built environment into a browser experience that still feels deliberate, cinematic, and believable.

That meant solving two different problems at once:

1. Build a reproducible Blender scene that can regenerate the outpost and render high-quality source outputs.
2. Translate that scene into a performant web presentation that still reads like the original concept instead of a raw asset dump.

## Stack

- Blender 5.1 for procedural scene generation and source-of-truth asset creation
- Python for the Blender scene generator
- React 19 + Vite + TypeScript for the web app
- React Three Fiber + Drei + Three.js for the browser scene
- Vercel for deployment

## Repo structure

```text
3DMoonX/
- public/assets/
  - lunar-base.glb          # shipped browser asset
- src/
  - App.tsx                 # cinematic scene composition
  - App.css                 # visual presentation
  - index.css               # global styling
- tools/blender/
  - build_lunar_base.py     # Blender generator and export pipeline
  - README-source.md        # source-scene notes
  - generated/              # generated .blend, preview, and GLB outputs
- CASESTUDY.md              # project write-up
```

## Local development

Install dependencies and run the site locally:

```bash
npm install
npm run dev
```

Open `http://127.0.0.1:5173/`.

## Blender pipeline

The Blender workflow stays in the repo so the web asset can be rebuilt from source instead of being treated as a one-off export.

### Regenerate the source scene and web asset

```bash
npm run scene:build
npm run scene:sync
```

`scene:build`:

- opens Blender in background mode
- regenerates the lunar base scene
- saves the `.blend`
- renders a preview image
- exports a lightweight `GLB`

`scene:sync` copies the generated `GLB` into `public/assets/` for the web app.

## Production build

```bash
npm run build
```

## Deployment

The project is set up for Vercel deployments.

```bash
vercel deploy . -y
```

Current production URL:

- [3dmoonx.vercel.app](https://3dmoonx.vercel.app)

## Highlights

- Blender-generated lunar base scene with named collections and modular assets
- Lightweight `GLB` export path for browser delivery
- Cinematic autoplay camera instead of free-orbit interaction
- Browser-side art direction layered on top of the exported scene
- End-to-end source pipeline that keeps the `.blend`, preview render, and web asset in sync

## Case study

If you want the full story behind the build, pipeline decisions, and technical tradeoffs, see [CASESTUDY.md](./CASESTUDY.md).

## Next ideas

- Add a second hero camera sequence for a slow orbital reveal
- Replace procedural Earth with a richer texture pipeline for closer shots
- Introduce optional postprocessing and atmospheric dust passes for higher-fidelity presentation

## On-Chain Systems Portfolio

Core XRPL EVM systems plus related public product and AI repositories from the same portfolio.

<table>
  <thead>
    <tr>
      <th>Project</th>
      <th>Description</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><a href="https://github.com/zrt219/Zuc-Mine-Command-Center">ZUC Mine Command Center</a></td>
      <td>On-chain uranium mining operations dashboard with real-time reserve tracking, miner registry, and direct contract interaction through a frontend-only control surface.</td>
      <td><a href="https://zuc-mine-command-center.vercel.app/">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/-U235-Fuel-Cycle-">U235 Fuel Cycle</a></td>
      <td>Deterministic XRPL EVM fuel-cycle pipeline that tracks uranium batches from ore to enriched fuel rod with full on-chain traceability.</td>
      <td><a href="https://u235-fuel-cycle.vercel.app/">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/ISR-Network">ISR Network</a></td>
      <td>In-situ recovery control system with on-chain asset tracking, lifecycle state transitions, and operator-facing industrial simulation.</td>
      <td><a href="https://isr-network.vercel.app/">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Dark-Matter-Farm">Dark Matter Farm</a></td>
      <td>XRPL EVM staking protocol with three orbit tiers, lock-period yield mechanics, and event-driven reward emissions.</td>
      <td><a href="https://dark-matter-farm.vercel.app/">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Cohr-Lab">Cohr Lab</a></td>
      <td>Semiconductor laser fabrication lifecycle modeled as an immutable on-chain state machine from crystal growth to final pigtail.</td>
      <td><a href="https://cohr-lab.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/ForgeX">ForgeX</a></td>
      <td>Foundry-powered XRPL EVM deployment console that combines a natural-language UI, Node CLI orchestration, and realtime shader-based visuals.</td>
      <td><a href="https://forgex-theta.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/DatumX">DatumX</a></td>
      <td>Verification protocol for AI-transformed industrial data with deterministic lineage, validator review, and XRPL EVM finalization.</td>
      <td><a href="https://datumx.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Ethex-Lottery-Game">Ethex Lottery Game</a></td>
      <td>Foundry plus Next.js betting workflow that modernizes the EthexLoto lifecycle for XRPL EVM reviewer-facing execution.</td>
      <td>Public Repo</td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/3DMoonX">3DMoonX</a></td>
      <td>Cinematic lunar industrial-base experience that combines Blender source assets with a React Three Fiber web runtime.</td>
      <td><a href="https://3dmoonx.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Unknown002">Unknown002</a></td>
      <td>Browser-based 3D engineering viewer for a nuclear-electric propulsion spacecraft concept with staged prompt-pack support.</td>
      <td>Public Repo</td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/AI-Engineering-Evidence-Engine">AI Engineering Evidence Engine</a></td>
      <td>Interactive evidence dashboard that turns local engineering proof into a reviewer-facing systems narrative.</td>
      <td><a href="https://zhane-grey-evidence-dashboard.vercel.app/">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Build-Doctor">Build Doctor</a></td>
      <td>Codex-style build diagnosis harness for failed Next.js and Vercel builds with deterministic failure analysis.</td>
      <td><a href="https://vercel-build-doctor-agent.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/ai-gateway-failover-playground">AI Gateway Failover Playground</a></td>
      <td>Public-facing sandbox for request routing, provider fallback, and resilient AI gateway behavior.</td>
      <td><a href="https://ai-gateway-failover-playground.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/enterprise-agent-workflow-studio">Enterprise Agent Workflow Studio</a></td>
      <td>Public-facing studio for approval-gated enterprise agent workflows, risk scoring, and audit-oriented design.</td>
      <td><a href="https://enterprise-agent-workflow-studio.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/resume-evidence-rag-auditor">Resume Evidence RAG Auditor</a></td>
      <td>Public-facing proof surface for claim verification, evidence retrieval, and grounded resume bullet generation.</td>
      <td><a href="https://resume-evidence-rag-auditor.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/AI-resume-tailor-service-">AI Resume Tailor Service</a></td>
      <td>Static Vercel-ready application for evidence-backed resume, cover-letter, and job-packet tailoring.</td>
      <td><a href="https://ai-resume-tailor-service.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/Fuji">Fuji</a></td>
      <td>Cinematic Next.js Fuji gallery atlas for portfolio storytelling and visual system design.</td>
      <td><a href="https://fuji-byzrt.vercel.app">Live</a></td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/ai-agents-for-beginners">AI Agents for Beginners</a></td>
      <td>Lesson repository for getting started building AI agents.</td>
      <td>Public Repo</td>
    </tr>
    <tr>
      <td><a href="https://github.com/zrt219/agentic-rag-memory-digital-twin-edge-system">Agentic RAG Memory Digital Twin Edge System</a></td>
      <td>Public-facing landing page for an agentic RAG, memory, and digital-twin edge-system portfolio project.</td>
      <td><a href="https://agentic-rag-memory-digital-twin-edg.vercel.app">Live</a></td>
    </tr>
  </tbody>
</table>

