"""Gradio web interface for ChemAgent."""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr

from chemagent import ChemAgent
from chemagent.config import get_config
from .history import HistoryManager
from .visualizer import ResultVisualizer


class ChemAgentUI:
    """Gradio UI for ChemAgent."""
    
    def __init__(self):
        """Initialize UI with agent and components."""
        self.agent = ChemAgent()
        self.config = get_config()
        self.history_manager = HistoryManager()
        self.visualizer = ResultVisualizer()
        
    def process_query(
        self,
        query: str,
        use_cache: bool = True,
        verbose: bool = False
    ) -> Tuple[str, str, str, List[Dict]]:
        """Process a single query and return formatted results.
        
        Args:
            query: Natural language query
            use_cache: Enable result caching
            verbose: Include execution details
            
        Returns:
            Tuple of (status_html, result_text, visualization_html, history)
        """
        if not query or not query.strip():
            return (
                self._format_status("error", "Empty query"),
                "Please enter a query.",
                "",
                self.history_manager.get_recent(10)
            )
        
        # Process query
        start_time = time.time()
        try:
            result = self.agent.query(
                query,
                use_cache=use_cache,
                verbose=verbose
            )
            execution_time = time.time() - start_time
            
            # Save to history
            self.history_manager.add_query(
                query=query,
                result=result,
                execution_time=execution_time,
                cached=result.cached
            )
            
            # Format results
            status_html = self._format_status(
                "success" if result.success else "error",
                f"Query completed in {execution_time:.2f}s"
            )
            
            result_text = self._format_result(result, verbose)
            viz_html = self.visualizer.visualize(result)
            history = self.history_manager.get_recent(10)
            
            return status_html, result_text, viz_html, history
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            return (
                self._format_status("error", error_msg),
                error_msg,
                "",
                self.history_manager.get_recent(10)
            )
    
    def process_batch(
        self,
        queries_text: str,
        use_cache: bool = True,
        enable_parallel: bool = True
    ) -> Tuple[str, str, List[Dict]]:
        """Process multiple queries from text input.
        
        Args:
            queries_text: Queries separated by newlines
            use_cache: Enable result caching
            enable_parallel: Enable parallel execution
            
        Returns:
            Tuple of (status_html, results_text, history)
        """
        if not queries_text or not queries_text.strip():
            return (
                self._format_status("error", "No queries provided"),
                "Please enter queries (one per line).",
                self.history_manager.get_recent(10)
            )
        
        queries = [q.strip() for q in queries_text.split('\n') if q.strip()]
        
        start_time = time.time()
        results = []
        successful = 0
        
        for i, query in enumerate(queries, 1):
            try:
                result = self.agent.query(
                    query,
                    use_cache=use_cache
                )
                
                if result.success:
                    successful += 1
                
                results.append({
                    "query": query,
                    "success": result.success,
                    "result": result
                })
                
                # Save to history
                self.history_manager.add_query(
                    query=query,
                    result=result,
                    execution_time=0,
                    cached=result.cached
                )
                
            except Exception as e:
                results.append({
                    "query": query,
                    "success": False,
                    "error": str(e)
                })
        
        total_time = time.time() - start_time
        
        # Format batch results
        status_html = self._format_status(
            "success",
            f"Processed {len(queries)} queries in {total_time:.2f}s"
        )
        
        results_text = self._format_batch_results(results, successful, total_time)
        history = self.history_manager.get_recent(10)
        
        return status_html, results_text, history
    
    def load_history_item(self, history_item: Dict) -> Tuple[str, str, str]:
        """Load a query from history.
        
        Args:
            history_item: History item dictionary
            
        Returns:
            Tuple of (query, result_text, visualization_html)
        """
        if not history_item:
            return "", "", ""
        
        query = history_item.get("query", "")
        result = history_item.get("result", {})
        
        result_text = self._format_result(result, verbose=False)
        viz_html = self.visualizer.visualize(result)
        
        return query, result_text, viz_html
    
    def search_history(self, search_term: str) -> List[Dict]:
        """Search query history.
        
        Args:
            search_term: Term to search for
            
        Returns:
            List of matching history items
        """
        return self.history_manager.search(search_term)
    
    def toggle_favorite(self, query_id: str) -> List[Dict]:
        """Toggle favorite status of a query.
        
        Args:
            query_id: Query ID
            
        Returns:
            Updated history list
        """
        self.history_manager.toggle_favorite(query_id)
        return self.history_manager.get_recent(10)
    
    def get_favorites(self) -> List[Dict]:
        """Get favorite queries.
        
        Returns:
            List of favorite queries
        """
        return self.history_manager.get_favorites()
    
    def clear_history(self) -> Tuple[str, List[Dict]]:
        """Clear query history.
        
        Returns:
            Tuple of (message, empty history list)
        """
        self.history_manager.clear()
        return "History cleared.", []
    
    def _format_status(self, status: str, message: str) -> str:
        """Format status message as HTML."""
        color = {
            "success": "#4CAF50",
            "error": "#f44336",
            "info": "#2196F3"
        }.get(status, "#666")
        
        return f"""
        <div style="padding: 10px; background: {color}; color: white; border-radius: 5px; margin: 10px 0;">
            <strong>{status.upper()}:</strong> {message}
        </div>
        """
    
    def _format_result(self, result, verbose: bool) -> str:
        """Format query result as readable text."""
        if not result:
            return "No results."
        
        # Handle QueryResult dataclass
        from chemagent import QueryResult
        
        lines = []
        
        # Show the query
        if result.query:
            lines.append(f"Query: {result.query}")
            lines.append("")
        
        lines.append("QUERY RESULT")
        lines.append("-" * 80)
        
        # Basic info
        lines.append(f"Success: {result.success}")
        lines.append(f"Intent: {result.intent_type or 'unknown'}")
        lines.append(f"Execution Time: {result.execution_time_ms:.2f}ms")
        lines.append(f"Steps: {result.steps_taken}")
        
        if result.cached:
            lines.append("✓ Result from cache")
        
        lines.append("")
        
        # Main answer
        if result.answer:
            lines.append("ANSWER:")
            lines.append("-" * 80)
            lines.append(result.answer)
            lines.append("")
        
        # Error
        if result.error:
            lines.append("ERROR:")
            lines.append("-" * 80)
            lines.append(result.error)
            lines.append("")
        
        # Verbose details
        if verbose and result.provenance:
            lines.append("PROVENANCE:")
            lines.append("-" * 80)
            for item in result.provenance:
                lines.append(f"  • {item}")
        
        return "\n".join(lines)
    
    def _format_batch_results(
        self,
        results: List[Dict],
        successful: int,
        total_time: float
    ) -> str:
        """Format batch processing results."""
        lines = []
        lines.append("=" * 80)
        lines.append("BATCH PROCESSING RESULTS")
        lines.append("=" * 80)
        lines.append(f"Total queries: {len(results)}")
        lines.append(f"Successful: {successful}")
        lines.append(f"Failed: {len(results) - successful}")
        lines.append(f"Total time: {total_time:.2f}s")
        lines.append(f"Average time: {total_time/len(results):.2f}s per query")
        lines.append("")
        
        for i, item in enumerate(results, 1):
            lines.append(f"\n[{i}] {item['query']}")
            lines.append(f"    Status: {'✓ Success' if item['success'] else '✗ Failed'}")
            
            if item.get("error"):
                lines.append(f"    Error: {item['error']}")
            elif item.get("result"):
                result_summary = str(item["result"].get("result", ""))[:100]
                lines.append(f"    Result: {result_summary}...")
        
        lines.append("\n" + "=" * 80)
        
        return "\n".join(lines)


def create_app() -> gr.Blocks:
    """Create and configure Gradio app.
    
    Returns:
        Configured Gradio Blocks app
    """
    ui = ChemAgentUI()
    
    # Custom CSS for styling
    custom_css = """
    .container { max-width: 1400px; margin: auto; }
    .query-box { font-size: 16px; }
    .result-box { font-family: monospace; font-size: 14px; }
    .history-item { padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin: 5px 0; }
    """
    
    with gr.Blocks(
        title="ChemAgent - Pharmaceutical Research Assistant"
    ) as app:
        
        gr.Markdown("""
        # 🧪 ChemAgent - Pharmaceutical Research Assistant
        
        Natural language interface for compound lookup, property calculation, similarity search, and target analysis.
        """)
        
        with gr.Tabs():
            # Main Query Tab
            with gr.Tab("🔍 Query"):
                with gr.Row():
                    with gr.Column(scale=2):
                        query_input = gr.Textbox(
                            label="Enter your query",
                            placeholder="e.g., What is CHEMBL25? Find similar compounds to aspirin.",
                            lines=3,
                            elem_classes=["query-box"]
                        )
                        
                        with gr.Row():
                            submit_btn = gr.Button("🚀 Submit", variant="primary", scale=2)
                            clear_btn = gr.Button("🗑️ Clear", scale=1)
                        
                        with gr.Accordion("⚙️ Options", open=False):
                            use_cache = gr.Checkbox(label="Use cache", value=True)
                            verbose = gr.Checkbox(label="Verbose output", value=False)
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### 💡 Example Queries")
                        example_queries = [
                            "What is CHEMBL25?",
                            "Find similar compounds to aspirin",
                            "Get properties for caffeine",
                            "What targets does ibuprofen bind to?",
                            "Compare molecular weight of aspirin and ibuprofen"
                        ]
                        for example in example_queries:
                            gr.Button(example, size="sm").click(
                                lambda x=example: x,
                                outputs=query_input
                            )
                
                status_output = gr.HTML(label="Status")
                
                with gr.Row():
                    with gr.Column(scale=2):
                        result_output = gr.Markdown(
                            label="Results",
                            elem_classes=["result-box"]
                        )
                    
                    with gr.Column(scale=1):
                        viz_output = gr.HTML(label="Visualization")
            
            # Batch Processing Tab
            with gr.Tab("📦 Batch Processing"):
                gr.Markdown("""
                Process multiple queries at once (one per line).
                Queries will be processed in parallel for better performance.
                """)
                
                batch_input = gr.Textbox(
                    label="Queries (one per line)",
                    placeholder="What is CHEMBL25?\nFind similar compounds to aspirin\nGet properties for caffeine",
                    lines=10
                )
                
                with gr.Row():
                    batch_submit_btn = gr.Button("🚀 Process Batch", variant="primary")
                    with gr.Column():
                        batch_use_cache = gr.Checkbox(label="Use cache", value=True)
                        batch_parallel = gr.Checkbox(label="Enable parallel", value=True)
                
                batch_status = gr.HTML(label="Status")
                batch_results = gr.Markdown(
                    label="Batch Results",
                    elem_classes=["result-box"]
                )
            
            # History Tab
            with gr.Tab("📜 History"):
                with gr.Row():
                    search_box = gr.Textbox(
                        label="Search history",
                        placeholder="Search queries..."
                    )
                    show_favorites = gr.Button("⭐ Show Favorites")
                    clear_history_btn = gr.Button("🗑️ Clear History")
                
                history_output = gr.JSON(label="Query History")
                
                gr.Markdown("### Load from History")
                selected_history = gr.State(None)
                
                with gr.Row():
                    load_btn = gr.Button("📥 Load Selected")
                    favorite_btn = gr.Button("⭐ Toggle Favorite")
            
            # Help Tab
            with gr.Tab("❓ Help"):
                gr.Markdown("""
                ## How to Use ChemAgent
                
                ### Query Types
                
                1. **Compound Lookup**
                   - `What is CHEMBL25?`
                   - `Tell me about aspirin`
                   - `Look up CC(=O)OC1=CC=CC=C1C(=O)O`
                
                2. **Property Queries**
                   - `What is the molecular weight of aspirin?`
                   - `Get properties for CHEMBL25`
                   - `Calculate druglikeness for caffeine`
                
                3. **Similarity Search**
                   - `Find similar compounds to aspirin`
                   - `Search for analogs of CHEMBL25 with similarity > 0.8`
                   - `Top 10 most similar compounds to caffeine`
                
                4. **Target Queries**
                   - `What targets does aspirin bind to?`
                   - `Find compounds that bind to COX-2`
                   - `Get binding affinities for metformin`
                
                5. **Complex Workflows**
                   - `Find similar compounds to aspirin and get their targets`
                   - `Compare properties of aspirin and ibuprofen`
                   - `Find COX-2 inhibitors with IC50 < 100nM`
                
                ### Features
                
                - **Caching**: Results are cached for faster repeated queries
                - **Parallel Execution**: Independent steps run in parallel
                - **Batch Processing**: Process multiple queries efficiently
                - **History**: All queries are saved for later reference
                - **Favorites**: Mark important queries for quick access
                
                ### Keyboard Shortcuts
                
                - `Ctrl+Enter`: Submit query
                - `Ctrl+L`: Clear input
                
                ### API Access
                
                ChemAgent also provides a REST API:
                
                ```bash
                # Single query
                curl -X POST http://localhost:8000/query \\
                  -H "Content-Type: application/json" \\
                  -d '{"query": "What is CHEMBL25?"}'
                
                # Batch processing
                curl -X POST http://localhost:8000/batch \\
                  -H "Content-Type: application/json" \\
                  -d '{"queries": ["What is CHEMBL25?", "Find aspirin analogs"]}'
                ```
                """)
        
        # Event handlers
        submit_btn.click(
            fn=ui.process_query,
            inputs=[query_input, use_cache, verbose],
            outputs=[status_output, result_output, viz_output, history_output]
        )
        
        clear_btn.click(
            lambda: ("", "", ""),
            outputs=[query_input, result_output, viz_output]
        )
        
        batch_submit_btn.click(
            fn=ui.process_batch,
            inputs=[batch_input, batch_use_cache, batch_parallel],
            outputs=[batch_status, batch_results, history_output]
        )
        
        search_box.change(
            fn=ui.search_history,
            inputs=[search_box],
            outputs=[history_output]
        )
        
        show_favorites.click(
            fn=ui.get_favorites,
            outputs=[history_output]
        )
        
        clear_history_btn.click(
            fn=ui.clear_history,
            outputs=[batch_status, history_output]
        )
        
        # Load initial history
        app.load(
            fn=lambda: ui.history_manager.get_recent(10),
            outputs=[history_output]
        )
    
    return app


def launch_app(
    server_name: str = "0.0.0.0",
    server_port: int = 7860,
    share: bool = False,
    **kwargs
):
    """Launch Gradio app.
    
    Args:
        server_name: Server host
        server_port: Server port
        share: Create public share link
        **kwargs: Additional Gradio launch arguments
    """
    app = create_app()
    
    # Apply theme and CSS during launch (Gradio 6.0+)
    app.launch(
        server_name=server_name,
        server_port=server_port,
        share=share,
        **kwargs
    )


if __name__ == "__main__":
    launch_app()
