# Lunar Base Scene Generator

This folder is meant to hold the Blender scene generator for a realistic lunar industrial outpost.

## How to run

### In Blender
1. Open Blender 4.x.
2. Go to the **Scripting** workspace.
3. Open `build_lunar_base.py`.
4. Click **Run Script**.

### From the command line
If Blender is installed and on your `PATH`, you can also run:

```powershell
blender --background --python build_lunar_base.py
```

## Expected output

Running the generator should create a complete lunar base scene with:

- A Moon terrain surface
- Modular main base buildings
- Two cooling towers with vapor plumes
- Solar panel arrays
- Astronauts, vehicles, and utility props
- An Earth background element
- A wide hero camera and one sun light

The scene should be saved as a `.blend` file ready for rendering and further polish.

## Render notes

- Use **Cycles** for the final render.
- Keep the camera in a **wide cinematic** framing with the base centered, towers toward the left rear, and Earth high in the right sky.
- Use a single strong **Sun** light to match harsh lunar daylight and crisp shadows.

