# FModel_Tools/Universal_tools/material/channel_resolver.py
# Phase 2: Channel Resolution — maps UE material params to preset channels
# using GameProfile configuration. No Blender dependency.

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple

from .manifest_builder import MaterialManifest


# ============================================================
# Data Structures
# ============================================================

@dataclass
class GameProfile:
    """Per-game configuration driving UE parameter→channel mapping."""
    game_id: str = ""
    display_name: str = ""
    param_mapping: dict = field(default_factory=dict)   # {ue_param: channel|null}
    parent_inheritance: bool = True
    colorspace_rules: dict = field(default_factory=dict)  # {suffix: colorspace}
    default_preset: str = "pbr_standard"
    tool_groups_default: list = field(default_factory=list)

    @classmethod
    def load(cls, filepath: str) -> Optional["GameProfile"]:
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "param_mapping" in data:
                data["param_mapping"] = {k.lower(): v for k, v in data["param_mapping"].items()}
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        except (json.JSONDecodeError, IOError):
            return None


@dataclass
class ChannelAssignment:
    """Resolved mapping: a single UE param → preset channel + filesystem path."""
    channel: str              # "base_color", "normal", "roughness", etc.
    texture_path: str         # absolute path to texture file, or ""
    ue_param: str             # original UE parameter name
    colorspace: str           # "sRGB" | "Non-Color"
    source: str               # "manifest" | "profile" | "fallback" | "suffix"
    score: float = 1.0        # 1.0 = exact from manifest, lower = heuristic
    fallback_value: float = 0.0  # scalar fallback from manifest
    tool_groups: list = field(default_factory=list)
    is_normal_map: bool = False  # Phase 3 uses this to insert NormalMap node


# ============================================================
# Channel Map — Extended built-in for most games without profile
# ============================================================

_BUILTIN_MAPPING: List[Tuple[str, str]] = [
    # === Base Color / Diffuse / Albedo ===
    ("base_color_texture", "base_color"), ("basecolortexture", "base_color"),
    ("basecolourtexture", "base_color"), ("base color", "base_color"),
    ("basecolor", "base_color"), ("base_colour", "base_color"),
    ("tex_diffuse", "base_color"), ("tex_diff", "base_color"),
    ("diffusemap", "base_color"), ("diffuse_map", "base_color"),
    ("diffusetexture", "base_color"), ("diffuse_texture", "base_color"),
    ("diffuse", "base_color"), ("diff", "base_color"),
    ("albedomap", "base_color"), ("albedo_map", "base_color"),
    ("albedotexture", "base_color"), ("albedo_texture", "base_color"),
    ("albedo", "base_color"),
    ("t_diffuse", "base_color"), ("t_diff", "base_color"),
    ("t_basecol", "base_color"), ("t_basecolor", "base_color"),
    ("t_albedo", "base_color"),
    ("maintex", "base_color"), ("_maintex", "base_color"),  # Unity
    ("_basecolormap", "base_color"), ("_basemap", "base_color"),
    ("colormap", "base_color"), ("color_map", "base_color"),
    ("colortexture", "base_color"), ("colourtexture", "base_color"),
    ("base_col", "base_color"), ("base_color", "base_color"),
    ("col", "base_color"), ("map_d", "base_color"),

    # === Normal ===
    ("normalmap", "normal"), ("normal_map", "normal"),
    ("normaltexture", "normal"), ("normal_texture", "normal"),
    ("tex_normal", "normal"), ("t_normal", "normal"),
    ("normal", "normal"), ("norm", "normal"),
    ("nm", "normal"), ("map_n", "normal"),
    ("t_n", "normal"), ("t_nm", "normal"),
    ("bumpmap", "normal"), ("_bumpmap", "normal"),  # Unity
    ("bump_map", "normal"), ("bumptexture", "normal"),
    ("bump", "normal"),

    # === Roughness ===
    ("roughnessmap", "roughness"), ("roughness_map", "roughness"),
    ("roughnesstexture", "roughness"), ("roughness_texture", "roughness"),
    ("tex_roughness", "roughness"), ("t_roughness", "roughness"),
    ("roughness", "roughness"),
    ("rough", "roughness"),
    ("roughmap", "roughness"), ("rough_map", "roughness"),
    ("map_r", "roughness"), ("t_r", "roughness"),
    ("gloss", "roughness"), ("glossiness", "roughness"),  # invert later
    ("smoothness", "roughness"),  # Unity

    # === Metallic / Metalness ===
    ("metallicmap", "metallic"), ("metallic_map", "metallic"),
    ("metallictexture", "metallic"), ("metallic_texture", "metallic"),
    ("tex_metallic", "metallic"), ("t_metallic", "metallic"),
    ("metallic", "metallic"), ("metal", "metallic"),
    ("metalness", "metallic"), ("metalnessmap", "metallic"),
    ("metalmap", "metallic"), ("metal_map", "metallic"),
    ("map_m", "metallic"), ("t_m", "metallic"),
    ("metall", "metallic"),

    # === Ambient Occlusion ===
    ("ambientocclusion", "ao"), ("ambient_occlusion", "ao"),
    ("aomap", "ao"), ("ao_map", "ao"),
    ("aotexture", "ao"), ("ao_texture", "ao"),
    ("tex_ao", "ao"), ("t_ao", "ao"),
    ("ao", "ao"), ("map_ao", "ao"),
    ("occlusionmap", "ao"), ("occlusion_map", "ao"),
    ("occlusiontexture", "ao"), ("occlusion_texture", "ao"),
    ("occlusion", "ao"),
    ("mixed_ao", "ao"),

    # === Emissive / Emission ===
    ("emissive", "emissive"), ("emission", "emissive"),
    ("emissivecolor", "emissive"), ("emissive_color", "emissive"),
    ("emissivetexture", "emissive"), ("emissive_texture", "emissive"),
    ("emissivemap", "emissive"), ("emissive_map", "emissive"),
    ("tex_emissive", "emissive"), ("t_emissive", "emissive"),
    ("emissionmap", "emissive"), ("emission_map", "emissive"),
    ("emiss", "emissive"), ("emissive_color_texture", "emissive"),
    ("map_e", "emissive"),

    # === Alpha / Opacity ===
    ("opacitymask", "alpha"), ("opacity_mask", "alpha"),
    ("opacitymap", "alpha"), ("opacity_map", "alpha"),
    ("opacitytexture", "alpha"), ("opacity_texture", "alpha"),
    ("opacity", "alpha"), ("opa", "alpha"),
    ("alphamap", "alpha"), ("alpha_map", "alpha"),
    ("alphatexture", "alpha"), ("alpha_texture", "alpha"),
    ("alpha", "alpha"), ("tex_alpha", "alpha"),
    ("t_alpha", "alpha"), ("tex_opacity", "alpha"),
    ("transparency", "alpha"), ("trans", "alpha"),
    ("translucent", "alpha"), ("translucency", "alpha"),
    ("transmissive", "alpha"),
    ("cutoff", "alpha"), ("cutoffmap", "alpha"),
    ("mask", "alpha"), ("maskmap", "alpha"),
    ("clip", "alpha"),

    # === Thickness ===
    ("thicknessmap", "thickness"), ("thickness_map", "thickness"),
    ("thicknesstexture", "thickness"), ("thickness_texture", "thickness"),
    ("thickness", "thickness"), ("tex_thickness", "thickness"),
    ("t_thickness", "thickness"), ("thk", "thickness"),

    # === ORM / Packed (AO+Roughness+Metallic) ===
    ("orm", "orm"), ("orm_map", "orm"),
    ("ormtexture", "orm"), ("orm_texture", "orm"),
    ("tex_orm", "orm"), ("t_orm", "orm"),
    ("arm", "orm"), ("arm_map", "orm"),
    ("mrao", "orm"), ("mrao_map", "orm"),
    ("packed", "orm"), ("packedtexture", "orm"),
    ("occlusionroughnessmetallic", "orm"),
    ("t_orm_map", "orm"),

    # === Specular ===
    ("specularmap", "specular"), ("specular_map", "specular"),
    ("speculartexture", "specular"), ("specular_texture", "specular"),
    ("tex_specular", "specular"), ("t_specular", "specular"),
    ("specular", "specular"), ("spec", "specular"),
    ("specmap", "specular"), ("spec_map", "specular"),
    ("map_s", "specular"),

    # === Subsurface / SSS ===
    ("subsurfacecolor", "subsurface"), ("subsurface_color", "subsurface"),
    ("subsurfacetexture", "subsurface"), ("subsurface_texture", "subsurface"),
    ("subsurface", "subsurface"), ("sss", "subsurface"),
    ("subsurfacemap", "subsurface"), ("sss_map", "subsurface"),

    # === Height / Displacement / Bump ===
    ("heightmap", "height"), ("height_map", "height"),
    ("heighttexture", "height"), ("height_texture", "height"),
    ("height", "height"), ("displacement", "height"),
    ("displacementmap", "height"), ("displacement_map", "height"),
    ("tex_height", "height"), ("t_height", "height"),
    ("parallax", "height"), ("parallaxmap", "height"),

    # === Clear Coat ===
    ("clearcoat", "clearcoat"), ("clear_coat", "clearcoat"),
    ("clearcoatmap", "clearcoat"), ("clearcoat_texture", "clearcoat"),

    # === Unity HDRP ===
    ("_detailmask", "detail_mask"), ("_maskmap", "orm"),
    ("_metallicglossmap", "orm"), ("_specglossmap", "specular"),

    # === NPR / Anime ===
    ("hilight", "other"), ("highlight", "other"),
    ("sdf", "other"), ("matcap", "other"),
    ("ramp", "other"), ("rampmap", "other"),
    ("toonramp", "other"), ("shademap", "other"),
    ("outline", "other"), ("outlinewidth", "other"),
    ("ilmmap", "other"), ("ilm", "other"),
]


# Suffix-based colorspace detection (checked before channel-based)
_SUFFIX_COLORSPACE: List[Tuple[str, str]] = [
    # Non-Color suffixes
    ("_n", "Non-Color"), ("_normal", "Non-Color"), ("_nm", "Non-Color"),
    ("_bump", "Non-Color"),
    ("_r", "Non-Color"), ("_rough", "Non-Color"), ("_roughness", "Non-Color"),
    ("_gloss", "Non-Color"), ("_glossiness", "Non-Color"), ("_smoothness", "Non-Color"),
    ("_m", "Non-Color"), ("_metal", "Non-Color"), ("_metallic", "Non-Color"),
    ("_metall", "Non-Color"), ("_metalness", "Non-Color"),
    ("_ao", "Non-Color"), ("_occlusion", "Non-Color"),
    ("_orm", "Non-Color"), ("_arm", "Non-Color"), ("_mrao", "Non-Color"),
    ("_packed", "Non-Color"), ("_mask", "Non-Color"),
    ("_height", "Non-Color"), ("_displacement", "Non-Color"),
    ("_spec", "Non-Color"), ("_specular", "Non-Color"),
    ("_alpha", "Non-Color"), ("_opacity", "Non-Color"),
    ("_sss", "Non-Color"), ("_subsurface", "Non-Color"),
    ("_thickness", "Non-Color"), ("_thk", "Non-Color"),
    # sRGB suffixes (explicit)
    ("_d", "sRGB"), ("_diffuse", "sRGB"),
    ("_albedo", "sRGB"), ("_basecol", "sRGB"),
    ("_col", "sRGB"), ("_color", "sRGB"), ("_colour", "sRGB"),
    ("_e", "sRGB"), ("_emissive", "sRGB"), ("_emission", "sRGB"),
]


# Channel-based file suffix hints for missing-texture fallback scanning
_CHANNEL_SUFFIXES: Dict[str, List[str]] = {
    "base_color": ["_d", "_diffuse", "_albedo", "_basecol", "_basecolor", "_col", "_color", "_bc"],
    "normal":     ["_n", "_normal", "_nm", "_bump"],
    "roughness":  ["_r", "_rough", "_roughness", "_gloss"],
    "metallic":   ["_m", "_metal", "_metallic", "_metall", "_metalness"],
    "ao":         ["_ao", "_occlusion"],
    "emissive":   ["_e", "_emissive", "_emission"],
    "alpha":      ["_alpha", "_opacity", "_opa", "_alpha_mask", "_opa_mask"],
    "orm":        ["_orm", "_arm", "_mrao", "_packed"],
    "specular":   ["_s", "_spec", "_specular"],
    "height":     ["_height", "_h", "_displacement", "_parallax"],
    "subsurface": ["_sss", "_subsurface"],
    "clearcoat":  ["_clearcoat", "_coat"],
    "thickness":  ["_thickness", "_thk"],
}


# Supported texture file formats for scanning
_TEX_EXTENSIONS = (
    '.png', '.jpg', '.jpeg', '.tga', '.tiff', '.tif', '.bmp',
    '.exr', '.hdr', '.dds', '.webp', '.psd', '.ktx', '.ktx2',
    '.gif',
)

# CUE4Parse CMaterialParams2 — authoritative UE parameter name → channel mapping
# Source: CUE4Parse/UE4/Assets/Exports/Material/CMaterialParams2.cs
_CUE4PARSE_MAP: Dict[str, str] = {
    # ── Diffuse (base_color) ──
    "trunk_basecolor": "base_color", "shadeddiffuse": "base_color",
    "litdiffuse": "base_color", "base colour": "base_color", "clrm": "base_color",
    "diffuse_map": "base_color", "base color": "base_color", "base_tex": "base_color",
    "basetex": "base_color", "colortexture": "base_color",
    "background diffuse": "base_color", "bg diffuse texture": "base_color",
    "diffuse": "base_color", "diffuse_1": "base_color", "diffusetexture": "base_color",
    "diffusemap": "base_color", "diffuse a": "base_color",
    "base color map": "base_color", "desattexture": "base_color",
    "diffuse a map": "base_color", "diffuse top": "base_color",
    "diffuse side": "base_color", "base diffuse": "base_color",
    "diffuse base": "base_color", "diffuse base map": "base_color",
    "diffuse color map": "base_color", "basecolor_tex": "base_color",
    "diffuselayer1": "base_color", "1 - albedo": "base_color",
    "albedo": "base_color", "aldebo": "base_color",
    "alb": "base_color", "texturealbedo": "base_color", "albedotex": "base_color",
    "color_texture": "base_color", "base_d": "base_color",
    "tex_basecolor": "base_color", "albedocolour": "base_color", "bcr": "base_color",
    "base color texture": "base_color", "basecolortexture": "base_color",
    "basecolor_texture": "base_color", "base_color": "base_color",
    "basecolor": "base_color", "tex_bc": "base_color",
    "texa_bc": "base_color", "basediffuse": "base_color",
    "base texture color": "base_color", "basecolora": "base_color",
    "bc": "base_color", "bca": "base_color", "bc_map": "base_color",
    "base map": "base_color", "bce": "base_color", "color": "base_color",
    "co": "base_color", "co_": "base_color", "co_1": "base_color",
    "base_co": "base_color", "base color + linework": "base_color",
    "basecolorvt": "base_color", "tex_color": "base_color",
    "color tex": "base_color", "texcolor": "base_color", "albedmap": "base_color",
    "tex_colormap": "base_color", "colormap": "base_color",
    "main_t_basecolor": "base_color", "basecolour": "base_color",
    "base_texture": "base_color", "t_basecolor": "base_color",
    "decal_texture": "base_color", "petaldetailmap": "base_color",
    "clifftexture": "base_color", "m1_t_bc": "base_color",
    "skin diffuse": "base_color", "color_main": "base_color",
    "maintex": "base_color", "tonerimtex": "base_color",
    "primary base color": "base_color", "basecolor_nonvt": "base_color",
    "l0_b/bm": "base_color", "b/bm": "base_color",
    "nro_base_color": "base_color", "baecolor_tex": "base_color",
    "layer00_basecolor_tex": "base_color", "01. diffuse texture": "base_color",
    "basemap": "base_color", "tex_skinbase_bc": "base_color",
    "tex_core_layer_albedo": "base_color", "bc_texture": "base_color",
    "rgbmap": "base_color", "rgb_map": "base_color",
    "mw_texturebasecolor": "base_color", "texture": "base_color",
    "coloropacity": "base_color", "simple_basecolor_texture": "base_color",
    "albedotexture": "base_color", "albedo texture": "base_color",
    "bc_lut": "base_color", "bco": "base_color", "cr": "base_color",
    "c/r": "base_color", "basecolor_tex(a:mask)": "base_color",
    "base color map vt": "base_color", "basecolor_vt": "base_color",
    "basecolor_map": "base_color", "bacecolor_map": "base_color",
    "colorao": "base_color", "rgbmask": "base_color",
    "color & alpha": "base_color", "basecolor - texture": "base_color",
    "clothing diffuse": "base_color", "base color [standard]": "base_color",
    "base color vt": "base_color", "basecolroughness": "base_color",
    "basecolalpha": "base_color", "color map (packed)": "base_color",
    "d(id)": "base_color", "bc texture (bc/bco)": "base_color",
    "bcm basecolor|metallic map": "base_color",
    # Layer 1-7 (secondary UV)
    "diffuse_texture_2": "base_color", "diffuselayer2": "base_color",
    "diffuse b": "base_color", "diffuse b map": "base_color",
    "basecolorb": "base_color", "background diffuse 2": "base_color",
    "diffuse_texture_3": "base_color", "diffuselayer3": "base_color",
    "diffuse c": "base_color", "diffuse c map": "base_color",
    "basecolorc": "base_color", "background diffuse 3": "base_color",

    # ── Normals ──
    "trunk_normal": "normal", "t_normal": "normal", "normal": "normal",
    "normalmap": "normal", "nrro": "normal", "base normal": "normal",
    "basenormalmap": "normal", "normals": "normal",
    "normala": "normal", "normaltexture": "normal",
    "normal texture": "normal", "normal_texture": "normal",
    "normal tex": "normal",
    "normal a map": "normal", "normals top": "normal",
    "normals side": "normal", "fallback normal": "normal",
    "base_n": "normal", "basenormal_tex": "normal",
    "basenormal_nonvt": "normal", "base_normal": "normal",
    "basenormal": "normal", "normal base": "normal",
    "normalvt": "normal", "texturenormal": "normal",
    "tex_bakednormal": "normal", "texnor": "normal",
    "normal vt": "normal", "bakednormalmap": "normal",
    "3 - baked normal": "normal", "base texture normal": "normal",
    "normal base map": "normal", "tex_nm": "normal",
    "texa_nm": "normal", "normal_tex": "normal",
    "n": "normal", "nm": "normal", "nm_1": "normal",
    "base_nm": "normal", "nrm": "normal", "t_nrm": "normal",
    "m1_t_nrm": "normal", "base nrm": "normal", "nrm base": "normal",
    "nrh": "normal", "mw_texturenormal": "normal",
    "texture a normal": "normal", "cliffnormal": "normal",
    "skin normal": "normal", "normal_main": "normal",
    "main_t_normal(b：sssmask)": "normal",
    "primary normal map": "normal", "orn": "normal",
    "nro_base_normal": "normal", "layer00_normal_tex": "normal",
    "tex_skinbase_n": "normal", "tex_core_layer_normal": "normal",
    "simple_normal_texture": "normal", "basenormal texture": "normal",
    "noh": "normal", "n/o/h": "normal", "nmh": "normal",
    "nwo": "normal", "normal_vt": "normal", "nrm_map": "normal",
    "normal - texture": "normal", "clothing normal": "normal",
    "normal [standard]": "normal", "ncd_mask": "normal",
    "normal map (packed)": "normal", "n2r(m)": "normal",
    "normal texture (n)": "normal",

    # ── SpecularMasks / ORM ──
    "trunk_specular": "orm", "packedtexture": "orm", "specularmasks": "orm",
    "specular": "orm", "specmap": "orm", "t_specular": "orm",
    "specular top": "orm", "specular side": "orm", "mg": "orm",
    "orm": "orm", "mrae": "orm", "mras": "orm", "mrao": "orm",
    "mra": "orm", "mrao_map": "orm", "mra a": "orm", "mrs": "orm",
    "lp": "orm", "lp_1": "orm", "base_lp": "orm", "base_r*": "orm",
    "mro_tex": "orm", "texturerma": "orm", "tex_multimask": "orm",
    "tex_multi": "orm", "texmrc": "orm", "texmra": "orm",
    "texrcn": "orm", "multimaskmap": "orm", "mro map": "orm",
    "mroa map": "orm", "mro": "orm", "base_sro": "orm",
    "base texture rmao": "orm", "skin srxo": "orm",
    "srxo_mask": "orm", "srxo": "orm", "sroa": "orm", "sr": "orm",
    "sro map": "orm", "srm": "orm", "sc_map": "orm",
    "ao": "orm", "pack": "orm", "pak": "orm", "t_pak": "orm",
    "m1_t_pak": "orm", "2 - packed mask (mrao)": "orm",
    "roughnessmaterial_mask": "orm", "packed tex": "orm",
    "packed texture": "orm", "cliff spec texture": "orm",
    "physicalmap": "orm", "kizokmap": "orm",
    "roughness_main": "orm", "main_t_mga": "orm",
    "tex_ch": "orm", "texa_ch": "orm", "armmap": "orm",
    "rem": "orm", "primary arme": "orm", "combinetex(hra)": "orm",
    "tpa_speccolortex": "orm", "tex_rme": "orm", "compvt": "orm",
    "metalroughocc_tex": "orm", "layer00_metalroughoccdp_tex": "orm",
    "tex_skinbase_orm": "orm", "tex_core_layer_ao": "orm",
    "rgb[ao/r/metallic]_texture": "orm",
    "simple_occlroughmet_texture": "orm", "p (nonevt)": "orm",
    "pack tex1": "orm", "casr": "orm", "roughness_vt": "orm",
    "occlusionroughnessmetallictexture": "orm",
    "clothing orm": "orm", "orc [standard]": "orm",
    "orme_tex": "orm", "roughness vt": "orm", "rmao vt": "orm",
    "mix(ao,rough,mask,metal)": "orm",

    # ── Emissive ──
    "emissive": "emissive", "emissivetexture": "emissive",
    "emissivecolortexture": "emissive", "emissivecolor": "emissive",
    "emissivemask": "emissive", "emmisivecolor_a": "emissive",
    "textureemissive": "emissive", "texem": "emissive",
    "main_t_emissive": "emissive", "pbremissivetex": "emissive",
}


# Colorspace defaults per channel (used when suffix detection fails)
_BUILTIN_COLORSPACE: Dict[str, str] = {
    "base_color": "sRGB", "emissive": "sRGB", "emission": "sRGB", "specular": "sRGB",
    "normal": "Non-Color", "roughness": "Non-Color",
    "metallic": "Non-Color", "ao": "Non-Color",
    "alpha": "Non-Color", "orm": "Non-Color",
    "height": "Non-Color", "subsurface": "sRGB",
    "clearcoat": "Non-Color", "detail_mask": "Non-Color",
    "thickness": "Non-Color", "other": "sRGB",
}

# Human-readable labels for each channel (shared by shader manager)
_CHANNEL_LABELS: Dict[str, str] = {
    "base_color": "Base Color", "normal": "Normal",
    "roughness": "Roughness", "metallic": "Metallic",
    "ao": "AO", "emissive": "Emission",
    "alpha": "Alpha", "orm": "ORM",
    "specular": "Specular", "height": "Height",
    "subsurface": "Subsurface", "clearcoat": "Clearcoat",
    "thickness": "Thickness", "other": "Other",
}


# ============================================================
# ChannelResolver
# ============================================================

class ChannelResolver:
    """Resolves MaterialManifest[] + GameProfile → ChannelAssignment[]."""

    def __init__(self, tex_dir: str, profile: Optional[GameProfile] = None,
                 content_dir: str = ""):
        self.tex_dir = tex_dir
        self.profile = profile
        self.content_dir = content_dir
        self._tex_index: Optional[Dict[str, List[str]]] = None

    def resolve(self, manifolds: List[MaterialManifest]) -> Dict[str, List[ChannelAssignment]]:
        """Resolve all manifests. Returns {material_name: [ChannelAssignment]}."""
        self._tex_index = self._scan_textures()
        result = {}
        for m in manifolds:
            if not m.is_active:
                continue
            assignments = self._resolve_one(m)
            if assignments:
                result[m.material_name] = assignments
        return result

    def _resolve_one(self, m: MaterialManifest) -> List[ChannelAssignment]:
        assignments = []
        seen_channels = set()

        for pname, tex_name in m.texture_params.items():
            ch = self._map_param_to_channel(pname)
            if not ch:
                continue
            # 1. Direct UE ObjectPath → filesystem (if available)
            tex_path = ""
            obj_path = m.texture_object_paths.get(pname, "")
            if obj_path and self.content_dir:
                tex_path = self._resolve_ue_path(obj_path)
            # 2. Fall back to texture index search
            if not tex_path:
                tex_path = self._find_texture(tex_name)
            # 3. Engine texture fallback
            if not tex_path:
                tex_path = self._resolve_engine_texture(tex_name, ch)
            cs = self._resolve_colorspace(ch, tex_name)

            # Channel-level is_normal_map flag
            normal_candidates = {"normal", "normalmap"}
            is_nm = ch.lower() in normal_candidates or \
                    any(kw in pname.lower() for kw in ("normal", "bump", "nm"))

            assignments.append(ChannelAssignment(
                channel=ch, texture_path=tex_path, ue_param=pname,
                colorspace=cs,
                source="manifest" if tex_path else "profile",
                score=1.0 if tex_path else 0.5,
                fallback_value=m.scalar_params.get(pname, 0.0),
                tool_groups=list(self.profile.tool_groups_default) if self.profile else [],
                is_normal_map=is_nm,
            ))
            if tex_path:
                seen_channels.add(ch)

        # ORM auto-detect and expand to individual ao/roughness/metallic
        _orm_suffixes = {"_orm": "decodeorm", "_arm": "decodearm", "_mrao": "decodemrao"}
        expanded = []
        for a in assignments:
            if a.channel == "orm" and a.texture_path and not a.texture_path.startswith("__engine__"):
                basename = os.path.basename(a.texture_path).lower()
                decode_type = "decodeorm"
                for suffix, dt in _orm_suffixes.items():
                    if suffix in basename:
                        decode_type = dt
                        break
                a.tool_groups = [decode_type]
                for sub_ch, sub_fallback in [("ao", 0.0), ("roughness", 0.5), ("metallic", 0.0)]:
                    if sub_ch not in seen_channels:
                        expanded.append(ChannelAssignment(
                            channel=sub_ch, texture_path=a.texture_path, ue_param=a.ue_param,
                            colorspace="Non-Color",
                            source="orm_expand", score=a.score * 0.9,
                            fallback_value=a.fallback_value or sub_fallback,
                            tool_groups=list(a.tool_groups),
                        ))
                        seen_channels.add(sub_ch)
        assignments.extend(expanded)

        # Scalar-only channels not covered by texture params
        for pname, value in m.scalar_params.items():
            if pname in m.texture_params:
                continue
            ch = self._map_param_to_channel(pname)
            if not ch:
                continue
            if ch not in seen_channels:
                normal_candidates = {"normal"}
                assignments.append(ChannelAssignment(
                    channel=ch, texture_path="", ue_param=pname,
                    colorspace=_BUILTIN_COLORSPACE.get(ch, "sRGB"),
                    source="fallback", score=0.0, fallback_value=value,
                    is_normal_map=ch.lower() in normal_candidates,
                ))
                seen_channels.add(ch)

        # Suffix-based fallback: if no texture for a known channel, scan filename patterns
        _missing_key_channels = {"base_color", "normal", "roughness", "metallic", "ao", "emissive", "alpha"}
        for ch in _missing_key_channels - seen_channels:
            candidate = self._find_texture_by_suffix(m.filter_token, ch)
            if candidate:
                cs = self._resolve_colorspace(ch, os.path.basename(candidate))
                normal_candidates = {"normal"}
                assignments.append(ChannelAssignment(
                    channel=ch, texture_path=candidate,
                    ue_param=f"auto:{ch}", colorspace=cs,
                    source="suffix", score=0.6,
                    is_normal_map=ch.lower() in normal_candidates,
                ))
                seen_channels.add(ch)

        return assignments

    # ------------------------------------------------------------------
    # Texture index
    # ------------------------------------------------------------------

    def _scan_textures(self) -> Dict[str, List[str]]:
        if not os.path.isdir(self.tex_dir):
            return {}
        index: Dict[str, List[str]] = {}
        for root, dirs, files in os.walk(self.tex_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.lower().endswith(_TEX_EXTENSIONS):
                    continue
                token = self._normalize(os.path.splitext(f)[0])
                path = os.path.join(root, f)
                index.setdefault(token, []).append(path)
        return index

    def _find_texture(self, tex_name: str) -> str:
        """Multi-pass texture matching: exact → token → partial."""
        if not self._tex_index:
            return ""
        norm = self._normalize(tex_name)
        # Pass 1: exact normalized match
        for token, paths in self._tex_index.items():
            if token == norm:
                return paths[0]
        # Pass 2: one contains the other
        for token, paths in self._tex_index.items():
            if norm in token or token in norm:
                for path in paths:
                    if self._normalize(os.path.splitext(os.path.basename(path))[0]) == norm:
                        return path
        # Pass 3: token-based (split by underscore, must share at least one non-trivial token)
        norm_tokens = set(t for t in norm.split("_") if len(t) > 1)
        best_match = ""
        best_score = 0
        for token, paths in self._tex_index.items():
            token_parts = set(t for t in token.split("_") if len(t) > 1)
            common = norm_tokens & token_parts
            if len(common) > best_score:
                best_score = len(common)
                best_match = paths[0]
        if best_score >= 2:
            return best_match
        return ""

    def _find_texture_by_suffix(self, filter_token: str, channel: str) -> str:
        """Scan texture index for files matching {filter_token}_{suffix} pattern.
        Prefers exact match over partial match."""
        if not self._tex_index or not filter_token:
            return ""
        norm_ft = self._normalize(filter_token)
        suffix_candidates = _CHANNEL_SUFFIXES.get(channel, [])
        best_exact = ""
        best_partial = ""
        for suffix in suffix_candidates:
            suffix_norm = self._normalize(suffix)
            for token, paths in self._tex_index.items():
                token_clean = token.lstrip("t_").lstrip("t")
                expected = f"{norm_ft}{suffix_norm}"
                if token == expected or token_clean == expected:
                    best_exact = paths[0]
                    break
                if len(suffix_norm) <= 2:
                    ft_found = norm_ft in token
                    sf_found = suffix_norm.lstrip('_') in token.replace('-', '_').split('_')
                else:
                    ft_found = norm_ft in token
                    sf_found = suffix_norm in token
                if ft_found and sf_found and not best_partial:
                    best_partial = paths[0]
            if best_exact:
                break
        return best_exact or best_partial

    @staticmethod
    def _normalize(s: str) -> str:
        return "".join(c for c in s.lower() if c.isalnum() or c in ("_", "-"))

    # ------------------------------------------------------------------
    # Parameter mapping
    # ------------------------------------------------------------------

    def _map_param_to_channel(self, pname: str) -> str:
        """Map a UE parameter name to a preset channel name.
        Returns "other" for unmapped params (still imported, not connected)."""
        key = pname.lower().strip()

        # 1. GameProfile exact match
        if self.profile and key in self.profile.param_mapping:
            mapped = self.profile.param_mapping[key]
            return mapped if mapped else "other"

        # 2. CUE4Parse CMaterialParams2 exact match (FModel-authoritative)
        if key in _CUE4PARSE_MAP:
            return _CUE4PARSE_MAP[key]

        # 3. GameProfile substring match
        if self.profile:
            for pk, pv in self.profile.param_mapping.items():
                if pk.lower() in key or key in pk.lower():
                    return pv if pv else "other"

        # 4. Built-in keyword matching (longer keywords first)
        for kw, ch in _BUILTIN_MAPPING:
            match = False
            if len(kw) <= 2:
                # Short keywords: must be a standalone underscore-delimited token
                tokens = key.replace('-', '_').split('_')
                match = kw in tokens
            else:
                match = kw in key
            if match:
                return ch

        return "other"

    def _resolve_ue_path(self, ue_path: str) -> str:
        """Convert UE ObjectPath → filesystem. Try common texture extensions.
        Handles: /Game/X/Y, Project/Content/X/Y, Project/X/Y."""
        if not self.content_dir or not ue_path:
            return ""
        path = ue_path.replace('\\', '/')
        path = re.sub(r'\.\d+$', '', path) if re.search(r'\.\d+$', path) else path
        # Strip UE ObjectName suffix: 'Pkg.ObjName' → 'Pkg' when suffix mirrors basename
        parts = path.rsplit('/', 1)
        if len(parts) == 2 and '.' in parts[1]:
            base, ext = parts[1].rsplit('.', 1)
            if base and ext and base.lower().endswith(ext.lower()):
                parts[1] = base
                path = '/'.join(parts)

        if path.startswith('/Game/'):
            base = os.path.join(self.content_dir, path[6:])
        elif '/' in path:
            segs = path.split('/')
            if len(segs) > 2 and segs[1].lower() == 'content':
                base = os.path.join(self.content_dir, '/'.join(segs[2:]))
            else:
                base = os.path.join(os.path.dirname(self.content_dir), '/'.join(segs[1:]))
        else:
            return ""

        for ext in _TEX_EXTENSIONS:
            candidate = base + ext
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _resolve_colorspace(self, channel: str, tex_name: str) -> str:
        """Determine colorspace: channel default > GameProfile > suffix.
        Channel from JSON manifest is authoritative; suffix only corrects 'other'."""
        # 1. GameProfile colorspace rules (highest priority, per-game override)
        if self.profile and self.profile.colorspace_rules and tex_name:
            basename = os.path.basename(tex_name).lower()
            for suffix, cs in self.profile.colorspace_rules.items():
                if suffix.lower() in basename:
                    return cs

        # 2. Channel-based default (from manifest — most trustworthy)
        cs = _BUILTIN_COLORSPACE.get(channel)
        if cs:
            return cs

        # 3. Suffix-based detection (fallback for "other" / unlisted channels)
        basename = os.path.basename(tex_name).lower() if tex_name else ""
        for suffix, cs in _SUFFIX_COLORSPACE:
            if suffix in basename:
                return cs

        return "sRGB"

    @staticmethod
    def _resolve_engine_texture(tex_name: str, channel: str) -> str:
        """Map engine-internal texture names (Black, White, DefaultNormal...)
        to synthetic paths that Phase 3 interprets as constant RGB nodes."""
        key = tex_name.lower().strip()
        if key in ("black",):
            return "__engine__:0,0,0,1"
        if key in ("white", "defaultwhite"):
            return "__engine__:1,1,1,1"
        if key in ("grey", "gray"):
            return "__engine__:0.5,0.5,0.5,1"
        if key in ("defaultnormal", "defaultnormalmap", "defaultnorm"):
            return "__engine__:0.5,0.5,1,1__normal"
        if key in ("defaultdiffuse", "default"):
            return "__engine__:0.5,0.5,0.5,1"
        return ""
