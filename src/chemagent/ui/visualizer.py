"""Result visualization for ChemAgent UI."""

from typing import Any, Dict, List


class ResultVisualizer:
    """Visualize query results with HTML/CSS."""
    
    def visualize(self, result) -> str:
        """Generate HTML visualization of result.
        
        Args:
            result: QueryResult dataclass
            
        Returns:
            HTML string for visualization
        """
        if not result or not result.success:
            return self._error_viz(result)
        
        intent_type = result.intent_type or "unknown"
        
        # Skip visualization for comparison queries (formatted answer is sufficient)
        if "comparison" in intent_type.lower():
            return ""
        
        # Route to appropriate visualizer
        if "compound" in intent_type.lower():
            return self._compound_viz(result)
        elif "property" in intent_type.lower():
            return self._property_viz(result)
        elif "similarity" in intent_type.lower():
            return self._similarity_viz(result)
        elif "target" in intent_type.lower():
            return self._target_viz(result)
        else:
            return self._generic_viz(result)
    
    def _error_viz(self, result) -> str:
        """Visualize error result."""
        error = result.error if result else "Unknown error"
        return f"""
        <div style="padding: 20px; background: #ffebee; border-left: 4px solid #f44336; border-radius: 4px;">
            <h3 style="color: #c62828; margin-top: 0;">❌ Error</h3>
            <p style="color: #666;">{error}</p>
        </div>
        """
    
    def _compound_viz(self, result) -> str:
        """Visualize compound lookup result."""
        data = result.raw_output
        
        if not data:
            return "<p>No compound data available.</p>"
        
        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #1976D2; margin-top: 0;">🧪 Compound Information</h3>
            
            <div style="background: white; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <h4>Basic Information</h4>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 8px; font-weight: bold; width: 40%;">Name:</td>
                        <td style="padding: 8px;">{data.get('name', 'N/A')}</td>
                    </tr>
                    <tr style="background: #f9f9f9;">
                        <td style="padding: 8px; font-weight: bold;">ChEMBL ID:</td>
                        <td style="padding: 8px;">{data.get('chembl_id', 'N/A')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; font-weight: bold;">Type:</td>
                        <td style="padding: 8px;">{data.get('type', 'N/A')}</td>
                    </tr>
                </table>
            </div>
        """
        
        if data.get("properties"):
            html += """
            <div style="background: white; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <h4>Properties</h4>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px;">
            """
            
            for key, value in data["properties"].items():
                html += f"""
                <div style="padding: 10px; background: #f9f9f9; border-radius: 4px;">
                    <div style="font-weight: bold; color: #666; font-size: 12px;">{key.upper()}</div>
                    <div style="font-size: 18px; color: #333;">{value}</div>
                </div>
                """
            
            html += "</div></div>"
        
        html += "</div>"
        
        return html
    
    def _property_viz(self, result) -> str:
        """Visualize property query result."""
        data = result.raw_output if result else {}
        
        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #1976D2; margin-top: 0;">📊 Molecular Properties</h3>
            
            <div style="background: white; padding: 15px; border-radius: 4px;">
        """
        
        if isinstance(data, dict):
            html += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">'
            
            for key, value in data.items():
                if key not in ["_metadata", "success"]:
                    html += f"""
                    <div style="padding: 15px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="font-size: 12px; opacity: 0.9; text-transform: uppercase; letter-spacing: 1px;">
                            {key.replace('_', ' ')}
                        </div>
                        <div style="font-size: 24px; font-weight: bold; margin-top: 5px;">
                            {value}
                        </div>
                    </div>
                    """
            
            html += '</div>'
        else:
            html += f'<p>{str(data)}</p>'
        
        html += "</div></div>"
        
        return html
    
    def _similarity_viz(self, result) -> str:
        """Visualize similarity search results."""
        data = result.raw_output if result else {}
        
        if isinstance(data, list):
            compounds = data[:10]  # Show top 10
        else:
            return "<p>No similarity results.</p>"
        
        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #1976D2; margin-top: 0;">🔍 Similar Compounds</h3>
            <p style="color: #666;">Top {len(compounds)} matches</p>
        """
        
        for i, compound in enumerate(compounds, 1):
            similarity = compound.get("similarity", 0)
            bar_width = int(similarity * 100)
            
            html += f"""
            <div style="background: white; padding: 15px; border-radius: 4px; margin: 10px 0;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <span style="font-weight: bold;">#{i} {compound.get('name', 'Unknown')}</span>
                    <span style="background: #4CAF50; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        {similarity:.3f}
                    </span>
                </div>
                <div style="background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;">
                    <div style="background: linear-gradient(90deg, #4CAF50, #8BC34A); 
                                height: 100%; width: {bar_width}%; transition: width 0.3s;">
                    </div>
                </div>
                <div style="font-size: 12px; color: #666; margin-top: 5px;">
                    ChEMBL ID: {compound.get('chembl_id', 'N/A')}
                </div>
            </div>
            """
        
        html += "</div>"
        
        return html
    
    def _target_viz(self, result) -> str:
        """Visualize target query results."""
        data = result.raw_output if result else {}
        
        if isinstance(data, list):
            targets = data
        else:
            return "<p>No target data available.</p>"
        
        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #1976D2; margin-top: 0;">🎯 Protein Targets</h3>
            <p style="color: #666;">Found {len(targets)} targets</p>
        """
        
        for target in targets:
            html += f"""
            <div style="background: white; padding: 15px; border-radius: 4px; margin: 10px 0; 
                        border-left: 4px solid #FF9800;">
                <h4 style="margin: 0 0 10px 0; color: #333;">{target.get('name', 'Unknown Target')}</h4>
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; font-size: 14px;">
                    <div>
                        <span style="color: #666;">Type:</span> 
                        <strong>{target.get('type', 'N/A')}</strong>
                    </div>
                    <div>
                        <span style="color: #666;">Organism:</span> 
                        <strong>{target.get('organism', 'N/A')}</strong>
                    </div>
                </div>
                {self._activity_badge(target.get('activity'))}
            </div>
            """
        
        html += "</div>"
        
        return html
    
    def _activity_badge(self, activity: Any) -> str:
        """Generate activity badge HTML."""
        if not activity:
            return ""
        
        return f"""
        <div style="margin-top: 10px; padding: 8px; background: #e3f2fd; border-radius: 4px; font-size: 13px;">
            <strong>Activity:</strong> {activity}
        </div>
        """
    
    def _generic_viz(self, result) -> str:
        """Generic visualization for unknown result types."""
        data = result.raw_output if result else {}
        
        html = f"""
        <div style="padding: 20px; background: #f5f5f5; border-radius: 8px;">
            <h3 style="color: #1976D2; margin-top: 0;">📋 Result</h3>
            <div style="background: white; padding: 15px; border-radius: 4px; font-family: monospace; 
                        font-size: 13px; overflow-x: auto;">
                <pre style="margin: 0; white-space: pre-wrap;">{self._format_dict(data)}</pre>
            </div>
        </div>
        """
        
        return html
    
    def _format_dict(self, data: Any, indent: int = 0) -> str:
        """Format dictionary for display."""
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                prefix = "  " * indent
                if isinstance(value, (dict, list)):
                    lines.append(f"{prefix}{key}:")
                    lines.append(self._format_dict(value, indent + 1))
                else:
                    lines.append(f"{prefix}{key}: {value}")
            return "\n".join(lines)
        elif isinstance(data, list):
            lines = []
            for i, item in enumerate(data):
                prefix = "  " * indent
                lines.append(f"{prefix}[{i}] {self._format_dict(item, indent + 1)}")
            return "\n".join(lines)
        else:
            return str(data)
