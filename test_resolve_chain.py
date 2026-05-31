#!/usr/bin/env python3
"""FModel Material Resolve Chain Test Script - standalone, no Blender dependency.
Usage:
  python test_resolve_chain.py <model.uemodel> [depth]          # table
  python test_resolve_chain.py --batch <file.txt> [depth]       # batch
  python test_resolve_chain.py --verbose <model> [depth]        # per-texture
  python test_resolve_chain.py --summary <model> [depth]        # one-line
  python test_resolve_chain.py --auto [depth_max] <model>       # auto-detect depth
  python test_resolve_chain.py --no-input ...                   # skip prompt
"""

import json, os, re, sys
import importlib.util as _iu

_AD = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _AD)

def _lm(n, fp):
    s = _iu.spec_from_file_location(n, fp)
    m = _iu.module_from_spec(s)
    sys.modules[n] = m
    s.loader.exec_module(m)
    return m

_M = _lm("Universal_tools.material.manifest_builder",
         os.path.join(_AD, "Universal_tools", "material", "manifest_builder.py"))
_C = _lm("Universal_tools.material.channel_resolver",
         os.path.join(_AD, "Universal_tools", "material", "channel_resolver.py"))

ManifestBuilder, ChannelResolver, GameProfile = _M.ManifestBuilder, _C.ChannelResolver, _C.GameProfile


def _auto_depth(mp, max_d=10):
    """Find minimal depth reaching a dir with Material/ and Texture/ (or Content/)."""
    r = os.path.dirname(os.path.abspath(mp))
    for d in range(max_d + 1):
        has_mt = os.path.isdir(os.path.join(r, "Material")) and os.path.isdir(os.path.join(r, "Texture"))
        has_ct = os.path.basename(r).lower() == "content"
        if has_mt or has_ct:
            return d
        p = os.path.dirname(r)
        if p == r: break
        r = p
    return 3


def _load_profile():
    pd = os.path.join(_AD, "Shaders", "GameProfiles")
    if os.path.isdir(pd):
        for e in sorted(os.listdir(pd)):
            if e.endswith(".json"):
                p = GameProfile.load(os.path.join(pd, e))
                if p: return p
    return None


def _resolve_single(mp, depth, profile, verbose=False, miss_detail=False):
    if not mp.lower().endswith('.uemodel'): return None, []
    mtx = {"slots":0,"active":0,"tex":0,"engine":0,"miss":0,"mats":0,"diag":"OK"}
    dl = []
    jp = os.path.splitext(mp)[0] + ".json"
    if not os.path.exists(jp): mtx["diag"]="NO_JSON"; dl.append(f"NO_JSON:{jp}"); return mtx, dl

    b = ManifestBuilder(mp, search_depth=depth)
    ms = b.discover()
    act = [m for m in ms if m.is_active]
    mtx["slots"], mtx["active"] = len(ms), len(act)
    if not act: mtx["diag"]="NO_ACTIVE"; return mtx, dl
    if not b.content_dir: dl.append("NO_CONTENT"); mtx["diag"]="NO_CONTENT"

    r = ChannelResolver(b.project_dir, profile, content_dir=b.content_dir)
    asgn = r.resolve(ms)
    mtx["mats"] = len(asgn)
    if not asgn: mtx["diag"]="NO_ASSIGNMENTS"; return mtx, dl

    # Per-channel source labels for verbose output
    _src_labels = {"manifest": "MANIFEST", "profile": "PROFILE", "suffix": "SUFFIX",
                   "fallback": "FALLBACK", "orm_expand": "ORM", "auto": "AUTO"}

    if verbose:
        dl.append(f"  content_dir = {b.content_dir or '(none)'}")
        dl.append(f"  tex_dir     = {b.project_dir or '(none)'}")

    for mn, cl in asgn.items():
        for a in cl:
            if a.texture_path.startswith("__engine__"):
                mtx["engine"] += 1
            elif a.texture_path:
                mtx["tex"] += 1
                sl = _src_labels.get(a.source, a.source[:8].upper())
                if verbose:
                    dl.append(f"  {sl:9} [{mn}] {a.channel:12} -> {os.path.basename(a.texture_path)}")
            else:
                mtx["miss"] += 1
                if verbose:
                    dl.append(f"  MISS     [{mn}] {a.channel:12} <- {a.ue_param}")

    if mtx["tex"] == 0 and mtx["engine"] == 0:
        mtx["diag"] = "NO_TEXTURES" if mtx["active"] > 0 else mtx["diag"]

    # MISS breakdown
    if miss_detail and mtx["miss"] > 0:
        miss_ch = {}
        for mn, cl in asgn.items():
            for a in cl:
                if not a.texture_path:
                    key = f"{mn}:{a.channel}"
                    miss_ch[key] = miss_ch.get(key, 0) + 1
        dl.append(f"  MISS: {len(miss_ch)} unique ({mtx['miss']} total)")
        for k, v in sorted(miss_ch.items(), key=lambda x: -x[1]):
            dl.append(f"    {k} x{v}")

    return mtx, dl


_FLAGS = {"--summary", "--verbose", "-v", "--quiet", "--no-input", "--miss",
           "--batch", "--auto", "--help", "-h"}
_SHORT_MAP = {"-v": "--verbose", "-h": "--help"}

if __name__ == "__main__":
    # Normalize short flags
    args = [_SHORT_MAP.get(a, a) for a in sys.argv[1:]]

    summary_only = "--summary" in args
    verbose = "--verbose" in args
    quiet = "--quiet" in args
    no_input = "--no-input" in args
    batch_mode = "--batch" in args
    auto_depth = "--auto" in args
    miss_detail = "--miss" in args

    # Parse depth
    sd = 2
    for a in args:
        if a.isdigit() or (a.startswith('-') and a[1:].isdigit()):
            sd = int(a.lstrip('-'))
            break

    profile = _load_profile()
    mps = []

    if batch_mode:
        try: bi = args.index("--batch"); bf = args[bi+1]
        except: bf = ""
        if bf and os.path.isfile(bf):
            with open(bf, 'r', encoding='utf-8') as f:
                mps = [l.strip() for l in f if l.strip() and not l.strip().startswith('#')]
    else:
        pa = [a for a in args if not a.startswith('-') and not a.isdigit() and a not in _FLAGS
              and a != (args[args.index("--batch")+1] if "--batch" in args and args.index("--batch")+1 < len(args) else "")]
        if pa:
            mps = [pa[0]]
        else:
            # Default: find any .uemodel in Fmodel Export/
            export_dir = os.path.join(_AD, "Fmodel Export")
            if os.path.isdir(export_dir):
                for root, dirs, files in os.walk(export_dir):
                    for f in files:
                        if f.lower().endswith('.uemodel'):
                            mps = [os.path.join(root, f)]
                            break
                    if mps:
                        break

    if not mps:
        print("Usage: python test_resolve_chain.py <model.uemodel> [depth] [flags]")
        print("  --summary     One-line per model")
        print("  --verbose     Per-texture source tracing (MANIFEST/SUFFIX/FALLBACK)")
        print("  --miss        Per-material MISS channel breakdown")
        print("  --batch FILE  Read models from file")
        print("  --auto        Auto-detect search depth")
        print("  --no-input    Skip exit prompt")
        print("\nNo .uemodel found in Fmodel Export/")
        sys.exit(1)

    hdr = False
    for mp in mps:
        if not os.path.exists(mp):
            if not quiet: print(f"# NOT_FOUND: {mp}")
            continue

        sdi = _auto_depth(mp, max_d=sd) if auto_depth else sd

        if summary_only:
            mt, _ = _resolve_single(mp, sdi, profile, miss_detail=miss_detail)
            if mt: print(f"{os.path.basename(mp)}|slots={mt['slots']}|active={mt['active']}|tex={mt['tex']}|engine={mt['engine']}|miss={mt['miss']}|mats={mt['mats']}|{mt['diag']}")
        elif verbose:
            if not hdr: print(f"  depth={sdi}  profile={profile.game_id if profile else 'builtin'}"); hdr = True
            print(f"\n-- {mp}")
            mt, dl = _resolve_single(mp, sdi, profile, verbose=True, miss_detail=miss_detail)
            if mt:
                for d in dl: print(d)
                print(f"-- {os.path.basename(mp)}|slots={mt['slots']}|active={mt['active']}|tex={mt['tex']}|engine={mt['engine']}|miss={mt['miss']}|mats={mt['mats']}|{mt['diag']}")
        else:
            if not hdr:
                print(f"{'MODEL':<40} {'SLOTS':>5} {'ACT':>4} {'TEX':>4} {'ENG':>4} {'MISS':>5} {'MATS':>4} {'DIAG'}")
                print("-" * 78)
                hdr = True
            mt, _ = _resolve_single(mp, sdi, profile, miss_detail=miss_detail)
            if mt:
                nm = os.path.basename(mp)
                print(f"{nm:<40} {mt['slots']:>5} {mt['active']:>4} {mt['tex']:>4} {mt['engine']:>4} {mt['miss']:>5} {mt['mats']:>4} {mt['diag']}")

    if not no_input:
        try: input("\nPress Enter...")
        except: pass
