# FModel_Tools/Universal_tools/material/manifest_builder.py
# Phase 1: Asset Discovery — pure JSON parsing, no Blender dependency, no guessing

import json
import os
import re
from dataclasses import dataclass, field
from typing import Optional, List


# ============================================================
# Data Structures
# ============================================================
def _resolve_search_root(model_filepath: str, search_depth: int) -> str:
    """从模型文件向上回溯，找到同时包含 Material/ 和 Texture/ 的目录。"""
    root = os.path.dirname(os.path.abspath(model_filepath))
    for _ in range(search_depth + 1):
        if os.path.isdir(os.path.join(root, "Material")) and \
           os.path.isdir(os.path.join(root, "Texture")):
            return root
        parent = os.path.dirname(root)
        if parent == root:
            break
        root = parent
    root = os.path.dirname(os.path.abspath(model_filepath))
    for _ in range(search_depth):
        parent = os.path.dirname(root)
        if parent == root:
            break
        root = parent
    return root


@dataclass
class MaterialManifest:
    """Parsed material data from model JSON + material instance JSON chain."""
    material_name: str           # e.g. "MI_shizuku_Hair"
    slot_name: str               # e.g. "m_hair"
    texture_params: dict = field(default_factory=dict)  # {ue_param: tex_name}
    texture_object_paths: dict = field(default_factory=dict)  # {ue_param: "/Game/..."}
    scalar_params: dict = field(default_factory=dict)   # {ue_param: value}
    vector_params: dict = field(default_factory=dict)   # {ue_param: (r,g,b,a)}
    parent_chain: list = field(default_factory=list)     # [mi_name, parent, ...]
    mi_json_path: str = ""       # path to the material instance JSON
    is_active: bool = True       # False if Material=null (unused slot)
    filter_token: str = ""       # normalized token for filtering


# ============================================================
# Manifest Builder
# ============================================================

class ManifestBuilder:
    """Builds MaterialManifest[] from a FModel export directory."""

    def __init__(self, model_path: str, search_depth: int = 2):
        self.model_path = model_path if model_path.lower().endswith('.uemodel') else ""
        self.search_depth = search_depth
        self.content_dir = self._find_content_dir() if self.model_path else ""
        # Keep project_dir for Phase 1b fallback and backward compat
        self.project_dir = self._find_project_root() if self.model_path else ""
        self.tex_dir = os.path.join(self.project_dir, "Texture") if self.project_dir else ""
        self.mat_dir = os.path.join(self.project_dir, "Material") if self.project_dir else ""
        self.model_json_data: list = []
        self._ue_cache: set = set()  # track resolved UE paths to avoid re-checking

    def _find_content_dir(self) -> str:
        """Walk up from model file to find 'Content/' directory (UE /Game/ root)."""
        root = os.path.dirname(os.path.abspath(self.model_path))
        for _ in range(12):  # reasonable max depth
            if os.path.basename(root).lower() == "content":
                return root
            parent = os.path.dirname(root)
            if parent == root:
                break
            root = parent
        return ""

    def _find_project_root(self) -> str:
        """从模型文件向上回溯，找到同时包含 Material/ 和 Texture/ 的目录。"""
        return _resolve_search_root(self.model_path, self.search_depth)

    def _ue_path_to_disk(self, ue_path: str) -> str:
        """Convert UE ObjectPath to filesystem path. Handles 3 formats:
        - '/Game/X/Y/Z.0' → '{content_dir}/X/Y/Z.{ext}'
        - 'Project/Content/X/Y/Z.0' → '{content_dir}/X/Y/Z.{ext}'
        - 'Project/X/Y/Z.0' → '{parent_of_content}/Project/X/Y/Z.{ext}'"""
        if not self.content_dir:
            return ""
        path = ue_path.replace('\\', '/')
        path = re.sub(r'\.\d+$', '', path) if re.search(r'\.\d+$', path) else path
        # Strip UE ObjectName suffix: 'Pkg.ObjectName' → 'Pkg'
        # Matches pattern where the filename duplicates after the dot
        # e.g. 'amelia_body_mat_Base_Color.amelia_body_mat_Base_Color' → strip
        # but NOT 'file.png' (different after dot) or 'file.0' (numeric version)
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
                # ProjectName/Content/X/Y → strip Project + Content, use rest
                base = os.path.join(self.content_dir, '/'.join(segs[2:]))
            else:
                # ProjectName/X/Y → strip Project, join under parent of content
                base = os.path.join(os.path.dirname(self.content_dir), '/'.join(segs[1:]))
        else:
            return ""

        return self._try_extensions(base)

    def _try_extensions(self, base_path: str) -> str:
        """Try .json first, then texture extensions on a base path."""
        candidate = base_path + ".json"
        if os.path.isfile(candidate):
            return candidate
        for ext in ('.png', '.tga', '.dds', '.jpg', '.jpeg', '.bmp', '.exr', '.tiff', '.tif', '.webp'):
            candidate = base_path + ext
            if os.path.isfile(candidate):
                return candidate
        return ""

    def _find_mi_json(self, mi_name: str, ue_path: str = "") -> str:
        """Locate MI JSON file. Tries: 1) direct UE path → disk, 2) mat_dir search."""
        # 1. Direct UE ObjectPath resolution
        if ue_path and self.content_dir:
            direct = self._ue_path_to_disk(ue_path)
            if direct:
                return direct
        # 2. Search mat_dir
        if self.mat_dir:
            direct = os.path.join(self.mat_dir, f"{mi_name}.json")
            if os.path.exists(direct):
                return direct
            for root, dirs, files in os.walk(self.mat_dir):
                for f in files:
                    if f == f"{mi_name}.json":
                        return os.path.join(root, f)
        return ""

    def discover(self) -> List[MaterialManifest]:
        """Entry point: parse model JSON and return all material manifests."""
        if not self.model_path or not self._load_model_json():
            return []
        manifests = []
        entries = self._extract_skeletal_materials()
        for entry in entries:
            slot_name = entry.get("MaterialSlotName", "")
            material = entry.get("Material")
            if material is None:
                manifests.append(MaterialManifest(
                    material_name=slot_name, slot_name=slot_name, is_active=False,
                ))
                continue
            mi_name = self._extract_mi_name(material)
            if not mi_name:
                manifests.append(MaterialManifest(
                    material_name=slot_name, slot_name=slot_name, is_active=False,
                ))
                continue
            mi_object_path = material.get("ObjectPath", "")
            manifold = MaterialManifest(
                material_name=mi_name, slot_name=slot_name,
                filter_token=mi_name, is_active=True,
            )
            self._walk_material_chain(manifold, mi_object_path=mi_object_path)
            manifests.append(manifold)
        return manifests

    def _load_model_json(self) -> bool:
        json_path = os.path.splitext(self.model_path)[0] + ".json"
        if not os.path.exists(json_path):
            return False
        try:
            with open(json_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                self.model_json_data = json.load(f)
            return True
        except (json.JSONDecodeError, IOError):
            return False

    def _extract_skeletal_materials(self) -> list:
        for item in self.model_json_data:
            if isinstance(item, dict) and item.get("Type") == "SkeletalMesh":
                return item.get("SkeletalMaterials", [])
        return []

    @staticmethod
    def _extract_mi_name(material: dict) -> str:
        obj_path = material.get("ObjectPath", "")
        obj_name = material.get("ObjectName", "")
        if obj_path:
            parts = obj_path.replace('\\', '/').split('/')
            mi = parts[-1].rsplit('.', 1)[0] if parts else ""
            if mi:
                return mi
        if obj_name:
            m = re.search(r"'([^']*)'", obj_name)
            if m:
                return m.group(1)
        return ""

    @staticmethod
    def _parse_texture_params(props: dict) -> tuple:
        """Returns (name_dict, path_dict) from TextureParameterValues."""
        names = {}
        paths = {}
        for tv in props.get("TextureParameterValues", []):
            pname = tv.get("ParameterInfo", {}).get("Name", "")
            pval = tv.get("ParameterValue", {})
            tex_ref = pval.get("ObjectName", "")
            obj_path = pval.get("ObjectPath", "")
            if pname and tex_ref:
                m = re.search(r"'([^']*)'", tex_ref)
                if m:
                    names[pname] = m.group(1)
            if pname and obj_path:
                paths[pname] = obj_path
        return names, paths

    @staticmethod
    def _parse_scalar_params(props: dict) -> dict:
        params = {}
        for sv in props.get("ScalarParameterValues", []):
            pname = sv.get("ParameterInfo", {}).get("Name", "")
            pval = sv.get("ParameterValue")
            if pname and pval is not None:
                params[pname] = pval
        return params

    @staticmethod
    def _parse_vector_params(props: dict) -> dict:
        params = {}
        for sv in props.get("VectorParameterValues", []):
            pname = sv.get("ParameterInfo", {}).get("Name", "")
            pval = sv.get("ParameterValue", {})
            if pname and isinstance(pval, dict):
                r = pval.get("R", 0)
                g = pval.get("G", 0)
                b = pval.get("B", 0)
                a = pval.get("A", 0)
                params[pname] = (r, g, b, a)
        return params

    # ------------------------------------------------------------------
    # Material chain walking
    # ------------------------------------------------------------------

    def _load_mi_data(self, mi_name: str, ue_path: str = "") -> Optional[dict]:
        path = self._find_mi_json(mi_name, ue_path)
        if not path:
            return None
        try:
            with open(path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
        # Format A: list of objects with "Properties" key
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("Type") in ("MaterialInstanceConstant", "Material"):
                    return item
        # Format A fallback: single dict with "Properties" key
        if isinstance(data, dict) and "Properties" in data:
            return data
        # Format B: flat dict with "Textures"/"Parameters" at top level
        if isinstance(data, dict) and "Textures" in data:
            props = {}
            tex_vals = []
            for pname, obj_path_or_name in data.get("Textures", {}).items():
                raw_basename = os.path.basename(obj_path_or_name)
                # Strip UE ObjectName suffix: 'Pkg.ObjName' → 'Pkg'
                if '.' in raw_basename:
                    base, ext = raw_basename.rsplit('.', 1)
                    if base and ext and base.lower().endswith(ext.lower()):
                        raw_basename = base
                tex_vals.append({
                    "ParameterInfo": {"Name": pname},
                    "ParameterValue": {
                        "ObjectName": f"Texture2D'{raw_basename}'",
                        "ObjectPath": obj_path_or_name,
                    }
                })
            props["TextureParameterValues"] = tex_vals
            sca_vals = []
            for pname, pval in data.get("Parameters", {}).items():
                sca_vals.append({"ParameterInfo": {"Name": pname}, "ParameterValue": pval})
            props["ScalarParameterValues"] = sca_vals
            result = {"Type": "MaterialInstanceConstant", "Properties": props}
            # Preserve self ObjectPath for chain debugging
            if ue_path:
                result["ObjectPath"] = ue_path
            return result
        return None

    def _walk_material_chain(self, manifold: MaterialManifest, max_depth: int = 5,
                             mi_object_path: str = ""):
        """Walk parent material chain collecting texture/scalar/vector params."""
        current_name = manifold.material_name
        tex = {}
        tex_paths = {}
        scalar = {}
        vector = {}
        chain = []

        for depth in range(max_depth):
            if not current_name:
                break
            # First iteration: try direct UE path for initial MI
            mi_path = ""
            if depth == 0 and mi_object_path:
                mi_path = self._ue_path_to_disk(mi_object_path)
            mi_data = self._load_mi_data(current_name, ue_path=mi_object_path if depth == 0 else "")
            if not mi_data:
                break

            props = mi_data.get("Properties", {})
            new_tex, new_tex_paths = self._parse_texture_params(props)

            # Detect empty MI with no parent linkage — mark inactive for Phase 1b
            if depth == 0 and not new_tex and not props.get("Parent", {}).get("ObjectPath"):
                if manifold.texture_params:
                    continue  # already has textures from previous iterations
                print(f"[FModel] EMPTY_MI: '{current_name}' 无贴图且无父材质，标记为不活跃")
                manifold.is_active = False
                return
            new_scalar = self._parse_scalar_params(props)
            new_vector = self._parse_vector_params(props)
            # Child overrides parent
            new_tex.update(tex)
            new_scalar.update(scalar)
            new_vector.update(vector)
            new_tex_paths.update(tex_paths)
            tex = new_tex
            tex_paths = new_tex_paths
            scalar = new_scalar
            vector = new_vector

            chain.append(current_name)
            if not manifold.mi_json_path:
                mi_data_obj_path = mi_data.get("ObjectPath", "")
                manifold.mi_json_path = self._find_mi_json(current_name, mi_data_obj_path)

            # Follow parent
            parent = props.get("Parent", {})
            parent_path = parent.get("ObjectPath", "")
            current_name = self._extract_mi_name(parent) if parent else ""
            if not current_name:
                break

        manifold.texture_params = tex
        manifold.texture_object_paths = tex_paths
        manifold.scalar_params = scalar
        manifold.vector_params = vector
        manifold.parent_chain = chain

    # ==================================================================
    # Heuristic Phase 1b: JSON-less material name → texture matching
    # ==================================================================

    _HEURISTIC_PREFIXES = ('mi_', 'm_', 'mat_', 'material_')

    @staticmethod
    def _extract_tokens(name: str) -> list:
        """Extract semantic tokens from a material or texture name.
        Tries stripping common prefixes first; falls back to raw tokens
        if stripping leaves nothing (e.g. 'Mat_1' → keep 'mat')."""
        name = name.lower()
        tokens = re.split(r'[_\s\-\.]+', name)
        # Raw: keep tokens with len > 1 and not purely numeric
        raw = [t for t in tokens if len(t) > 1 and not t.isdigit()]

        for prefix in ManifestBuilder._HEURISTIC_PREFIXES:
            if name.startswith(prefix):
                stripped = name[len(prefix):]
                stripped_tokens = re.split(r'[_\s\-\.]+', stripped)
                stripped_tokens = [t for t in stripped_tokens if len(t) > 2 and not t.isdigit()]
                if stripped_tokens:
                    return stripped_tokens
                break
        return raw

    @staticmethod
    def is_generic_name(name: str) -> bool:
        """Returns True if the material name has no useful semantic tokens."""
        return len(ManifestBuilder._extract_tokens(name)) == 0

    @staticmethod
    def are_all_generic(names: list) -> bool:
        """Returns True if ALL names are auto-generated (no semantic value)."""
        if not names:
            return True
        return all(ManifestBuilder.is_generic_name(n) for n in names)

    @classmethod
    def discover_heuristic(cls, slot_names: list, tex_dir: str) -> List[MaterialManifest]:
        """Phase 1b: Scan texture directory and match to material slots by token
        overlap when no model JSON is available.

        Matching strategy:
        1. Index all textures, extract tokens and channel by suffix
        2. For each slot: intersect slot tokens with texture tokens
        3. Accept match if ≥1 token overlap AND texture has a channel suffix
        4. Lone unmatched textures with no suffix → default base_color
        """
        from .channel_resolver import _CHANNEL_SUFFIXES, _TEX_EXTENSIONS

        if not tex_dir or not os.path.isdir(tex_dir):
            return []

        tex_files = {}
        for root, dirs, files in os.walk(tex_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for f in files:
                if not f.lower().endswith(_TEX_EXTENSIONS):
                    continue
                name_lower = f.lower()
                basename_raw = os.path.splitext(f)[0]
                # Split on underscore, hyphen, whitespace, AND camelCase
                tokens = set(re.split(r'[_\s\-]+|(?<=[a-z])(?=[A-Z])', basename_raw))
                tokens = {t.lower() for t in tokens if len(t) > 1 and not t.isdigit()}
                ch = cls._guess_channel_from_suffix(name_lower, tokens, _CHANNEL_SUFFIXES)
                tex_files[name_lower] = {
                    'path': os.path.join(root, f),
                    'tokens': tokens,
                    'channel': ch,
                }

        if not tex_files:
            return []

        manifests = []
        for slot_name in slot_names:
            slot_tokens = set(cls._extract_tokens(slot_name))
            if not slot_tokens:
                manifests.append(MaterialManifest(
                    material_name=slot_name, slot_name=slot_name,
                    filter_token=slot_name, is_active=False,
                ))
                continue

            matched = {}       # {channel: (path, token_set)}
            unmatched = []     # [{path, tokens}] — no suffix detected
            used_fnames = []   # deferred removal from tex_files for dedup
            manifold = MaterialManifest(
                material_name=slot_name, slot_name=slot_name,
                filter_token=slot_name, is_active=True,
            )

            for fname, info in tex_files.items():
                common = slot_tokens & info['tokens']
                if not common:
                    continue
                if info['channel']:
                    existing = matched.get(info['channel'])
                    if existing is None or len(common) > len(existing[1]):
                        matched[info['channel']] = (info['path'], common)
                        tex_stem = os.path.splitext(os.path.basename(info['path']))[0]
                        manifold.texture_params[f"auto:{info['channel']}"] = tex_stem
                    used_fnames.append(fname)
                else:
                    unmatched.append({'path': info['path'], 'common': common})
                    used_fnames.append(fname)

            # Dedup: remove matched textures from pool so next slots can't steal
            for fname in used_fnames:
                if fname in tex_files:
                    del tex_files[fname]

            # Fallback: if exactly one unmatched texture with no suffix
            # and no other textures matched this slot, assume base_color
            if not matched and len(unmatched) == 1:
                u = unmatched[0]
                matched['base_color'] = (u['path'], u['common'])
                tex_stem = os.path.splitext(os.path.basename(u['path']))[0]
                manifold.texture_params["auto:base_color"] = tex_stem

            if matched:
                manifests.append(manifold)
            else:
                manifold.is_active = False
                manifests.append(manifold)

        return manifests

    @staticmethod
    def _guess_channel_from_suffix(filename_lower: str, tokens: set, suffix_map: dict) -> str:
        """Determine channel from filename tokens AND suffix patterns.
        Supports suffix naming (T_Body_D), mid-name naming (T_diffuse_Body),
        and camelCase naming (BodyColor). Longer match wins."""
        basename = filename_lower
        scored = []
        for ch, patterns in suffix_map.items():
            for pat in patterns:
                token = pat.lstrip("_")
                score = 0
                if basename.endswith(pat):
                    score = len(pat) * 2  # suffix priority
                elif token in tokens:
                    score = len(token)
                if score > 0:
                    scored.append((score, ch))
        if scored:
            scored.sort(reverse=True)
            return scored[0][1]
        return ""
