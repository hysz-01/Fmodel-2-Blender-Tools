# FModel 2 Blender Tools

A full-stack asset pipeline addon for **UE/FModel** workflows in Blender 5.0.

---

## Modules

### 1. Asset Pipeline

A 4-step guided wizard to import animations, build asset libraries, and generate thumbnails in one click.

| Step | Function |
|------|----------|
| Flow | Select FModel flow |
| Project | Set source/output directories, skeleton filter (eyedropper pick) |
| Scan | Scan `.ueanim` dictionary — auto-discover skeletons & animations |
| Import/Package | Set import params → import animations → build library → generate thumbnails |

Thumbnails:
- OpenGL viewport snapshot (fast) and Render engine (high quality) modes
- Isolate skeleton children (hide other scene objects)
- Deterministic hash naming — rebaking overwrites old thumbnails
- "Rebake Thumbnails" button for updating without re-importing

---

### 2. Material Tools

Auto-parse UE JSON material data to build PBR/NPR shader node graphs.

**Phase 1 — Asset Discovery**  
Parse FModel-exported model JSON and material instance JSON to extract texture paths and scalar/vector params.

**Phase 2 — Channel Resolution**  
UE param name → standard channel mapping, via:
- GameProfile exact match
- CUE4Parse material param dictionary (200+ entries)
- Built-in keyword matching
- ORM auto-detect (`_ORM`/`_ARM`/`_MRAO` suffix → splits to AO/Roughness/Metallic)

**Phase 3 — Node Building**  
Auto-build Blender material node graphs: Texture → Tool Chain → Shader Group, with NormalMap / Invert / ORM Decode support.

---

### 3. Shader Manager

- **Template Import**: One-click import of PBR Standard, NPR Toon, and more from `Shaders/shaders.blend`
- **Custom Shaders**: Save node groups as reusable templates
- **Interface Mapping**: Auto-detect group sockets, map to standard channels (Base Color, Normal, Roughness, etc.)
- **Preset System**: Export/load presets as JSON, usable from the Material panel

---

### 4. Asset Library

**Animation Assets**  
- Tree / list / card three view modes
- Skeleton filter + name search
- Thumbnail preview + detail panel (frame count, duration, skeleton, source)
- One-click preview/apply to armature
- NLA deployment (replace/append/overwrite)

**Model Assets**  
- Save character models to library (with preview)
- Card grid browser with inline thumbnails
- One-click import to scene

---

### 5. Extension Tools

| Tool | Functions |
|------|-----------|
| Mesh | Clean empty morphs / separate by material |
| Skeleton | Sort bones / batch rename / UE standard naming / bone mapping / pose mirror |
| Animation | Clean action keyframes / batch clean |

---

### 6. GameProfile Manager

Edit GameProfile presets in the Shader Editor:
- Create / delete / edit profiles
- UE param name → standard channel mapping
- Auto-saves to `Shaders/GameProfiles/`

---

## FModel Export Guide

To ensure the material resolver and animation import work correctly, keep these JSON files on export:

### Models
```
✅ .uemodel file
✅ Model JSON (same-name .json with SkeletalMesh / MaterialInterface data)
✅ Material Instance JSON (MaterialInstanceConstant with TextureParameterValues)
```

### Textures
```
✅ All textures (.png / .tga / .dds)
✅ Preserve directory structure (Content/Textures/...)
```

### Animations
```
✅ .ueanim files
✅ Animation JSON (with AnimSequence structure)
✅ Dictionary manifest JSON (with skeleton references and folder hierarchy)
```

### Recommended FModel Settings
- Export mode: **Single File + JSON**
- Texture format: PNG (preserve alpha for WebP thumbnails)
- Material export: **Keep MaterialInstanceConstant texture parameters**
- Directory structure: **Preserve UE4 original hierarchy**

---

## Installation

Place `FModel_Tools/` into the Blender addons directory:

```
%APPDATA%\Blender Foundation\Blender\5.0\scripts\addons\
```

Enable **FModel Tools** in Blender Preferences.

---

## Requirements

- Blender 5.0+
- Bundled vendors: `io_scene_ueformat` / `io_scene_psk_psa` (auto-detect user-installed versions)

---

## Internationalization

- Default: Chinese interface
- Switch Blender language to English → all panels, buttons, descriptions auto-translate (309 entries, `README_ZH.md` for the Chinese version)
