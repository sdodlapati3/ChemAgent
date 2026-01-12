#!/usr/bin/env python3
"""
Frontend Integration Test Suite
Tests ChemAgent as if interacting from UI/API with diverse queries.
Simulates real user interactions across all complexity levels.
"""

import json
import time
import random
import asyncio
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

# Test queries organized by complexity
TEST_QUERIES = {
    # Level 1: Simple Lookups (should be fast, cached)
    "simple": [
        "What is CHEMBL25?",
        "Look up aspirin",
        "Find information about ibuprofen",
        "What is caffeine?",
        "Tell me about metformin",
        "Look up CHEMBL1",
        "What is acetaminophen?",
        "Find compound CHEMBL192",
        "What is penicillin?",
        "Look up omeprazole",
    ],
    
    # Level 2: Property Queries
    "properties": [
        "What is the molecular weight of aspirin?",
        "Get LogP for CHEMBL25",
        "Show properties of ibuprofen",
        "What are the properties of metformin?",
        "Get molecular formula for caffeine",
        "What is the SMILES of aspirin?",
        "Show druglikeness of CHEMBL1",
        "Get all properties for acetaminophen",
        "What is the polar surface area of metformin?",
        "Show Lipinski properties for ibuprofen",
    ],
    
    # Level 3: Similarity Searches
    "similarity": [
        "Find compounds similar to aspirin",
        "What molecules are similar to ibuprofen?",
        "Search for structures like metformin",
        "Find similar compounds to CHEMBL25 with 0.8 threshold",
        "Show molecules resembling caffeine",
        "Find structural analogs of acetaminophen",
        "Search for aspirin-like compounds",
        "What compounds look like penicillin?",
        "Find similar structures to omeprazole",
        "Get compounds with similar structure to CHEMBL1",
    ],
    
    # Level 4: Target Queries
    "targets": [
        "What are the targets of aspirin?",
        "Find targets for metformin",
        "What does ibuprofen bind to?",
        "Get protein targets for CHEMBL25",
        "Which enzymes does caffeine inhibit?",
        "Find targets of acetaminophen",
        "What receptors bind CHEMBL1?",
        "Show targets for omeprazole",
        "What pathways is aspirin involved in?",
        "Find molecular targets of ibuprofen",
    ],
    
    # Level 5: Multi-step Workflows
    "workflows": [
        "Find similar compounds to aspirin and get their targets",
        "Get properties and targets for CHEMBL25",
        "Look up caffeine and find compounds similar to it",
        "Get all targets for metformin and find other compounds binding to those targets",
        "Find compounds similar to ibuprofen and show their properties",
        "What are aspirin's targets and what else binds to them?",
        "Find COX-2 inhibitors and get their druglikeness",
        "Compare properties of aspirin and ibuprofen",
        "Find similar compounds to metformin with MW < 300",
        "Get targets of CHEMBL25 and find compounds with higher affinity",
    ],
    
    # Level 6: Complex Research Queries
    "research": [
        "What compounds target both COX-1 and COX-2?",
        "Find kinase inhibitors similar to imatinib",
        "Get all FDA approved compounds targeting EGFR",
        "Find compounds with LogP between 2 and 5 and MW < 500",
        "What are the most selective COX-2 inhibitors?",
        "Find GPCR ligands similar to metformin",
        "Get compounds that pass Lipinski's rule of five",
        "What antibiotics are similar to penicillin?",
        "Find anti-inflammatory compounds with good oral bioavailability",
        "Compare binding affinities of aspirin analogs to COX enzymes",
    ],
    
    # Level 7: Edge Cases and Variations
    "edge_cases": [
        "CHEMBL25",  # Just an ID
        "aspirin targets",  # Abbreviated
        "similar to CC(=O)OC1=CC=CC=C1C(=O)O",  # Raw SMILES
        "MW of caffeine",  # Abbreviated property
        "what's ibuprofen?",  # Casual
        "tell me everything about metformin",  # Broad
        "aspirin vs ibuprofen",  # Comparison shorthand
        "CHEMBL1 properties targets",  # Keyword style
        "find drug for headache",  # Indication-based
        "anti inflammatory compounds",  # Category search
    ],
    
    # Level 8: Database-specific Queries (BindingDB, UniProt)
    "database_specific": [
        "Find binding data for aspirin in BindingDB",
        "Get UniProt information for human COX-2",
        "What is the binding affinity of ibuprofen to COX-1?",
        "Look up P00750 in UniProt",
        "Find IC50 values for CHEMBL25",
        "Get protein sequence for cyclooxygenase-2",
        "What is the Ki of metformin for its targets?",
        "Find all assay data for caffeine",
        "Get binding constants from BindingDB for omeprazole",
        "Look up AMPK in UniProt and find its inhibitors",
    ],
}

# Additional stress test queries for high load
STRESS_QUERIES = [
    "What is {compound}?",
    "Find compounds similar to {compound}",
    "Get properties of {compound}",
    "What targets does {compound} bind?",
    "{compound} molecular weight",
    "Find {compound} analogs with better druglikeness",
]

COMPOUND_NAMES = [
    "aspirin", "ibuprofen", "metformin", "caffeine", "acetaminophen",
    "omeprazole", "penicillin", "amoxicillin", "lisinopril", "atorvastatin",
    "simvastatin", "metoprolol", "amlodipine", "gabapentin", "losartan",
    "clopidogrel", "warfarin", "albuterol", "fluticasone", "sertraline",
]


@dataclass
class QueryResult:
    """Result of a single query execution"""
    query: str
    category: str
    success: bool
    execution_time: float
    response_length: int
    has_formatted_answer: bool
    error: Optional[str] = None
    raw_response: Optional[Dict] = None


@dataclass
class TestReport:
    """Aggregated test results"""
    total_queries: int = 0
    successful: int = 0
    failed: int = 0
    total_time: float = 0.0
    avg_response_time: float = 0.0
    results_by_category: Dict[str, Dict] = field(default_factory=dict)
    errors: List[Dict] = field(default_factory=list)
    
    def add_result(self, result: QueryResult):
        self.total_queries += 1
        self.total_time += result.execution_time
        
        if result.success:
            self.successful += 1
        else:
            self.failed += 1
            self.errors.append({
                "query": result.query,
                "category": result.category,
                "error": result.error
            })
        
        # Track by category
        if result.category not in self.results_by_category:
            self.results_by_category[result.category] = {
                "total": 0, "success": 0, "failed": 0, 
                "total_time": 0.0, "queries": []
            }
        
        cat = self.results_by_category[result.category]
        cat["total"] += 1
        cat["total_time"] += result.execution_time
        if result.success:
            cat["success"] += 1
        else:
            cat["failed"] += 1
        cat["queries"].append({
            "query": result.query[:50] + "..." if len(result.query) > 50 else result.query,
            "success": result.success,
            "time": result.execution_time
        })
    
    def calculate_averages(self):
        if self.total_queries > 0:
            self.avg_response_time = self.total_time / self.total_queries
        for cat in self.results_by_category.values():
            if cat["total"] > 0:
                cat["avg_time"] = cat["total_time"] / cat["total"]
                cat["success_rate"] = cat["success"] / cat["total"] * 100
    
    def print_summary(self):
        self.calculate_averages()
        
        print("\n" + "="*70)
        print("FRONTEND INTEGRATION TEST REPORT")
        print("="*70)
        print(f"\nOverall Results:")
        print(f"  Total Queries:     {self.total_queries}")
        print(f"  Successful:        {self.successful} ({self.successful/self.total_queries*100:.1f}%)")
        print(f"  Failed:            {self.failed} ({self.failed/self.total_queries*100:.1f}%)")
        print(f"  Total Time:        {self.total_time:.2f}s")
        print(f"  Avg Response Time: {self.avg_response_time:.2f}s")
        
        print(f"\nResults by Category:")
        print("-"*70)
        print(f"{'Category':<20} {'Total':>8} {'Success':>10} {'Failed':>8} {'Rate':>8} {'Avg Time':>10}")
        print("-"*70)
        
        for cat_name, cat_data in sorted(self.results_by_category.items()):
            print(f"{cat_name:<20} {cat_data['total']:>8} {cat_data['success']:>10} "
                  f"{cat_data['failed']:>8} {cat_data.get('success_rate', 0):>7.1f}% "
                  f"{cat_data.get('avg_time', 0):>9.2f}s")
        
        if self.errors:
            print(f"\nFailed Queries ({len(self.errors)}):")
            print("-"*70)
            for i, err in enumerate(self.errors[:10]):  # Show first 10
                print(f"  {i+1}. [{err['category']}] {err['query'][:50]}...")
                print(f"     Error: {err['error'][:80]}...")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        print("="*70)


class FrontendTester:
    """Simulates frontend interactions with ChemAgent"""
    
    def __init__(self, use_api=False, api_url="http://localhost:8000"):
        self.use_api = use_api
        self.api_url = api_url
        self.agent = None
        self.report = TestReport()
        
        if not use_api:
            # Initialize ChemAgent facade (same as UI does)
            from chemagent import ChemAgent
            self.agent = ChemAgent()
    
    def execute_query(self, query: str, category: str, 
                      rate_limit_delay: float = 0.5) -> QueryResult:
        """Execute a single query and measure results"""
        start_time = time.time()
        success = False
        error = None
        response_length = 0
        has_formatted = False
        raw_response = None
        
        # Add delay between queries to avoid rate limits
        time.sleep(rate_limit_delay)
        
        try:
            if self.use_api:
                import requests
                resp = requests.post(
                    f"{self.api_url}/api/v1/query",
                    json={"query": query},
                    timeout=60
                )
                raw_response = resp.json()
                success = raw_response.get("status") == "success"
                
                # Check for formatted answer
                result = raw_response.get("result", {})
                if isinstance(result, dict):
                    answer = result.get("answer", "")
                    has_formatted = bool(answer) and len(answer) > 10
                    response_length = len(str(answer))
                else:
                    response_length = len(str(result))
                    has_formatted = response_length > 10
                    
            else:
                # Use ChemAgent facade directly (like UI does)
                result = self.agent.query(query)
                raw_response = {"result": result}
                
                # Check response quality
                if result:
                    response_length = len(str(result))
                    # Check for markdown formatting or structured content
                    has_formatted = (
                        "##" in str(result) or 
                        "**" in str(result) or
                        "- " in str(result) or
                        len(str(result)) > 50
                    )
                    success = True
                else:
                    error = "Empty response"
                    
        except Exception as e:
            error = str(e)
            traceback.print_exc()
        
        execution_time = time.time() - start_time
        
        return QueryResult(
            query=query,
            category=category,
            success=success,
            execution_time=execution_time,
            response_length=response_length,
            has_formatted_answer=has_formatted,
            error=error,
            raw_response=raw_response
        )
    
    def run_category_tests(self, category: str, queries: List[str], 
                           verbose: bool = True) -> List[QueryResult]:
        """Run all queries in a category"""
        results = []
        
        if verbose:
            print(f"\n{'='*60}")
            print(f"Testing Category: {category.upper()}")
            print(f"{'='*60}")
        
        for i, query in enumerate(queries):
            if verbose:
                print(f"  [{i+1}/{len(queries)}] {query[:50]}...", end=" ", flush=True)
            
            result = self.execute_query(query, category)
            results.append(result)
            self.report.add_result(result)
            
            if verbose:
                status = "✓" if result.success else "✗"
                print(f"{status} ({result.execution_time:.2f}s)")
                
                if not result.success and result.error:
                    print(f"       Error: {result.error[:60]}...")
        
        return results
    
    def run_all_tests(self, categories: Optional[List[str]] = None, 
                      verbose: bool = True) -> TestReport:
        """Run tests across all or specified categories"""
        
        if categories is None:
            categories = list(TEST_QUERIES.keys())
        
        print("\n" + "#"*70)
        print("# CHEMAGENT FRONTEND INTEGRATION TEST")
        print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"# Mode: {'API' if self.use_api else 'Direct (Facade)'}")
        print("#"*70)
        
        for category in categories:
            if category in TEST_QUERIES:
                self.run_category_tests(category, TEST_QUERIES[category], verbose)
        
        self.report.print_summary()
        return self.report
    
    def run_stress_test(self, num_queries: int = 100, 
                        parallel: bool = True, 
                        max_workers: int = 5) -> TestReport:
        """Run stress test with generated queries"""
        
        print("\n" + "#"*70)
        print("# STRESS TEST")
        print(f"# Queries: {num_queries}, Parallel: {parallel}, Workers: {max_workers}")
        print("#"*70)
        
        # Generate random queries
        queries = []
        for _ in range(num_queries):
            template = random.choice(STRESS_QUERIES)
            compound = random.choice(COMPOUND_NAMES)
            queries.append((template.format(compound=compound), "stress"))
        
        if parallel:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self.execute_query, q, cat): (q, cat) 
                    for q, cat in queries
                }
                
                completed = 0
                for future in as_completed(futures):
                    result = future.result()
                    self.report.add_result(result)
                    completed += 1
                    
                    if completed % 10 == 0:
                        print(f"  Progress: {completed}/{num_queries} "
                              f"({self.report.successful} success, {self.report.failed} failed)")
        else:
            for i, (query, cat) in enumerate(queries):
                result = self.execute_query(query, cat)
                self.report.add_result(result)
                
                if (i + 1) % 10 == 0:
                    print(f"  Progress: {i+1}/{num_queries}")
        
        self.report.print_summary()
        return self.report
    
    def run_specific_queries(self, queries: List[str], 
                             category: str = "custom") -> TestReport:
        """Run specific custom queries"""
        self.run_category_tests(category, queries, verbose=True)
        self.report.print_summary()
        return self.report


def main():
    """Main entry point for frontend testing"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChemAgent Frontend Integration Test")
    parser.add_argument("--api", action="store_true", help="Test via API instead of direct")
    parser.add_argument("--api-url", default="http://localhost:8000", help="API URL")
    parser.add_argument("--categories", nargs="+", help="Categories to test")
    parser.add_argument("--stress", type=int, help="Run stress test with N queries")
    parser.add_argument("--parallel", action="store_true", help="Run stress test in parallel")
    parser.add_argument("--workers", type=int, default=5, help="Parallel workers")
    parser.add_argument("--quick", action="store_true", help="Quick test (2 per category)")
    parser.add_argument("--output", help="Save results to JSON file")
    
    args = parser.parse_args()
    
    tester = FrontendTester(use_api=args.api, api_url=args.api_url)
    
    if args.stress:
        report = tester.run_stress_test(
            num_queries=args.stress,
            parallel=args.parallel,
            max_workers=args.workers
        )
    else:
        # Modify queries for quick test
        if args.quick:
            for cat in TEST_QUERIES:
                TEST_QUERIES[cat] = TEST_QUERIES[cat][:2]
        
        report = tester.run_all_tests(categories=args.categories)
    
    # Save results if requested
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "mode": "api" if args.api else "direct",
            "total_queries": report.total_queries,
            "successful": report.successful,
            "failed": report.failed,
            "success_rate": report.successful / report.total_queries * 100 if report.total_queries > 0 else 0,
            "total_time": report.total_time,
            "avg_response_time": report.avg_response_time,
            "categories": report.results_by_category,
            "errors": report.errors
        }
        
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Return exit code based on success rate
    success_rate = report.successful / report.total_queries * 100 if report.total_queries > 0 else 0
    return 0 if success_rate >= 90 else 1


if __name__ == "__main__":
    exit(main())
