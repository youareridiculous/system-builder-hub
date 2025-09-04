"""
Agent implementer - normalizes and validates BuilderState
"""
import logging
from typing import Dict, Any
from ..builder_schema import normalize_state, coerce_defaults, Node

logger = logging.getLogger(__name__)

def implement(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fill defaults, ensure consistency (route-first slugs, API/table naming)"""
    try:
        # Convert nodes to Node objects to apply defaults
        if 'nodes' in state:
            nodes = []
            for node_data in state['nodes']:
                if isinstance(node_data, dict):
                    node = Node(**node_data)
                    # Apply defaults
                    node.props = coerce_defaults(node)
                    nodes.append(node)
                else:
                    nodes.append(node_data)
            state['nodes'] = nodes
        
        # Normalize the entire state
        normalized = normalize_state(state)
        
        logger.info(f"Implemented state: {len(normalized.nodes)} nodes, {len(normalized.edges)} edges")
        return {
            'project_id': state.get('project_id', ''),
            'version': normalized.version,
            'nodes': [
                {
                    'id': node.id,
                    'type': node.type,
                    'props': node.props,
                    'meta': node.meta
                }
                for node in normalized.nodes
            ],
            'edges': [
                {
                    'source': edge.source,
                    'target': edge.target,
                    'kind': edge.kind
                }
                for edge in normalized.edges
            ],
            'metadata': normalized.metadata
        }
        
    except Exception as e:
        logger.error(f"Error implementing state: {e}")
        # Return original state if normalization fails
        return state
