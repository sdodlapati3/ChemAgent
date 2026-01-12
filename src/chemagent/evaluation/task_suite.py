"""
Evaluation Task Suite for ChemAgent.

Provides a collection of evaluation tasks organized by category:
- Target validation queries (Open Targets)
- Compound lookups (ChEMBL)
- Property calculations (RDKit)
- Similarity searches
- Multi-step workflows

Each task defines:
- Query text
- Expected assertions (constraints to check)
- Difficulty level
- Category
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .assertions import (
    Assertion,
    HasProvenance,
    ContainsEntity,
    ContainsAnyEntity,
    HasNumericValue,
    HasAssociationScore,
    HasStructuredData,
    SourceIs,
    ResponseLength,
    NoHallucination,
)

logger = logging.getLogger(__name__)


class TaskCategory(Enum):
    """Categories of evaluation tasks."""
    TARGET_VALIDATION = "target_validation"
    DISEASE_ASSOCIATION = "disease_association"
    COMPOUND_LOOKUP = "compound_lookup"
    PROPERTY_CALCULATION = "property_calculation"
    SIMILARITY_SEARCH = "similarity_search"
    BIOACTIVITY = "bioactivity"
    MULTI_STEP = "multi_step"
    EDGE_CASE = "edge_case"


class TaskDifficulty(Enum):
    """Difficulty levels."""
    EASY = "easy"           # Single tool, direct query
    MEDIUM = "medium"       # May need entity resolution
    HARD = "hard"           # Multi-step, ambiguous
    EXPERT = "expert"       # Complex workflow


@dataclass
class EvaluationTask:
    """A single evaluation task."""
    task_id: str
    query: str
    category: TaskCategory
    difficulty: TaskDifficulty
    assertions: List[Assertion]
    description: str = ""
    expected_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "query": self.query,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "description": self.description,
            "expected_tools": self.expected_tools,
            "assertions": [a.name for a in self.assertions],
            "metadata": self.metadata
        }


class TaskSuite:
    """Collection of evaluation tasks."""
    
    def __init__(self, name: str = "default"):
        self.name = name
        self.tasks: List[EvaluationTask] = []
    
    def add_task(self, task: EvaluationTask):
        """Add a task to the suite."""
        self.tasks.append(task)
    
    def get_by_category(self, category: TaskCategory) -> List[EvaluationTask]:
        """Get tasks by category."""
        return [t for t in self.tasks if t.category == category]
    
    def get_by_difficulty(self, difficulty: TaskDifficulty) -> List[EvaluationTask]:
        """Get tasks by difficulty."""
        return [t for t in self.tasks if t.difficulty == difficulty]
    
    def __len__(self) -> int:
        return len(self.tasks)
    
    def __iter__(self):
        return iter(self.tasks)
    
    def summary(self) -> Dict[str, Any]:
        """Get summary statistics."""
        by_category = {}
        by_difficulty = {}
        
        for task in self.tasks:
            cat = task.category.value
            diff = task.difficulty.value
            by_category[cat] = by_category.get(cat, 0) + 1
            by_difficulty[diff] = by_difficulty.get(diff, 0) + 1
        
        return {
            "name": self.name,
            "total_tasks": len(self.tasks),
            "by_category": by_category,
            "by_difficulty": by_difficulty
        }
    
    def save(self, path: str):
        """Save task suite to JSON file."""
        data = {
            "name": self.name,
            "tasks": [t.to_dict() for t in self.tasks]
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.tasks)} tasks to {path}")


def create_default_task_suite() -> TaskSuite:
    """Create the default evaluation task suite."""
    suite = TaskSuite("chemagent_v1")
    
    # =========================================================================
    # Target Validation Tasks (Open Targets)
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="tv_001",
        query="What evidence links EGFR to lung cancer?",
        category=TaskCategory.TARGET_VALIDATION,
        difficulty=TaskDifficulty.EASY,
        description="Basic target-disease evidence query",
        expected_tools=["opentargets_search_target", "opentargets_get_associations"],
        assertions=[
            HasProvenance(),
            SourceIs("Open Targets"),
            ContainsEntity("EGFR"),
            ContainsAnyEntity(["lung cancer", "NSCLC", "adenocarcinoma"]),
            HasAssociationScore(),
            NoHallucination(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="tv_002",
        query="Is BRAF a good target for melanoma treatment?",
        category=TaskCategory.TARGET_VALIDATION,
        difficulty=TaskDifficulty.MEDIUM,
        description="Target validation with therapeutic context",
        expected_tools=["opentargets_search_target", "opentargets_get_associations"],
        assertions=[
            HasProvenance(),
            ContainsEntity("BRAF"),
            ContainsAnyEntity(["melanoma", "skin cancer"]),
            HasAssociationScore(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="tv_003",
        query="What genetic evidence supports targeting TP53 in cancer?",
        category=TaskCategory.TARGET_VALIDATION,
        difficulty=TaskDifficulty.MEDIUM,
        description="Specific evidence type query",
        expected_tools=["opentargets_search_target", "opentargets_get_evidence"],
        assertions=[
            HasProvenance(),
            ContainsAnyEntity(["TP53", "p53"]),
            ContainsAnyEntity(["genetic", "mutation", "somatic"]),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="tv_004",
        query="What diseases are associated with KRAS mutations?",
        category=TaskCategory.DISEASE_ASSOCIATION,
        difficulty=TaskDifficulty.EASY,
        description="Target to disease associations",
        expected_tools=["opentargets_search_target", "opentargets_get_associations"],
        assertions=[
            HasProvenance(),
            ContainsEntity("KRAS"),
            HasAssociationScore(),
            HasStructuredData(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="tv_005",
        query="What are the known drugs targeting HER2?",
        category=TaskCategory.TARGET_VALIDATION,
        difficulty=TaskDifficulty.MEDIUM,
        description="Target drugs query",
        expected_tools=["opentargets_search_target"],
        assertions=[
            HasProvenance(),
            ContainsAnyEntity(["HER2", "ERBB2"]),
            ContainsAnyEntity(["trastuzumab", "herceptin", "pertuzumab", "lapatinib"]),
        ]
    ))
    
    # =========================================================================
    # Compound Lookup Tasks (ChEMBL)
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="cl_001",
        query="Tell me about aspirin",
        category=TaskCategory.COMPOUND_LOOKUP,
        difficulty=TaskDifficulty.EASY,
        description="Basic compound lookup by name",
        expected_tools=["chembl_search_by_name"],
        assertions=[
            HasProvenance(),
            ContainsEntity("aspirin"),
            HasNumericValue(min_count=2),  # MW, LogP
            NoHallucination(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="cl_002",
        query="What is CHEMBL25?",
        category=TaskCategory.COMPOUND_LOOKUP,
        difficulty=TaskDifficulty.EASY,
        description="Compound lookup by ChEMBL ID",
        expected_tools=["chembl_get_compound"],
        assertions=[
            HasProvenance(),
            ContainsEntity("CHEMBL25"),
            HasNumericValue(min_count=1),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="cl_003",
        query="What are the properties of metformin?",
        category=TaskCategory.COMPOUND_LOOKUP,
        difficulty=TaskDifficulty.EASY,
        description="Compound properties query",
        expected_tools=["chembl_search_by_name"],
        assertions=[
            HasProvenance(),
            ContainsEntity("metformin"),
            HasNumericValue(min_count=2),
            HasStructuredData(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="cl_004",
        query="Find information about ibuprofen including its molecular weight",
        category=TaskCategory.COMPOUND_LOOKUP,
        difficulty=TaskDifficulty.EASY,
        description="Specific property request",
        expected_tools=["chembl_search_by_name"],
        assertions=[
            ContainsEntity("ibuprofen"),
            ContainsAnyEntity(["molecular weight", "MW", "206"]),  # MW ~206
            HasNumericValue(min_count=1),
        ]
    ))
    
    # =========================================================================
    # Property Calculation Tasks (RDKit)
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="pc_001",
        query="Calculate properties for CCO (ethanol)",
        category=TaskCategory.PROPERTY_CALCULATION,
        difficulty=TaskDifficulty.EASY,
        description="Basic property calculation from SMILES",
        expected_tools=["rdkit_calc_properties"],
        assertions=[
            HasNumericValue(min_count=3),
            ContainsAnyEntity(["molecular weight", "MW", "LogP"]),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="pc_002",
        query="Is CC(=O)Oc1ccccc1C(=O)O drug-like? Check Lipinski's rules",
        category=TaskCategory.PROPERTY_CALCULATION,
        difficulty=TaskDifficulty.MEDIUM,
        description="Lipinski rule of 5 check",
        expected_tools=["rdkit_calc_lipinski"],
        assertions=[
            HasNumericValue(min_count=4),  # 4 Lipinski properties
            ContainsAnyEntity(["Lipinski", "drug-like", "Rule of 5"]),
        ]
    ))
    
    # =========================================================================
    # Similarity Search Tasks
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="ss_001",
        query="Find compounds similar to aspirin",
        category=TaskCategory.SIMILARITY_SEARCH,
        difficulty=TaskDifficulty.MEDIUM,
        description="Similarity search by compound name",
        expected_tools=["chembl_search_by_name", "chembl_similarity_search"],
        assertions=[
            HasProvenance(),
            ContainsEntity("aspirin"),
            ContainsAnyEntity(["similar", "analog", "similarity"]),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="ss_002",
        query="Find analogs of ibuprofen with similarity > 70%",
        category=TaskCategory.SIMILARITY_SEARCH,
        difficulty=TaskDifficulty.MEDIUM,
        description="Similarity search with threshold",
        expected_tools=["chembl_search_by_name", "chembl_similarity_search"],
        assertions=[
            HasProvenance(),
            ContainsEntity("ibuprofen"),
            HasNumericValue(min_count=1),
        ]
    ))
    
    # =========================================================================
    # Bioactivity Tasks
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="ba_001",
        query="What are the targets of aspirin?",
        category=TaskCategory.BIOACTIVITY,
        difficulty=TaskDifficulty.MEDIUM,
        description="Compound targets query",
        expected_tools=["chembl_search_by_name", "chembl_get_activities"],
        assertions=[
            HasProvenance(),
            ContainsEntity("aspirin"),
            ContainsAnyEntity(["COX", "cyclooxygenase", "target"]),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="ba_002",
        query="What is the bioactivity profile of CHEMBL25?",
        category=TaskCategory.BIOACTIVITY,
        difficulty=TaskDifficulty.EASY,
        description="Bioactivity by ChEMBL ID",
        expected_tools=["chembl_get_activities"],
        assertions=[
            HasProvenance(),
            ContainsEntity("CHEMBL25"),
            ContainsAnyEntity(["IC50", "activity", "target", "assay"]),
        ]
    ))
    
    # =========================================================================
    # Multi-Step Workflow Tasks
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="ms_001",
        query="What evidence links EGFR to lung cancer, and what drugs target it?",
        category=TaskCategory.MULTI_STEP,
        difficulty=TaskDifficulty.HARD,
        description="Combined target validation and drug query",
        expected_tools=["opentargets_search_target", "opentargets_get_associations"],
        assertions=[
            HasProvenance(),
            ContainsEntity("EGFR"),
            ContainsAnyEntity(["lung cancer", "NSCLC"]),
            ContainsAnyEntity(["erlotinib", "gefitinib", "osimertinib", "drug"]),
            HasAssociationScore(),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="ms_002",
        query="Tell me about aspirin, its properties, and what it targets",
        category=TaskCategory.MULTI_STEP,
        difficulty=TaskDifficulty.HARD,
        description="Compound info + properties + targets",
        expected_tools=["chembl_search_by_name", "chembl_get_activities"],
        assertions=[
            HasProvenance(),
            ContainsEntity("aspirin"),
            HasNumericValue(min_count=2),
            ContainsAnyEntity(["COX", "target", "activity"]),
        ]
    ))
    
    # =========================================================================
    # Edge Cases
    # =========================================================================
    
    suite.add_task(EvaluationTask(
        task_id="ec_001",
        query="What is xyz123_not_a_compound?",
        category=TaskCategory.EDGE_CASE,
        difficulty=TaskDifficulty.EASY,
        description="Unknown compound handling",
        expected_tools=["chembl_search_by_name"],
        assertions=[
            ResponseLength(min_words=5, max_words=200),
            # Should gracefully handle not found
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="ec_002",
        query="Calculate properties",  # Missing SMILES
        category=TaskCategory.EDGE_CASE,
        difficulty=TaskDifficulty.EASY,
        description="Incomplete query handling",
        assertions=[
            ResponseLength(min_words=5, max_words=200),
        ]
    ))
    
    suite.add_task(EvaluationTask(
        task_id="ec_003",
        query="What is the meaning of life?",
        category=TaskCategory.EDGE_CASE,
        difficulty=TaskDifficulty.EASY,
        description="Off-topic query handling",
        assertions=[
            ResponseLength(min_words=5, max_words=200),
        ]
    ))
    
    logger.info(f"Created task suite with {len(suite)} tasks")
    return suite


def load_task_suite(path: str) -> TaskSuite:
    """Load task suite from JSON file."""
    # This would reconstruct assertions from names
    # For now, return default suite
    return create_default_task_suite()
