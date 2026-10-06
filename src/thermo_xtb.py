# -*- coding: utf-8 -*-
r"""
xTB 热力学模块：用 GFN2-xTB + GBSA 水相溶剂化计算分子自由能 G°，
用于反应 ΔG 筛选。

流程：SMILES -> RDKit 多构象 -> MMFF 选最低 -> xTB --ohess -> G°(T)
反应 ΔG = ΣG(产物) - ΣG(反应物)，原子守恒时绝对参考自动抵消。

缓存：data/xtb_cache/<InChIKey>.json
"""
import subprocess
import tempfile
import time
import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple

from rdkit import Chem
from rdkit.Chem import AllChem

XTB = Path(r"D:\TCMAI\tools\xtb\xtb-6.7.1\bin\xtb.exe")
CACHE_DIR = Path(r"D:\TCMAI\data\xtb_cache")
HARTREE_TO_KJ = 2625.5


def _inchikey(smiles: str) -> Optional[str]:
    mol = Chem.MolFromSmiles(smiles)
    return Chem.MolToInchiKey(mol) if mol else None


def _make_xyz(smiles: str, n_conf: int = 5) -> Optional[str]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    cids = list(AllChem.EmbedMultipleConfs(mol, numConfs=n_conf, params=params))
    if not cids:
        return None

    if len(cids) > 1:
        AllChem.MMFFOptimizeMoleculeConfs(mol, numThreads=0)
        props = AllChem.MMFFGetMoleculeProperties(mol)
        energies = []
        for cid in cids:
            ff = AllChem.MMFFGetMoleculeForceField(mol, props, confId=cid)
            energies.append(ff.CalcEnergy() if ff else float("inf"))
        best = cids[energies.index(min(energies))]
    else:
        AllChem.MMFFOptimizeMolecule(mol, confId=cids[0])
        best = cids[0]

    conf = mol.GetConformer(best)
    lines = [str(mol.GetNumAtoms()), smiles]
    for i, atom in enumerate(mol.GetAtoms()):
        p = conf.GetAtomPosition(i)
        lines.append(f"{atom.GetSymbol():2s} {p.x:14.8f} {p.y:14.8f} {p.z:14.8f}")
    return "\n".join(lines) + "\n"


def _run_xtb(xyz: str) -> Tuple[Optional[float], float]:
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "mol.xyz").write_text(xyz, encoding="utf-8")
        t0 = time.time()
        try:
            r = subprocess.run(
                [str(XTB), "mol.xyz", "--ohess", "--gbsa", "water"],
                cwd=td, capture_output=True, timeout=3600,
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return None, time.time() - t0
        elapsed = time.time() - t0
        if r.returncode != 0:
            return None, elapsed
        m = re.search(r"TOTAL FREE ENERGY\s+(-?\d+\.\d+)\s*Eh",
                      (r.stdout or "") + (r.stderr or ""))
        return (float(m.group(1)) if m else None), elapsed


def get_g(smiles: str, n_conf: int = 5, verbose: bool = False) -> Optional[float]:
    """分子 G°(T)，单位 Hartree。带缓存。"""
    key = _inchikey(smiles)
    if not key:
        return None
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cf = CACHE_DIR / f"{key}.json"
    if cf.exists():
        return json.loads(cf.read_text())["g"]

    xyz = _make_xyz(smiles, n_conf=n_conf)
    if not xyz:
        if verbose:
            print(f"  [x] 无法生成 3D: {smiles}")
        return None
    g, sec = _run_xtb(xyz)
    if g is None:
        if verbose:
            print(f"  [x] xTB 失败: {smiles}")
        return None
    cf.write_text(json.dumps({"smiles": smiles, "g": g, "sec": sec}))
    if verbose:
        print(f"  [ok] {smiles[:40]:40s} G={g:.6f} Eh  ({sec:.1f}s)")
    return g


def _formula(smiles: str) -> Optional[str]:
    mol = Chem.MolFromSmiles(smiles)
    return Chem.rdMolDescriptors.CalcMolFormula(mol) if mol else None


def _balanced(reactants: List[str], products: List[str]) -> bool:
    """原子守恒检查（用分子式比对，简版：只比总 C/H/O/N/S 计数）"""
    from collections import Counter

    def parse(f):
        c = Counter()
        for elem, n in re.findall(r"([A-Z][a-z]?)(\d*)", f):
            if elem:
                c[elem] += int(n) if n else 1
        return c

    rc, pc = Counter(), Counter()
    for s in reactants:
        f = _formula(s)
        if not f:
            return False
        rc += parse(f)
    for s in products:
        f = _formula(s)
        if not f:
            return False
        pc += parse(f)
    return rc == pc


def reaction_delta_g(reactants: List[str], products: List[str],
                     verbose: bool = True) -> Dict:
    """反应 ΔG (kJ/mol)"""
    if not _balanced(reactants, products):
        return {"error": "原子不守恒，无法计算 ΔG"}

    if verbose:
        print(f"反应物: {reactants}")
        print(f"产物:   {products}")

    gR, gP = [], []
    if verbose:
        print("\n计算反应物:")
    for s in reactants:
        g = get_g(s, verbose=verbose)
        if g is None:
            return {"error": f"反应物计算失败: {s}"}
        gR.append(g)
    if verbose:
        print("\n计算产物:")
    for s in products:
        g = get_g(s, verbose=verbose)
        if g is None:
            return {"error": f"产物计算失败: {s}"}
        gP.append(g)

    dg_eh = sum(gP) - sum(gR)
    dg_kj = dg_eh * HARTREE_TO_KJ
    verdict = "自发" if dg_kj < 0 else "非自发"
    return {
        "delta_g_kJ": round(dg_kj, 2),
        "delta_g_Eh": round(dg_eh, 6),
        "verdict": verdict,
    }


if __name__ == "__main__":
    # 验证：乙酸乙酯水解
    print("=" * 60)
    print("验证 1: 乙酸乙酯水解")
    print("CC(=O)OCC + H2O -> CC(=O)O + CCO")
    print("=" * 60)
    r = reaction_delta_g(["CC(=O)OCC", "O"], ["CC(=O)O", "CCO"])
    print(f"\n结果: {r}")
    print(f"\n文献参考: ΔG ≈ -20 ~ -40 kJ/mol（自发）")

    # 验证 2：葡萄糖苷水解（甲基葡萄糖苷 -> 葡萄糖 + 甲醇）
    print("\n" + "=" * 60)
    print("验证 2: 甲基葡萄糖苷水解")
    print("=" * 60)
    r2 = reaction_delta_g(["COC1OC(CO)C(O)C(O)C1O", "O"],
                         ["OC1OC(CO)C(O)C(O)C1O", "CO"])
    print(f"\n结果: {r2}")