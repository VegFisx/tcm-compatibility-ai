# -*- coding: utf-8 -*-
"""xTB 自由能测试：葡萄糖 --ohess"""
import subprocess, tempfile, time, re
from pathlib import Path
from rdkit import Chem
from rdkit.Chem import AllChem

XTB = Path(r"D:\TCMAI\tools\xtb\xtb-6.7.1\bin\xtb.exe")
SMILES = "OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O"


def smiles_to_xyz(smiles):
    mol = Chem.MolFromSmiles(smiles)
    mol = Chem.AddHs(mol)
    AllChem.EmbedMolecule(mol, randomSeed=42)
    AllChem.MMFFOptimizeMolecule(mol)
    lines = [str(mol.GetNumAtoms()), "mol"]
    conf = mol.GetConformer()
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        lines.append(f"{atom.GetSymbol():2s} {pos.x:14.8f} {pos.y:14.8f} {pos.z:14.8f}")
    return "\n".join(lines) + "\n"


def main():
    xyz = smiles_to_xyz(SMILES)
    print(f"原子数: {xyz.splitlines()[0]}")

    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "mol.xyz").write_text(xyz, encoding="utf-8")
        t0 = time.time()
        r = subprocess.run(
            [str(XTB), "mol.xyz", "--ohess", "--gbsa", "water"],
            cwd=td, capture_output=True, timeout=1800,
            encoding="utf-8", errors="replace",
        )
        elapsed = time.time() - t0
        print(f"\n耗时: {elapsed:.1f} 秒")
        print(f"returncode: {r.returncode}\n")

        out = (r.stdout or "") + "\n" + (r.stderr or "")
        # 抓关键行
        for line in out.splitlines():
            if any(k in line for k in ["TOTAL ENERGY", "TOTAL FREE ENERGY",
                                       "G(T)", "G(T,p)", "HOMO", "LUMO",
                                       "normal termination", "ERROR"]):
                print(line)

        # 显式提取自由能
        m = re.search(r"TOTAL FREE ENERGY\s+(-?\d+\.\d+)\s*Eh", out)
        if m:
            g_eh = float(m.group(1))
            g_kj = g_eh * 2625.5  # Hartree -> kJ/mol
            print(f"\n=> G° = {g_eh:.6f} Eh = {g_kj:.1f} kJ/mol")


if __name__ == "__main__":
    main()