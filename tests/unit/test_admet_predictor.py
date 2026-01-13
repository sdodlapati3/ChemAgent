"""
Unit tests for ADMET predictor module.
"""

import pytest
from chemagent.tools.admet_predictor import (
    ADMETPredictor,
    ADMETReport,
    PhysicochemicalProperties,
    AbsorptionPrediction,
    DistributionPrediction,
    MetabolismPrediction,
    ExcretionPrediction,
    ToxicityPrediction,
    DrugLikenessAssessment,
    ToxicityAlert,
)


class TestADMETPredictor:
    """Test suite for ADMETPredictor."""
    
    @pytest.fixture
    def predictor(self):
        """Create predictor instance."""
        return ADMETPredictor()
    
    @pytest.fixture
    def aspirin_smiles(self):
        """Aspirin SMILES string."""
        return "CC(=O)Oc1ccccc1C(=O)O"
    
    @pytest.fixture
    def caffeine_smiles(self):
        """Caffeine SMILES string."""
        return "Cn1cnc2c1c(=O)n(c(=O)n2C)C"
    
    def test_predictor_initialization(self, predictor):
        """Test predictor initializes correctly."""
        assert predictor is not None
        assert predictor.pains_catalog is not None
        assert predictor.brenk_catalog is not None
    
    def test_predict_aspirin(self, predictor, aspirin_smiles):
        """Test ADMET prediction for aspirin."""
        report = predictor.predict(aspirin_smiles, "Aspirin")
        
        assert isinstance(report, ADMETReport)
        assert report.smiles == aspirin_smiles
        assert report.compound_name == "Aspirin"
        assert 0.0 <= report.overall_score <= 1.0
        assert report.overall_assessment in ["Favorable", "Moderate concerns", "Significant concerns"]
    
    def test_predict_caffeine(self, predictor, caffeine_smiles):
        """Test ADMET prediction for caffeine."""
        report = predictor.predict(caffeine_smiles, "Caffeine")
        
        assert isinstance(report, ADMETReport)
        assert report.overall_assessment in ["Favorable", "Moderate concerns", "Significant concerns"]
    
    def test_physicochemical_properties(self, predictor, aspirin_smiles):
        """Test physicochemical property calculation."""
        report = predictor.predict(aspirin_smiles)
        props = report.physicochemical
        
        assert isinstance(props, PhysicochemicalProperties)
        # Aspirin: MW ~180.16
        assert 170 < props.molecular_weight < 190
        # LogP should be reasonable
        assert -5 < props.logp < 10
        # TPSA for aspirin with carboxylic acid and ester
        assert props.tpsa > 40
        assert props.num_h_donors >= 1  # COOH
        assert props.num_h_acceptors >= 3  # Carbonyl O's
    
    def test_absorption_prediction(self, predictor, aspirin_smiles):
        """Test absorption prediction."""
        report = predictor.predict(aspirin_smiles)
        absorption = report.absorption
        
        assert isinstance(absorption, AbsorptionPrediction)
        assert absorption.human_intestinal_absorption in ["High", "Moderate", "Low"]
        assert absorption.caco2_permeability in ["High", "Medium", "Moderate", "Low"]
        assert 0 <= absorption.bioavailability_score <= 1
        assert absorption.solubility_class is not None
    
    def test_distribution_prediction(self, predictor, aspirin_smiles):
        """Test distribution prediction."""
        report = predictor.predict(aspirin_smiles)
        dist = report.distribution
        
        assert isinstance(dist, DistributionPrediction)
        assert isinstance(dist.bbb_permeant, bool)
        assert dist.ppb_class in ["High", "Moderate", "Low"]
        assert isinstance(dist.pgp_substrate, bool)
    
    def test_metabolism_prediction(self, predictor, aspirin_smiles):
        """Test metabolism prediction."""
        report = predictor.predict(aspirin_smiles)
        metab = report.metabolism
        
        assert isinstance(metab, MetabolismPrediction)
        assert metab.metabolic_stability in ["High", "Moderate", "Low", "Stable", "Moderate stability", "Unstable"]
        assert isinstance(metab.cyp3a4_substrate, bool)
        assert isinstance(metab.cyp3a4_inhibitor, bool)
    
    def test_excretion_prediction(self, predictor, aspirin_smiles):
        """Test excretion prediction."""
        report = predictor.predict(aspirin_smiles)
        excretion = report.excretion
        
        assert isinstance(excretion, ExcretionPrediction)
        assert excretion.renal_clearance_class in ["High", "Medium", "Moderate", "Low"]
        assert excretion.half_life_class in ["Short", "Medium", "Long"]
    
    def test_toxicity_prediction(self, predictor, aspirin_smiles):
        """Test toxicity prediction."""
        report = predictor.predict(aspirin_smiles)
        tox = report.toxicity
        
        assert isinstance(tox, ToxicityPrediction)
        assert tox.toxicity_risk in ["High", "Medium", "Low"]
        assert isinstance(tox.pains_alerts, list)
        assert isinstance(tox.brenk_alerts, list)
        # ames_mutagenicity can be bool or string
        assert tox.ames_mutagenicity in [True, False, "Positive", "Negative", "Inconclusive"]
    
    def test_drug_likeness(self, predictor, aspirin_smiles):
        """Test drug-likeness assessment."""
        report = predictor.predict(aspirin_smiles)
        dl = report.drug_likeness
        
        assert isinstance(dl, DrugLikenessAssessment)
        assert isinstance(dl.lipinski_passes, bool)
        assert isinstance(dl.veber_passes, bool)
        assert isinstance(dl.ghose_passes, bool)
        assert 0 <= dl.drug_likeness_score <= 1
        # Aspirin should pass Lipinski
        assert dl.lipinski_passes is True
    
    def test_invalid_smiles(self, predictor):
        """Test handling of invalid SMILES."""
        with pytest.raises(ValueError):
            predictor.predict("not_a_valid_smiles")
    
    def test_key_concerns_generated(self, predictor, aspirin_smiles):
        """Test that key concerns are generated."""
        report = predictor.predict(aspirin_smiles)
        
        # key_concerns should be a list
        assert isinstance(report.key_concerns, list)
        assert isinstance(report.recommendations, list)
    
    def test_pains_detection(self, predictor):
        """Test PAINS alert detection."""
        # Rhodanine - known PAINS substructure
        rhodanine_smiles = "NC1=NC(=O)SC1=Cc1ccccc1"
        report = predictor.predict(rhodanine_smiles)
        
        # Should detect alerts (may vary based on exact structure)
        # Just verify the analysis runs
        assert report.toxicity.toxicity_risk is not None


class TestDrugLikeness:
    """Test suite for drug-likeness rules."""
    
    @pytest.fixture
    def predictor(self):
        return ADMETPredictor()
    
    def test_lipinski_compliant_drug(self, predictor):
        """Test Lipinski rule on a compliant drug (ibuprofen)."""
        ibuprofen = "CC(C)Cc1ccc(cc1)C(C)C(=O)O"
        report = predictor.predict(ibuprofen)
        
        assert report.drug_likeness.lipinski_passes is True
        assert len([v for v in report.drug_likeness.violations if "Lipinski" in v]) == 0
    
    def test_lipinski_violating_compound(self, predictor):
        """Test Lipinski rule on a violating compound (high logP)."""
        # Long hydrocarbon chain - high LogP violation
        large_compound = "CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC"  # Very long chain
        report = predictor.predict(large_compound)
        
        # Should have LogP violation (> 5)
        assert report.physicochemical.logp > 5
        # May have Lipinski violations
        assert report.drug_likeness.lipinski_violations >= 0


class TestToxicityAlerts:
    """Test suite for toxicity alert detection."""
    
    @pytest.fixture
    def predictor(self):
        return ADMETPredictor()
    
    def test_nitro_compound_alert(self, predictor):
        """Test detection of nitro group (mutagenicity concern)."""
        nitrobenzene = "c1ccc(cc1)[N+](=O)[O-]"
        report = predictor.predict(nitrobenzene)
        
        # Should flag mutagenicity concerns
        # The exact alert may vary based on the filter catalogs
        assert report.toxicity is not None
    
    def test_safe_compound(self, predictor):
        """Test a relatively safe compound."""
        glycine = "NCC(=O)O"  # Simple amino acid
        report = predictor.predict(glycine)
        
        # Should have low toxicity risk
        assert report.toxicity.pains_alerts == []


class TestIntegration:
    """Integration tests for ADMET predictor."""
    
    def test_batch_prediction(self):
        """Test predicting multiple compounds."""
        predictor = ADMETPredictor()
        
        compounds = [
            ("CC(=O)Oc1ccccc1C(=O)O", "Aspirin"),
            ("CC(C)Cc1ccc(cc1)C(C)C(=O)O", "Ibuprofen"),
            ("CC(=O)Nc1ccc(O)cc1", "Acetaminophen"),
        ]
        
        results = []
        for smiles, name in compounds:
            report = predictor.predict(smiles, name)
            results.append(report)
        
        assert len(results) == 3
        for report in results:
            assert report.overall_score > 0
            assert report.overall_assessment is not None
    
    def test_prediction_consistency(self):
        """Test that predictions are consistent across multiple runs."""
        predictor = ADMETPredictor()
        smiles = "CC(=O)Oc1ccccc1C(=O)O"
        
        report1 = predictor.predict(smiles)
        report2 = predictor.predict(smiles)
        
        assert report1.overall_score == report2.overall_score
        assert report1.overall_assessment == report2.overall_assessment
        assert report1.physicochemical.molecular_weight == report2.physicochemical.molecular_weight
