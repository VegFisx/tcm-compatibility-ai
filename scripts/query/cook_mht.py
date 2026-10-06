from rdkit import Chem
from rdkit.Chem import AllChem, rdMolDescriptors

molecules = {
    "麻黄碱": "CN[C@@H](C)[C@H](O)C1=CC=CC=C1",
    "伪麻黄碱": "CN[C@@H](C)[C@@H](O)C1=CC=CC=C1",
    "桂皮酸": "O=C(O)/C=C/C1=CC=CC=C1",
    "桂皮醛": "O=C/C=C/C1=CC=CC=C1",
    "桂皮醇": "OC/C=C/C1=CC=CC=C1",
    "苦杏仁苷": "N#C[C@H](O[C@@H]1O[C@H](CO[C@@H]2O[C@H](CO)[C@@H](O)[C@H](O)[C@H]2O)[C@@H](O)[C@H](O)[C@H]1O)C1=CC=CC=C1",
    "甘草酸": "CC1(C)[C@@H](O[C@H]2O[C@H](C(=O)O)[C@@H](O)[C@H](O)[C@H]2O[C@@H]2O[C@H](C(=O)O)[C@@H](O)[C@H](O)[C@H]2O)CC[C@]2(C)[C@H]3C(=O)C=C4[C@@H]5C[C@@](C)(C(=O)O)CC[C@]5(C)CC[C@@]4(C)[C@]3(C)CC[C@@H]12"
}

reactions = {
    "氰醇分解": AllChem.ReactionFromSmarts(
        '[C:1]([OH])([C:2]#N)>>[C:1]=O.[C:2]#N'
    ),
    "醛氧化成酸": AllChem.ReactionFromSmarts(
        '[C:1]=[O:2]>>[C:1](=[O:2])[OH]'
    ),
    "烯丙醇氧化": AllChem.ReactionFromSmarts(
        '[C:1]=[C:2][CH2:3][OH:4]>>[C:1]=[C:2][CH:3]=O'
    ),
    "不饱和酸脱羧": AllChem.ReactionFromSmarts(
        '[c:1]/[CH:2]=[CH:3]/[C:4](=[O:5])[OH:6]'
        '>>'
        '[c:1]/[CH:2]=[CH2:3].[C:4](=[O:5])=[O:6]'
    ),
    "糖苷水解": AllChem.ReactionFromSmarts(
        '[C:1][O:2][C:3]1[O:4][C:5][C:6][C:7][C:8]1'
        '>>'
        '[C:1][OH:2].[H][O:3][C:3]1[O:4][C:5][C:6][C:7][C:8]1'
    ),
}

def predict_products(smiles, max_iter=3):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return set()
    current = {Chem.MolToSmiles(mol)}
    all_products = set()
    for _ in range(max_iter):
        new = set()
        for smi in current:
            m = Chem.MolFromSmiles(smi)
            if m is None:
                continue
            for rname, rxn in reactions.items():
                try:
                    prod_sets = rxn.RunReactants((m,))
                except Exception as e:
                    continue
                for prod_set in prod_sets:
                    for p in prod_set:
                        try:
                            Chem.SanitizeMol(p)
                            psmi = Chem.MolToSmiles(p)
                            if psmi not in current and psmi not in all_products:
                                new.add(psmi)
                                all_products.add(psmi)
                        except Exception:
                            continue
        if not new:
            break
        current = new
    return all_products

for name, smi in molecules.items():
    print(f"\n=== {name} ===")
    prods = predict_products(smi)
    if not prods:
        print("当前规则下未预测到新化合物")
    for psmi in prods:
        mol = Chem.MolFromSmiles(psmi)
        if mol:
            formula = rdMolDescriptors.CalcMolFormula(mol)
            print(f"{psmi}    {formula}")