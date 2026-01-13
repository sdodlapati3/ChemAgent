"""
ADMET (Absorption, Distribution, Metabolism, Excretion, Toxicity) Prediction Module.

Provides computational predictions for drug-like properties critical in
drug discovery and development pipelines.

Key Features:
- Physicochemical property calculations
- ADME endpoint predictions (using empirical rules)
- Toxicity alerts (PAINS, Brenk, structural alerts)
- Drug-likeness filters (Lipinski, Veber, Ghose, Egan)
- Lead-likeness assessment
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, AllChem, FilterCatalog
from rdkit.Chem.FilterCatalog import FilterCatalogParams

logger = logging.getLogger(__name__)


class ADMETCategory(Enum):
    """ADMET prediction categories."""
    ABSORPTION = "absorption"
    DISTRIBUTION = "distribution"
    METABOLISM = "metabolism"
    EXCRETION = "excretion"
    TOXICITY = "toxicity"


@dataclass
class PhysicochemicalProperties:
    """Comprehensive physicochemical property calculations."""
    
    molecular_weight: float
    logp: float  # Wildman-Crippen LogP
    tpsa: float  # Topological polar surface area
    num_h_donors: int
    num_h_acceptors: int
    num_rotatable_bonds: int
    num_rings: int
    num_aromatic_rings: int
    num_heavy_atoms: int
    fraction_csp3: float
    molar_refractivity: float
    
    # Additional descriptors
    num_heteroatoms: int = 0
    num_stereocenters: int = 0
    formal_charge: int = 0


@dataclass
class AbsorptionPrediction:
    """Absorption (A) predictions."""
    
    # Oral absorption indicators
    human_intestinal_absorption: str  # "High", "Medium", "Low"
    hia_probability: float
    
    # Permeability
    caco2_permeability: str  # "High", "Medium", "Low"
    caco2_log_papp: float  # log Papp (cm/s)
    
    # Bioavailability
    bioavailability_score: float  # 0-1 scale
    
    # Solubility
    solubility_class: str  # "Highly soluble", "Soluble", "Poorly soluble", "Insoluble"
    log_s: float  # Predicted log S (mol/L)
    
    reasoning: List[str] = field(default_factory=list)


@dataclass
class DistributionPrediction:
    """Distribution (D) predictions."""
    
    # Blood-brain barrier
    bbb_permeant: bool
    bbb_probability: float
    
    # Plasma protein binding
    ppb_class: str  # "High", "Medium", "Low"
    ppb_percentage: float
    
    # Volume of distribution
    vd_class: str  # "High", "Medium", "Low"
    
    # P-glycoprotein
    pgp_substrate: bool
    pgp_inhibitor: bool
    
    reasoning: List[str] = field(default_factory=list)


@dataclass
class MetabolismPrediction:
    """Metabolism (M) predictions."""
    
    # CYP450 interactions
    cyp1a2_inhibitor: bool
    cyp2c9_inhibitor: bool
    cyp2c19_inhibitor: bool
    cyp2d6_inhibitor: bool
    cyp3a4_inhibitor: bool
    
    # Substrate predictions
    cyp3a4_substrate: bool
    cyp2d6_substrate: bool
    
    # Metabolic stability
    metabolic_stability: str  # "Stable", "Moderate", "Unstable"
    
    # Structural alerts for metabolism
    metabolic_soft_spots: List[str] = field(default_factory=list)
    
    reasoning: List[str] = field(default_factory=list)


@dataclass
class ExcretionPrediction:
    """Excretion (E) predictions."""
    
    # Renal clearance
    renal_clearance_class: str  # "High", "Medium", "Low"
    
    # Half-life estimation
    half_life_class: str  # "Short", "Medium", "Long"
    
    # Transporter interactions
    oat_substrate: bool  # Organic anion transporter
    oct_substrate: bool  # Organic cation transporter
    
    reasoning: List[str] = field(default_factory=list)


@dataclass
class ToxicityAlert:
    """Individual toxicity alert."""
    
    alert_name: str
    alert_type: str  # "PAINS", "Brenk", "NIH", "Structural"
    severity: str  # "High", "Medium", "Low"
    description: str
    matched_smarts: Optional[str] = None


@dataclass
class ToxicityPrediction:
    """Toxicity (T) predictions."""
    
    # Overall assessment
    toxicity_risk: str  # "High", "Medium", "Low"
    
    # Specific toxicity endpoints
    ames_mutagenicity: bool
    herg_inhibition: bool  # Cardiac toxicity
    hepatotoxicity_risk: str
    
    # Structural alerts
    pains_alerts: List[ToxicityAlert] = field(default_factory=list)
    brenk_alerts: List[ToxicityAlert] = field(default_factory=list)
    other_alerts: List[ToxicityAlert] = field(default_factory=list)
    
    # Drug-likeness violations
    num_alerts: int = 0
    
    reasoning: List[str] = field(default_factory=list)


@dataclass
class DrugLikenessAssessment:
    """Comprehensive drug-likeness assessment."""
    
    # Rule-based filters
    lipinski_passes: bool
    lipinski_violations: int
    
    veber_passes: bool
    veber_violations: int
    
    ghose_passes: bool
    ghose_violations: int
    
    egan_passes: bool
    egan_violations: int
    
    muegge_passes: bool
    muegge_violations: int
    
    # Lead-likeness
    lead_like: bool
    lead_violations: int
    
    # Overall score
    drug_likeness_score: float  # 0-1 composite score
    
    # Detailed violations
    violations: List[str] = field(default_factory=list)


@dataclass
class ADMETReport:
    """Complete ADMET prediction report."""
    
    smiles: str
    compound_name: Optional[str]
    
    # Component predictions
    physicochemical: PhysicochemicalProperties
    absorption: AbsorptionPrediction
    distribution: DistributionPrediction
    metabolism: MetabolismPrediction
    excretion: ExcretionPrediction
    toxicity: ToxicityPrediction
    drug_likeness: DrugLikenessAssessment
    
    # Overall assessment
    overall_score: float  # 0-1 composite ADMET score
    overall_assessment: str  # "Favorable", "Moderate concerns", "Significant concerns"
    key_concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class ADMETPredictor:
    """
    ADMET property predictor using rule-based and empirical models.
    
    This implementation uses established rules and correlations from
    medicinal chemistry literature rather than ML models, ensuring
    interpretability and transparency in predictions.
    """
    
    def __init__(self):
        """Initialize ADMET predictor with filter catalogs."""
        self._init_filter_catalogs()
    
    def _init_filter_catalogs(self):
        """Initialize RDKit filter catalogs for toxicity alerts."""
        # PAINS filters
        try:
            pains_params = FilterCatalogParams()
            pains_params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
            self.pains_catalog = FilterCatalog.FilterCatalog(pains_params)
        except Exception as e:
            logger.warning(f"Could not initialize PAINS catalog: {e}")
            self.pains_catalog = None
        
        # Brenk filters (unwanted substructures)
        try:
            brenk_params = FilterCatalogParams()
            brenk_params.AddCatalog(FilterCatalogParams.FilterCatalogs.BRENK)
            self.brenk_catalog = FilterCatalog.FilterCatalog(brenk_params)
        except Exception as e:
            logger.warning(f"Could not initialize Brenk catalog: {e}")
            self.brenk_catalog = None
        
        # NIH filters
        try:
            nih_params = FilterCatalogParams()
            nih_params.AddCatalog(FilterCatalogParams.FilterCatalogs.NIH)
            self.nih_catalog = FilterCatalog.FilterCatalog(nih_params)
        except Exception as e:
            logger.warning(f"Could not initialize NIH catalog: {e}")
            self.nih_catalog = None
    
    def predict(
        self,
        smiles: str,
        compound_name: Optional[str] = None
    ) -> ADMETReport:
        """
        Generate comprehensive ADMET predictions for a compound.
        
        Args:
            smiles: SMILES string of the compound
            compound_name: Optional name for the compound
            
        Returns:
            ADMETReport with all predictions
        """
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError(f"Invalid SMILES: {smiles}")
        
        # Calculate all components
        physico = self._calc_physicochemical(mol)
        absorption = self._predict_absorption(mol, physico)
        distribution = self._predict_distribution(mol, physico)
        metabolism = self._predict_metabolism(mol, physico)
        excretion = self._predict_excretion(mol, physico)
        toxicity = self._predict_toxicity(mol, physico)
        drug_likeness = self._assess_drug_likeness(mol, physico)
        
        # Calculate overall score and assessment
        overall_score, assessment, concerns, recommendations = self._calculate_overall(
            physico, absorption, distribution, metabolism, excretion, toxicity, drug_likeness
        )
        
        return ADMETReport(
            smiles=smiles,
            compound_name=compound_name,
            physicochemical=physico,
            absorption=absorption,
            distribution=distribution,
            metabolism=metabolism,
            excretion=excretion,
            toxicity=toxicity,
            drug_likeness=drug_likeness,
            overall_score=overall_score,
            overall_assessment=assessment,
            key_concerns=concerns,
            recommendations=recommendations,
        )
    
    def _calc_physicochemical(self, mol: Chem.Mol) -> PhysicochemicalProperties:
        """Calculate comprehensive physicochemical properties."""
        return PhysicochemicalProperties(
            molecular_weight=Descriptors.MolWt(mol),
            logp=Descriptors.MolLogP(mol),
            tpsa=Descriptors.TPSA(mol),
            num_h_donors=Descriptors.NumHDonors(mol),
            num_h_acceptors=Descriptors.NumHAcceptors(mol),
            num_rotatable_bonds=Descriptors.NumRotatableBonds(mol),
            num_rings=Descriptors.RingCount(mol),
            num_aromatic_rings=Descriptors.NumAromaticRings(mol),
            num_heavy_atoms=Descriptors.HeavyAtomCount(mol),
            fraction_csp3=Descriptors.FractionCSP3(mol),
            molar_refractivity=Descriptors.MolMR(mol),
            num_heteroatoms=Descriptors.NumHeteroatoms(mol),
            num_stereocenters=len(Chem.FindMolChiralCenters(mol, includeUnassigned=True)),
            formal_charge=Chem.GetFormalCharge(mol),
        )
    
    def _predict_absorption(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> AbsorptionPrediction:
        """
        Predict absorption properties.
        
        Uses empirical rules:
        - HIA: Based on PSA and LogP
        - Caco-2: Based on PSA and MW
        - Solubility: Based on LogP and MW
        """
        reasoning = []
        
        # Human Intestinal Absorption (HIA)
        # Rule: PSA < 140 Å² and LogP between -2 and 6
        if physico.tpsa < 100 and -1 < physico.logp < 5:
            hia = "High"
            hia_prob = 0.9
            reasoning.append("High HIA predicted due to favorable PSA (<100) and LogP")
        elif physico.tpsa < 140 and -2 < physico.logp < 6:
            hia = "Medium"
            hia_prob = 0.7
            reasoning.append("Medium HIA: PSA or LogP slightly outside optimal range")
        else:
            hia = "Low"
            hia_prob = 0.3
            reasoning.append(f"Low HIA: PSA={physico.tpsa:.1f} or LogP={physico.logp:.2f} unfavorable")
        
        # Caco-2 permeability
        # Rule: Based on PSA and MW (Palm et al. correlation)
        if physico.tpsa < 60 and physico.molecular_weight < 400:
            caco2 = "High"
            caco2_papp = -4.5
        elif physico.tpsa < 90 and physico.molecular_weight < 500:
            caco2 = "Medium"
            caco2_papp = -5.5
        else:
            caco2 = "Low"
            caco2_papp = -6.5
        
        # Bioavailability score (Martin's rule of 5 extended)
        ba_score = 1.0
        if physico.molecular_weight > 500:
            ba_score -= 0.2
        if physico.logp > 5:
            ba_score -= 0.2
        if physico.tpsa > 140:
            ba_score -= 0.2
        if physico.num_rotatable_bonds > 10:
            ba_score -= 0.2
        ba_score = max(0, ba_score)
        
        # Solubility (ESOL model approximation)
        # log S = 0.16 - 0.63*cLogP - 0.0062*MW + 0.066*RB - 0.74*AP
        log_s = 0.16 - 0.63 * physico.logp - 0.0062 * physico.molecular_weight
        
        if log_s > -2:
            sol_class = "Highly soluble"
        elif log_s > -4:
            sol_class = "Soluble"
        elif log_s > -6:
            sol_class = "Poorly soluble"
        else:
            sol_class = "Insoluble"
            reasoning.append(f"Poor solubility (log S = {log_s:.2f}) may limit absorption")
        
        return AbsorptionPrediction(
            human_intestinal_absorption=hia,
            hia_probability=hia_prob,
            caco2_permeability=caco2,
            caco2_log_papp=caco2_papp,
            bioavailability_score=ba_score,
            solubility_class=sol_class,
            log_s=log_s,
            reasoning=reasoning,
        )
    
    def _predict_distribution(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> DistributionPrediction:
        """
        Predict distribution properties.
        
        Uses empirical rules:
        - BBB: Lipinski's BBB rules (MW < 400, PSA < 90, HBD < 3)
        - PPB: Based on LogP and charge
        - P-gp: Based on MW and PSA
        """
        reasoning = []
        
        # Blood-Brain Barrier (BBB) penetration
        # Rule: MW < 400, PSA < 90, HBD < 3, LogP 1-3
        bbb_score = 0
        if physico.molecular_weight < 400:
            bbb_score += 1
        if physico.tpsa < 90:
            bbb_score += 1
        if physico.num_h_donors <= 3:
            bbb_score += 1
        if 1 < physico.logp < 3:
            bbb_score += 1
        
        bbb_permeant = bbb_score >= 3
        bbb_prob = bbb_score / 4.0
        
        if bbb_permeant:
            reasoning.append("BBB permeant: favorable MW, PSA, HBD, and LogP")
        else:
            reasoning.append(f"Limited BBB penetration (score: {bbb_score}/4)")
        
        # Plasma Protein Binding
        # Rule: Higher LogP = higher PPB, charged compounds vary
        if physico.logp > 4:
            ppb_class = "High"
            ppb_pct = 95.0
            reasoning.append("High plasma protein binding expected (high LogP)")
        elif physico.logp > 2:
            ppb_class = "Medium"
            ppb_pct = 80.0
        else:
            ppb_class = "Low"
            ppb_pct = 50.0
        
        # Volume of Distribution
        # Rule: Higher LogP and lower PSA = higher Vd
        if physico.logp > 3 and physico.tpsa < 75:
            vd_class = "High"
        elif physico.logp > 1:
            vd_class = "Medium"
        else:
            vd_class = "Low"
        
        # P-glycoprotein substrate/inhibitor
        # Rule: MW > 400 and PSA > 75 suggests P-gp substrate
        pgp_substrate = physico.molecular_weight > 400 and physico.tpsa > 75
        pgp_inhibitor = physico.molecular_weight > 400 and physico.logp > 4
        
        if pgp_substrate:
            reasoning.append("Potential P-gp substrate (may affect distribution)")
        
        return DistributionPrediction(
            bbb_permeant=bbb_permeant,
            bbb_probability=bbb_prob,
            ppb_class=ppb_class,
            ppb_percentage=ppb_pct,
            vd_class=vd_class,
            pgp_substrate=pgp_substrate,
            pgp_inhibitor=pgp_inhibitor,
            reasoning=reasoning,
        )
    
    def _predict_metabolism(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> MetabolismPrediction:
        """
        Predict metabolism properties.
        
        Uses structural features and empirical rules for CYP450 interactions.
        """
        reasoning = []
        soft_spots = []
        
        # CYP inhibition predictions based on structural features
        # These are simplified rules - real predictions would use ML models
        
        # CYP1A2: planar aromatic compounds
        cyp1a2_inhib = physico.num_aromatic_rings >= 2 and physico.tpsa < 50
        
        # CYP2C9: acidic compounds with aromatic rings
        cyp2c9_inhib = physico.formal_charge < 0 and physico.num_aromatic_rings >= 1
        
        # CYP2C19: basic nitrogen-containing compounds
        cyp2c19_inhib = physico.num_heteroatoms >= 2 and physico.logp > 2
        
        # CYP2D6: basic amines
        has_basic_n = mol.HasSubstructMatch(Chem.MolFromSmarts("[NX3;H2,H1;!$(NC=O)]"))
        cyp2d6_inhib = has_basic_n and physico.logp > 1
        cyp2d6_substrate = has_basic_n
        
        # CYP3A4: large lipophilic compounds (most common)
        cyp3a4_inhib = physico.molecular_weight > 350 and physico.logp > 3
        cyp3a4_substrate = physico.molecular_weight > 300
        
        if cyp3a4_substrate:
            reasoning.append("Likely CYP3A4 substrate (common for drugs >300 Da)")
        
        # Count inhibitions for stability assessment
        num_cyp_inhibitions = sum([
            cyp1a2_inhib, cyp2c9_inhib, cyp2c19_inhib,
            cyp2d6_inhib, cyp3a4_inhib
        ])
        
        if num_cyp_inhibitions >= 3:
            stability = "Unstable"
            reasoning.append(f"Multiple CYP interactions ({num_cyp_inhibitions}) suggest metabolic instability")
        elif num_cyp_inhibitions >= 1:
            stability = "Moderate"
        else:
            stability = "Stable"
        
        # Identify metabolic soft spots (simplified)
        if mol.HasSubstructMatch(Chem.MolFromSmarts("[CH3]")):
            soft_spots.append("Methyl groups (potential oxidation)")
        if mol.HasSubstructMatch(Chem.MolFromSmarts("[NH]")):
            soft_spots.append("Secondary amines (N-dealkylation)")
        if mol.HasSubstructMatch(Chem.MolFromSmarts("c")):
            soft_spots.append("Aromatic rings (hydroxylation)")
        
        return MetabolismPrediction(
            cyp1a2_inhibitor=cyp1a2_inhib,
            cyp2c9_inhibitor=cyp2c9_inhib,
            cyp2c19_inhibitor=cyp2c19_inhib,
            cyp2d6_inhibitor=cyp2d6_inhib,
            cyp3a4_inhibitor=cyp3a4_inhib,
            cyp3a4_substrate=cyp3a4_substrate,
            cyp2d6_substrate=cyp2d6_substrate,
            metabolic_stability=stability,
            metabolic_soft_spots=soft_spots,
            reasoning=reasoning,
        )
    
    def _predict_excretion(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> ExcretionPrediction:
        """
        Predict excretion properties.
        
        Uses empirical rules based on MW, charge, and LogP.
        """
        reasoning = []
        
        # Renal clearance
        # Rule: Small, hydrophilic, charged compounds = high renal clearance
        if physico.molecular_weight < 300 and physico.logp < 1:
            renal = "High"
            reasoning.append("High renal clearance expected (low MW, hydrophilic)")
        elif physico.molecular_weight < 500 and physico.logp < 3:
            renal = "Medium"
        else:
            renal = "Low"
            reasoning.append("Low renal clearance (large/lipophilic compound)")
        
        # Half-life estimation
        # Rule: Based on metabolic stability and clearance
        if physico.logp > 4 or physico.molecular_weight > 500:
            half_life = "Long"
        elif physico.logp < 1 and physico.molecular_weight < 300:
            half_life = "Short"
        else:
            half_life = "Medium"
        
        # Transporter predictions
        # OAT: organic anions (acids)
        oat_substrate = physico.formal_charge < 0
        
        # OCT: organic cations (bases)
        oct_substrate = physico.formal_charge > 0
        
        return ExcretionPrediction(
            renal_clearance_class=renal,
            half_life_class=half_life,
            oat_substrate=oat_substrate,
            oct_substrate=oct_substrate,
            reasoning=reasoning,
        )
    
    def _predict_toxicity(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> ToxicityPrediction:
        """
        Predict toxicity using structural alerts.
        
        Uses RDKit filter catalogs for PAINS, Brenk, and NIH alerts.
        """
        reasoning = []
        pains_alerts = []
        brenk_alerts = []
        other_alerts = []
        
        # Check PAINS alerts
        if self.pains_catalog:
            entry = self.pains_catalog.GetFirstMatch(mol)
            while entry:
                pains_alerts.append(ToxicityAlert(
                    alert_name=entry.GetDescription(),
                    alert_type="PAINS",
                    severity="High",
                    description="Pan-assay interference compound - may give false positives in assays",
                ))
                # Get next match
                matches = list(self.pains_catalog.GetMatches(mol))
                if len(matches) > len(pains_alerts):
                    entry = matches[len(pains_alerts)]
                else:
                    break
        
        if pains_alerts:
            reasoning.append(f"PAINS alert: {len(pains_alerts)} structural pattern(s) found")
        
        # Check Brenk alerts
        if self.brenk_catalog:
            matches = list(self.brenk_catalog.GetMatches(mol))
            for match in matches[:5]:  # Limit to first 5
                brenk_alerts.append(ToxicityAlert(
                    alert_name=match.GetDescription(),
                    alert_type="Brenk",
                    severity="Medium",
                    description="Unwanted substructure for drug development",
                ))
        
        if brenk_alerts:
            reasoning.append(f"Brenk alert: {len(brenk_alerts)} unwanted substructure(s)")
        
        # Check NIH alerts
        if self.nih_catalog:
            matches = list(self.nih_catalog.GetMatches(mol))
            for match in matches[:5]:
                other_alerts.append(ToxicityAlert(
                    alert_name=match.GetDescription(),
                    alert_type="NIH",
                    severity="Medium",
                    description="NIH screening alert",
                ))
        
        # Ames mutagenicity prediction (simplified)
        # Nitro groups, aromatic amines are mutagenic alerts
        has_nitro = mol.HasSubstructMatch(Chem.MolFromSmarts("[N+](=O)[O-]"))
        has_aromatic_amine = mol.HasSubstructMatch(Chem.MolFromSmarts("c[NH2]"))
        ames_positive = has_nitro or has_aromatic_amine
        
        if ames_positive:
            reasoning.append("Potential mutagenicity (nitro or aromatic amine detected)")
        
        # hERG inhibition prediction
        # Rule: LogP > 3.7, pKa > 7.4, and MW > 350
        herg_risk = physico.logp > 3.7 and physico.molecular_weight > 350
        
        if herg_risk:
            reasoning.append("Potential hERG inhibition risk (cardiac safety)")
        
        # Hepatotoxicity
        if physico.logp > 5 or pains_alerts or brenk_alerts:
            hepato_risk = "Medium"
        else:
            hepato_risk = "Low"
        
        # Overall toxicity risk
        total_alerts = len(pains_alerts) + len(brenk_alerts) + len(other_alerts)
        if total_alerts >= 3 or ames_positive or herg_risk:
            tox_risk = "High"
        elif total_alerts >= 1:
            tox_risk = "Medium"
        else:
            tox_risk = "Low"
        
        return ToxicityPrediction(
            toxicity_risk=tox_risk,
            ames_mutagenicity=ames_positive,
            herg_inhibition=herg_risk,
            hepatotoxicity_risk=hepato_risk,
            pains_alerts=pains_alerts,
            brenk_alerts=brenk_alerts,
            other_alerts=other_alerts,
            num_alerts=total_alerts,
            reasoning=reasoning,
        )
    
    def _assess_drug_likeness(
        self,
        mol: Chem.Mol,
        physico: PhysicochemicalProperties
    ) -> DrugLikenessAssessment:
        """
        Assess drug-likeness using multiple rule sets.
        """
        violations = []
        
        # Lipinski's Rule of 5
        lipinski_v = 0
        if physico.molecular_weight > 500:
            lipinski_v += 1
            violations.append("Lipinski: MW > 500")
        if physico.logp > 5:
            lipinski_v += 1
            violations.append("Lipinski: LogP > 5")
        if physico.num_h_donors > 5:
            lipinski_v += 1
            violations.append("Lipinski: HBD > 5")
        if physico.num_h_acceptors > 10:
            lipinski_v += 1
            violations.append("Lipinski: HBA > 10")
        lipinski_passes = lipinski_v <= 1
        
        # Veber's Rules (oral bioavailability)
        veber_v = 0
        if physico.num_rotatable_bonds > 10:
            veber_v += 1
            violations.append("Veber: Rotatable bonds > 10")
        if physico.tpsa > 140:
            veber_v += 1
            violations.append("Veber: TPSA > 140")
        veber_passes = veber_v == 0
        
        # Ghose filter
        ghose_v = 0
        if not (160 < physico.molecular_weight < 480):
            ghose_v += 1
        if not (-0.4 < physico.logp < 5.6):
            ghose_v += 1
        if not (40 < physico.molar_refractivity < 130):
            ghose_v += 1
        if not (20 < physico.num_heavy_atoms < 70):
            ghose_v += 1
        ghose_passes = ghose_v == 0
        
        # Egan filter (BBB)
        egan_v = 0
        if physico.tpsa > 131.6:
            egan_v += 1
        if physico.logp > 5.88:
            egan_v += 1
        egan_passes = egan_v == 0
        
        # Muegge filter
        muegge_v = 0
        if not (200 < physico.molecular_weight < 600):
            muegge_v += 1
        if not (-2 < physico.logp < 5):
            muegge_v += 1
        if physico.tpsa > 150:
            muegge_v += 1
        if physico.num_rings > 7:
            muegge_v += 1
        if physico.num_h_donors > 5:
            muegge_v += 1
        if physico.num_h_acceptors > 10:
            muegge_v += 1
        if physico.num_rotatable_bonds > 15:
            muegge_v += 1
        muegge_passes = muegge_v <= 1
        
        # Lead-likeness (Teague & Oprea)
        lead_v = 0
        if not (250 < physico.molecular_weight < 350):
            lead_v += 1
        if not (-1 < physico.logp < 3):
            lead_v += 1
        if physico.num_rotatable_bonds > 7:
            lead_v += 1
        lead_like = lead_v == 0
        
        # Calculate composite drug-likeness score
        filters_passed = sum([
            lipinski_passes, veber_passes, ghose_passes,
            egan_passes, muegge_passes
        ])
        dl_score = filters_passed / 5.0
        
        return DrugLikenessAssessment(
            lipinski_passes=lipinski_passes,
            lipinski_violations=lipinski_v,
            veber_passes=veber_passes,
            veber_violations=veber_v,
            ghose_passes=ghose_passes,
            ghose_violations=ghose_v,
            egan_passes=egan_passes,
            egan_violations=egan_v,
            muegge_passes=muegge_passes,
            muegge_violations=muegge_v,
            lead_like=lead_like,
            lead_violations=lead_v,
            drug_likeness_score=dl_score,
            violations=violations,
        )
    
    def _calculate_overall(
        self,
        physico: PhysicochemicalProperties,
        absorption: AbsorptionPrediction,
        distribution: DistributionPrediction,
        metabolism: MetabolismPrediction,
        excretion: ExcretionPrediction,
        toxicity: ToxicityPrediction,
        drug_likeness: DrugLikenessAssessment,
    ) -> Tuple[float, str, List[str], List[str]]:
        """Calculate overall ADMET score and generate recommendations."""
        concerns = []
        recommendations = []
        
        # Score components (0-1 each)
        scores = []
        
        # Absorption score
        if absorption.human_intestinal_absorption == "High":
            scores.append(1.0)
        elif absorption.human_intestinal_absorption == "Medium":
            scores.append(0.6)
        else:
            scores.append(0.3)
            concerns.append("Poor oral absorption predicted")
            recommendations.append("Consider formulation strategies or alternative routes")
        
        # Distribution score
        scores.append(distribution.bbb_probability)
        if distribution.ppb_class == "High":
            concerns.append("High plasma protein binding may limit free drug concentration")
        
        # Metabolism score
        if metabolism.metabolic_stability == "Stable":
            scores.append(1.0)
        elif metabolism.metabolic_stability == "Moderate":
            scores.append(0.6)
        else:
            scores.append(0.3)
            concerns.append("Metabolic instability may affect half-life")
            recommendations.append("Consider metabolic blocking groups")
        
        # Toxicity score
        if toxicity.toxicity_risk == "Low":
            scores.append(1.0)
        elif toxicity.toxicity_risk == "Medium":
            scores.append(0.6)
            concerns.append(f"{toxicity.num_alerts} structural alert(s) detected")
        else:
            scores.append(0.2)
            concerns.append("Significant toxicity concerns")
            recommendations.append("Remove flagged substructures if possible")
        
        # Drug-likeness score
        scores.append(drug_likeness.drug_likeness_score)
        if not drug_likeness.lipinski_passes:
            concerns.append(f"Lipinski violations: {drug_likeness.lipinski_violations}")
        
        # Calculate overall
        overall = sum(scores) / len(scores)
        
        if overall >= 0.7:
            assessment = "Favorable"
        elif overall >= 0.4:
            assessment = "Moderate concerns"
        else:
            assessment = "Significant concerns"
        
        return overall, assessment, concerns, recommendations
    
    def predict_quick(self, smiles: str) -> Dict[str, Any]:
        """
        Quick ADMET prediction returning simplified results.
        
        Useful for batch processing or API responses.
        """
        report = self.predict(smiles)
        
        return {
            "smiles": smiles,
            "overall_score": round(report.overall_score, 2),
            "assessment": report.overall_assessment,
            "absorption": report.absorption.human_intestinal_absorption,
            "bbb_permeant": report.distribution.bbb_permeant,
            "metabolic_stability": report.metabolism.metabolic_stability,
            "toxicity_risk": report.toxicity.toxicity_risk,
            "num_alerts": report.toxicity.num_alerts,
            "lipinski_passes": report.drug_likeness.lipinski_passes,
            "key_concerns": report.key_concerns,
        }


# Convenience function
def predict_admet(smiles: str, name: Optional[str] = None) -> ADMETReport:
    """
    Predict ADMET properties for a compound.
    
    Args:
        smiles: SMILES string
        name: Optional compound name
        
    Returns:
        Complete ADMETReport
    """
    predictor = ADMETPredictor()
    return predictor.predict(smiles, name)
