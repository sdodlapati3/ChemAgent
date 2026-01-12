"""
RDKit Chemistry Tools
====================

Pure chemistry functions powered by RDKit.

All functions are deterministic and return results with provenance metadata.
Heavily tested with 100+ unit tests.

Example:
    from chemagent.tools import RDKitTools
    
    tools = RDKitTools()
    result = tools.standardize_smiles("CC(=O)Oc1ccccc1C(=O)O")
    print(result.smiles)  # Canonical SMILES
    print(result.provenance)  # Source info
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Lipinski, rdMolDescriptors
    try:
        from rdkit.Chem.MolStandardize import rdMolStandardize
        STANDARDIZER_AVAILABLE = True
    except (ImportError, AttributeError):
        STANDARDIZER_AVAILABLE = False
    from rdkit.Chem.Scaffolds import MurckoScaffold
    from rdkit import __version__ as rdkit_version
    
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False
    STANDARDIZER_AVAILABLE = False
    rdkit_version = "not installed"

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Provenance:
    """Provenance metadata for chemistry operations."""
    
    source: str
    """Source of the data (e.g., 'rdkit', 'chembl')."""
    
    source_version: str
    """Version of the source."""
    
    timestamp: str
    """ISO 8601 timestamp."""
    
    method: str
    """Method/function used."""
    
    parameters: Dict[str, Any] = field(default_factory=dict)
    """Parameters used in the calculation."""
    
    @classmethod
    def create_rdkit(cls, method: str, **params: Any) -> Provenance:
        """Create provenance for RDKit operation."""
        return cls(
            source="rdkit",
            source_version=rdkit_version,
            timestamp=datetime.now().isoformat(),
            method=method,
            parameters=params,
        )


@dataclass
class StandardizedResult:
    """Result from SMILES standardization."""
    
    smiles: str
    """Canonical SMILES string."""
    
    inchi: str
    """InChI string."""
    
    inchi_key: str
    """InChI Key."""
    
    molecular_formula: str
    """Molecular formula (e.g., 'C9H8O4')."""
    
    provenance: Provenance
    """Provenance metadata."""


@dataclass
class MolecularProperties:
    """Molecular properties from RDKit descriptors."""
    
    # Basic properties
    molecular_weight: float
    """Molecular weight (g/mol)."""
    
    exact_mass: float
    """Exact mass."""
    
    # Lipinski Rule of 5
    logp: float
    """Calculated LogP (octanol-water partition coefficient)."""
    
    num_h_donors: int
    """Number of hydrogen bond donors."""
    
    num_h_acceptors: int
    """Number of hydrogen bond acceptors."""
    
    # Additional descriptors
    tpsa: float
    """Topological Polar Surface Area (Ų)."""
    
    num_rotatable_bonds: int
    """Number of rotatable bonds."""
    
    num_aromatic_rings: int
    """Number of aromatic rings."""
    
    num_rings: int
    """Total number of rings."""
    
    num_heteroatoms: int
    """Number of heteroatoms (non-C, non-H)."""
    
    formal_charge: int
    """Formal charge."""
    
    fraction_csp3: float
    """Fraction of sp³ carbons."""
    
    num_stereocenters: int
    """Number of stereogenic centers."""
    
    provenance: Provenance
    """Provenance metadata."""


@dataclass
class LipinskiResult:
    """Lipinski Rule of 5 evaluation."""
    
    molecular_weight: float
    logp: float
    num_h_donors: int
    num_h_acceptors: int
    
    violations: int
    """Number of Rule of 5 violations (0-4)."""
    
    passes: bool
    """True if passes Rule of 5 (≤1 violation allowed)."""
    
    details: List[str] = field(default_factory=list)
    """List of specific violations."""
    
    provenance: Provenance = field(default_factory=lambda: Provenance.create_rdkit("lipinski"))


@dataclass
class SimilarityResult:
    """Similarity search result."""
    
    smiles: str
    """SMILES of the match."""
    
    similarity: float
    """Tanimoto similarity (0.0 to 1.0)."""
    
    index: Optional[int] = None
    """Original index in input list."""
    
    provenance: Provenance = field(default_factory=lambda: Provenance.create_rdkit("similarity"))


# =============================================================================
# Main Tools Class
# =============================================================================

class RDKitTools:
    """
    Chemistry operations using RDKit.
    
    All methods are pure functions (no side effects) and return results
    with provenance metadata.
    
    Example:
        tools = RDKitTools()
        
        # Standardize SMILES
        result = tools.standardize_smiles("CC(=O)Oc1ccccc1C(=O)O")
        print(result.smiles)  # Canonical SMILES
        
        # Calculate properties
        mol = Chem.MolFromSmiles(result.smiles)
        props = tools.calc_molecular_properties(mol)
        print(f"MW: {props.molecular_weight:.2f}")
        print(f"LogP: {props.logp:.2f}")
        
        # Check Lipinski
        lipinski = tools.calc_lipinski(mol)
        print(f"Passes Lipinski: {lipinski.passes}")
    """
    
    def __init__(self):
        """Initialize RDKit tools."""
        if not RDKIT_AVAILABLE:
            raise ImportError(
                "RDKit is not installed. Please install it with:\n"
                "  conda install -c conda-forge rdkit"
            )
        
        # Initialize standardizer if available
        if STANDARDIZER_AVAILABLE:
            try:
                self.standardizer = rdMolStandardize.Standardizer()
                self.uncharger = rdMolStandardize.Uncharger()
                self.largest_fragment = rdMolStandardize.LargestFragmentChooser()
            except AttributeError:
                # Fallback if methods don't exist
                self.standardizer = None
                self.uncharger = None
                self.largest_fragment = None
        else:
            self.standardizer = None
            self.uncharger = None
            self.largest_fragment = None
    
    # =========================================================================
    # SMILES Standardization
    # =========================================================================
    
    def standardize_smiles(
        self,
        smiles: str,
        remove_salts: bool = True,
        neutralize: bool = True,
    ) -> StandardizedResult:
        """
        Standardize SMILES string.
        
        Performs:
        1. Parse SMILES
        2. Remove salts/counterions (optional)
        3. Neutralize charges (optional)
        4. Standardize structure (tautomer, stereochemistry)
        5. Generate canonical SMILES, InChI, InChI Key
        
        Args:
            smiles: Input SMILES string
            remove_salts: Remove salts and keep largest fragment
            neutralize: Remove charges where possible
            
        Returns:
            StandardizedResult with canonical SMILES and identifiers
            
        Raises:
            ValueError: If SMILES is invalid
            
        Example:
            >>> tools = RDKitTools()
            >>> result = tools.standardize_smiles("CC(=O)Oc1ccccc1C(=O)O")
            >>> result.smiles
            'CC(=O)Oc1ccccc1C(=O)O'
            >>> result.molecular_formula
            'C9H8O4'
        """
        try:
            # Parse SMILES
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
            
            # Remove salts (if standardizer available)
            if remove_salts and self.largest_fragment:
                mol = self.largest_fragment.choose(mol)
            
            # Standardize (if standardizer available)
            if self.standardizer:
                mol = self.standardizer.standardize(mol)
            
            # Neutralize (if standardizer available)
            if neutralize and self.uncharger:
                mol = self.uncharger.uncharge(mol)
            
            # Generate identifiers
            canonical_smiles = Chem.MolToSmiles(mol)
            inchi = Chem.MolToInchi(mol)
            inchi_key = Chem.MolToInchiKey(mol)
            molecular_formula = rdMolDescriptors.CalcMolFormula(mol)
            
            return StandardizedResult(
                smiles=canonical_smiles,
                inchi=inchi,
                inchi_key=inchi_key,
                molecular_formula=molecular_formula,
                provenance=Provenance.create_rdkit(
                    "standardize_smiles",
                    remove_salts=remove_salts,
                    neutralize=neutralize,
                    input_smiles=smiles,
                ),
            )
        
        except Exception as e:
            logger.error(f"Failed to standardize SMILES '{smiles}': {e}")
            raise ValueError(f"Failed to standardize SMILES: {e}") from e
    
    # =========================================================================
    # Property Calculation
    # =========================================================================
    
    def calc_molecular_properties(self, mol: Chem.Mol) -> MolecularProperties:
        """
        Calculate molecular properties.
        
        Computes comprehensive set of descriptors including:
        - Basic: MW, exact mass, formula
        - Lipinski: LogP, H-bond donors/acceptors
        - ADME: TPSA, rotatable bonds
        - Structural: rings, aromatic rings, heteroatoms
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            MolecularProperties with all descriptors
            
        Example:
            >>> mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")
            >>> props = tools.calc_molecular_properties(mol)
            >>> props.molecular_weight
            180.159
            >>> props.logp
            1.19
        """
        # Calculate fraction of sp3 carbons (with fallback for older RDKit versions)
        try:
            fraction_csp3 = Descriptors.FractionCSP3(mol)
        except AttributeError:
            # Fallback: manually calculate fraction of sp3 carbons
            try:
                from rdkit.Chem import Lipinski
                fraction_csp3 = Lipinski.FractionCSP3(mol)
            except (ImportError, AttributeError):
                # Last resort: calculate manually
                num_sp3 = sum(1 for atom in mol.GetAtoms() 
                             if atom.GetAtomicNum() == 6 and atom.GetHybridization() == Chem.HybridizationType.SP3)
                num_carbons = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() == 6)
                fraction_csp3 = num_sp3 / num_carbons if num_carbons > 0 else 0.0
        
        return MolecularProperties(
            molecular_weight=Descriptors.MolWt(mol),
            exact_mass=Descriptors.ExactMolWt(mol),
            logp=Descriptors.MolLogP(mol),
            num_h_donors=Descriptors.NumHDonors(mol),
            num_h_acceptors=Descriptors.NumHAcceptors(mol),
            tpsa=Descriptors.TPSA(mol),
            num_rotatable_bonds=Descriptors.NumRotatableBonds(mol),
            num_aromatic_rings=Descriptors.NumAromaticRings(mol),
            num_rings=Descriptors.RingCount(mol),
            num_heteroatoms=Descriptors.NumHeteroatoms(mol),
            formal_charge=Chem.GetFormalCharge(mol),
            fraction_csp3=fraction_csp3,
            num_stereocenters=len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
            provenance=Provenance.create_rdkit("calc_molecular_properties"),
        )
    
    def calc_lipinski(self, mol: Chem.Mol) -> LipinskiResult:
        """
        Calculate Lipinski Rule of 5 properties and violations.
        
        Rule of 5 criteria:
        1. Molecular weight ≤ 500 Da
        2. LogP ≤ 5
        3. Hydrogen bond donors ≤ 5
        4. Hydrogen bond acceptors ≤ 10
        
        A compound "passes" if it has ≤1 violation (Lipinski's original definition).
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            LipinskiResult with violations count and details
            
        Example:
            >>> mol = Chem.MolFromSmiles("CC(=O)Oc1ccccc1C(=O)O")  # Aspirin
            >>> lipinski = tools.calc_lipinski(mol)
            >>> lipinski.passes
            True
            >>> lipinski.violations
            0
        """
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        hbd = Descriptors.NumHDonors(mol)
        hba = Descriptors.NumHAcceptors(mol)
        
        violations = []
        if mw > 500:
            violations.append(f"MW > 500 ({mw:.1f})")
        if logp > 5:
            violations.append(f"LogP > 5 ({logp:.2f})")
        if hbd > 5:
            violations.append(f"H-bond donors > 5 ({hbd})")
        if hba > 10:
            violations.append(f"H-bond acceptors > 10 ({hba})")
        
        num_violations = len(violations)
        passes = num_violations <= 1  # ≤1 violation allowed
        
        return LipinskiResult(
            molecular_weight=mw,
            logp=logp,
            num_h_donors=hbd,
            num_h_acceptors=hba,
            violations=num_violations,
            passes=passes,
            details=violations,
            provenance=Provenance.create_rdkit("calc_lipinski"),
        )
    
    # =========================================================================
    # Similarity Search
    # =========================================================================
    
    def calc_fingerprint(
        self,
        mol: Chem.Mol,
        fp_type: str = "morgan",
        radius: int = 2,
        n_bits: int = 2048,
    ) -> Any:
        """
        Calculate molecular fingerprint.
        
        Args:
            mol: RDKit Mol object
            fp_type: Fingerprint type ('morgan', 'topological', 'atompair', 'torsion')
            radius: Morgan fingerprint radius (default: 2)
            n_bits: Number of bits in fingerprint (default: 2048)
            
        Returns:
            RDKit fingerprint object
            
        Example:
            >>> mol = Chem.MolFromSmiles("CCO")
            >>> fp = tools.calc_fingerprint(mol, fp_type="morgan", radius=2)
        """
        if fp_type == "morgan":
            return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)
        elif fp_type == "topological":
            return Chem.RDKFingerprint(mol, fpSize=n_bits)
        elif fp_type == "atompair":
            return AllChem.GetAtomPairFingerprint(mol)
        elif fp_type == "torsion":
            return AllChem.GetTopologicalTorsionFingerprint(mol)
        else:
            raise ValueError(f"Unknown fingerprint type: {fp_type}")
    
    def calc_similarity(
        self,
        mol1: Chem.Mol,
        mol2: Chem.Mol,
        fp_type: str = "morgan",
        radius: int = 2,
    ) -> float:
        """
        Calculate Tanimoto similarity between two molecules.
        
        Args:
            mol1: First molecule
            mol2: Second molecule
            fp_type: Fingerprint type
            radius: Morgan fingerprint radius
            
        Returns:
            Tanimoto similarity (0.0 to 1.0)
            
        Example:
            >>> mol1 = Chem.MolFromSmiles("CCO")
            >>> mol2 = Chem.MolFromSmiles("CCCO")
            >>> similarity = tools.calc_similarity(mol1, mol2)
            >>> similarity
            0.6666666666666666
        """
        fp1 = self.calc_fingerprint(mol1, fp_type, radius)
        fp2 = self.calc_fingerprint(mol2, fp_type, radius)
        
        return Chem.DataStructs.TanimotoSimilarity(fp1, fp2)
    
    def similarity_search(
        self,
        query_mol: Chem.Mol,
        mol_list: List[Chem.Mol],
        threshold: float = 0.7,
        fp_type: str = "morgan",
        radius: int = 2,
        return_top_n: Optional[int] = None,
    ) -> List[SimilarityResult]:
        """
        Search for similar molecules in a list.
        
        Args:
            query_mol: Query molecule
            mol_list: List of molecules to search
            threshold: Minimum Tanimoto similarity (0.0 to 1.0)
            fp_type: Fingerprint type
            radius: Morgan fingerprint radius
            return_top_n: Return only top N matches (None = all above threshold)
            
        Returns:
            List of SimilarityResult, sorted by descending similarity
            
        Example:
            >>> query = Chem.MolFromSmiles("CCO")
            >>> mols = [Chem.MolFromSmiles(s) for s in ["CCCO", "CCCCO", "c1ccccc1"]]
            >>> results = tools.similarity_search(query, mols, threshold=0.5)
            >>> len(results)
            2
            >>> results[0].similarity > results[1].similarity
            True
        """
        query_fp = self.calc_fingerprint(query_mol, fp_type, radius)
        
        results = []
        for i, mol in enumerate(mol_list):
            if mol is None:
                continue
            
            fp = self.calc_fingerprint(mol, fp_type, radius)
            similarity = Chem.DataStructs.TanimotoSimilarity(query_fp, fp)
            
            if similarity >= threshold:
                results.append(
                    SimilarityResult(
                        smiles=Chem.MolToSmiles(mol),
                        similarity=similarity,
                        index=i,
                        provenance=Provenance.create_rdkit(
                            "similarity_search",
                            fp_type=fp_type,
                            radius=radius,
                            threshold=threshold,
                        ),
                    )
                )
        
        # Sort by descending similarity
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        # Return top N if requested
        if return_top_n is not None:
            results = results[:return_top_n]
        
        return results
    
    # =========================================================================
    # Substructure Search
    # =========================================================================
    
    def substructure_search(
        self,
        query_smarts: str,
        mol_list: List[Chem.Mol],
    ) -> List[int]:
        """
        Search for molecules containing a substructure.
        
        Args:
            query_smarts: SMARTS pattern
            mol_list: List of molecules to search
            
        Returns:
            List of indices of molecules containing the substructure
            
        Example:
            >>> # Find molecules with benzene ring
            >>> mols = [
            ...     Chem.MolFromSmiles("c1ccccc1"),  # Benzene
            ...     Chem.MolFromSmiles("CCO"),  # Ethanol
            ...     Chem.MolFromSmiles("c1ccccc1O"),  # Phenol
            ... ]
            >>> matches = tools.substructure_search("c1ccccc1", mols)
            >>> matches
            [0, 2]
        """
        query_mol = Chem.MolFromSmarts(query_smarts)
        if query_mol is None:
            raise ValueError(f"Invalid SMARTS pattern: {query_smarts}")
        
        matches = []
        for i, mol in enumerate(mol_list):
            if mol is None:
                continue
            
            if mol.HasSubstructMatch(query_mol):
                matches.append(i)
        
        return matches
    
    # =========================================================================
    # Scaffold Extraction
    # =========================================================================
    
    def extract_murcko_scaffold(self, mol: Chem.Mol) -> str:
        """
        Extract Murcko scaffold (core structure without side chains).
        
        Args:
            mol: RDKit Mol object
            
        Returns:
            SMILES of Murcko scaffold
            
        Example:
            >>> mol = Chem.MolFromSmiles("c1ccc(cc1)CCN")  # Phenethylamine
            >>> scaffold = tools.extract_murcko_scaffold(mol)
            >>> scaffold
            'c1ccc(cc1)CC'
        """
        scaffold = MurckoScaffold.GetScaffoldForMol(mol)
        return Chem.MolToSmiles(scaffold)
    
    # =========================================================================
    # Validation
    # =========================================================================
    
    def is_valid_smiles(self, smiles: str) -> bool:
        """
        Check if SMILES string is valid.
        
        Args:
            smiles: SMILES string to validate
            
        Returns:
            True if valid, False otherwise
            
        Example:
            >>> tools.is_valid_smiles("CCO")
            True
            >>> tools.is_valid_smiles("invalid")
            False
        """
        try:
            mol = Chem.MolFromSmiles(smiles)
            return mol is not None
        except:
            return False
    
    def is_valid_smarts(self, smarts: str) -> bool:
        """
        Check if SMARTS pattern is valid.
        
        Args:
            smarts: SMARTS pattern to validate
            
        Returns:
            True if valid, False otherwise
            
        Example:
            >>> tools.is_valid_smarts("c1ccccc1")
            True
            >>> tools.is_valid_smarts("[invalid")
            False
        """
        try:
            mol = Chem.MolFromSmarts(smarts)
            return mol is not None
        except:
            return False


# =============================================================================
# Convenience Functions
# =============================================================================

def smiles_to_mol(smiles: str) -> Chem.Mol:
    """
    Convert SMILES to RDKit Mol object.
    
    Args:
        smiles: SMILES string
        
    Returns:
        RDKit Mol object
        
    Raises:
        ValueError: If SMILES is invalid
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")
    return mol


def mol_to_smiles(mol: Chem.Mol, canonical: bool = True) -> str:
    """
    Convert RDKit Mol object to SMILES.
    
    Args:
        mol: RDKit Mol object
        canonical: Return canonical SMILES
        
    Returns:
        SMILES string
    """
    return Chem.MolToSmiles(mol, canonical=canonical)
