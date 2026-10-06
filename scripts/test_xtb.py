# -*- coding: utf-8 -*-
"""xTB 冒烟测试：葡萄糖 SMILES -> 3D -> xTB 计算"""
import subprocess
import tempfile
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
    lines = [str(mol.GetNumAtoms()), "glucose"]
    conf = mol.GetConformer()
    for i, atom in enumerate(mol.GetAtoms()):
        pos = conf.GetAtomPosition(i)
        lines.append(f"{atom.GetSymbol():2s} {pos.x:14.8f} {pos.y:14.8f} {pos.z:14.8f}")
    return "\n".join(lines) + "\n"


def main():
    print(f"xTB: {XTB}")
    print(f"存在: {XTB.exists()}\n")
    xyz = smiles_to_xyz(SMILES)
    print(f"原子数: {xyz.splitlines()[0]}\n")

    with tempfile.TemporaryDirectory() as td:
        (Path(td) / "mol.xyz").write_text(xyz, encoding="utf-8")
        try:
            r = subprocess.run(
                [str(XTB), "mol.xyz", "--sp", "--gbsa", "water"],
                cwd=td,
                capture_output=True,
                timeout=600,
                encoding="utf-8",
                errors="replace",
            )
        except subprocess.TimeoutExpired:
            print("超时（>10 分钟）")
            return

        print(f"returncode = {r.returncode}\n")
        out = (r.stdout or "") + "\n--- STDERR ---\n" + (r.stderr or "")
        for line in out.splitlines():
            if any(k in line for k in ["TOTAL ENERGY", "HOMO", "LUMO", "GBSA",
                                       "error", "Error", "ERROR", "STDERR",
                                       "finished", "wall", "normal"]):
                print(line)


if __name__ == "__main__":
    main()