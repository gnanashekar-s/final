"""Mermaid diagram rendering component."""
import streamlit as st
import streamlit.components.v1 as components


def render_mermaid(mermaid_code: str, height: int = 400):
    """
    Render a Mermaid diagram using JavaScript.

    Args:
        mermaid_code: Mermaid diagram code
        height: Height of the rendered diagram in pixels
    """
    # HTML template with Mermaid.js
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
        <style>
            body {{
                background-color: transparent;
                margin: 0;
                padding: 10px;
            }}
            .mermaid {{
                display: flex;
                justify-content: center;
            }}
        </style>
    </head>
    <body>
        <div class="mermaid">
            {mermaid_code}
        </div>
        <script>
            mermaid.initialize({{
                startOnLoad: true,
                theme: 'default',
                securityLevel: 'loose',
            }});
        </script>
    </body>
    </html>
    """

    components.html(html_template, height=height)


def render_mermaid_with_fallback(mermaid_code: str, height: int = 400):
    """
    Render a Mermaid diagram with a code fallback.

    Args:
        mermaid_code: Mermaid diagram code
        height: Height of the rendered diagram in pixels
    """
    tab1, tab2 = st.tabs(["Diagram", "Code"])

    with tab1:
        try:
            render_mermaid(mermaid_code, height)
        except Exception as e:
            st.error(f"Failed to render diagram: {e}")
            st.code(mermaid_code, language="mermaid")

    with tab2:
        st.code(mermaid_code, language="mermaid")


def create_flowchart(nodes: list[dict], edges: list[dict]) -> str:
    """
    Create a Mermaid flowchart from nodes and edges.

    Args:
        nodes: List of node dicts with 'id', 'label', and optional 'style'
        edges: List of edge dicts with 'from', 'to', and optional 'label'

    Returns:
        Mermaid flowchart code
    """
    lines = ["graph TD"]

    # Add nodes
    for node in nodes:
        node_id = node.get("id", "")
        label = node.get("label", node_id)
        style = node.get("style", "")

        if style == "rounded":
            lines.append(f'    {node_id}("{label}")')
        elif style == "diamond":
            lines.append(f'    {node_id}{{"{label}"}}')
        elif style == "hexagon":
            lines.append(f'    {node_id}["{label}"]')
        else:
            lines.append(f'    {node_id}["{label}"]')

    # Add edges
    for edge in edges:
        from_id = edge.get("from", "")
        to_id = edge.get("to", "")
        label = edge.get("label", "")

        if label:
            lines.append(f'    {from_id} -->|"{label}"| {to_id}')
        else:
            lines.append(f"    {from_id} --> {to_id}")

    return "\n".join(lines)


def create_sequence_diagram(participants: list[str], interactions: list[dict]) -> str:
    """
    Create a Mermaid sequence diagram.

    Args:
        participants: List of participant names
        interactions: List of interaction dicts with 'from', 'to', 'message', and optional 'type'

    Returns:
        Mermaid sequence diagram code
    """
    lines = ["sequenceDiagram"]

    # Add participants
    for participant in participants:
        lines.append(f"    participant {participant}")

    # Add interactions
    for interaction in interactions:
        from_p = interaction.get("from", "")
        to_p = interaction.get("to", "")
        message = interaction.get("message", "")
        arrow_type = interaction.get("type", "solid")

        if arrow_type == "dashed":
            lines.append(f"    {from_p}-->>+ {to_p}: {message}")
        elif arrow_type == "return":
            lines.append(f"    {from_p}-->>- {to_p}: {message}")
        else:
            lines.append(f"    {from_p}->>+ {to_p}: {message}")

    return "\n".join(lines)


def create_er_diagram(entities: list[dict]) -> str:
    """
    Create a Mermaid ER diagram.

    Args:
        entities: List of entity dicts with 'name', 'fields', and optional 'relationships'

    Returns:
        Mermaid ER diagram code
    """
    lines = ["erDiagram"]

    # Add entities
    for entity in entities:
        name = entity.get("name", "Entity")
        fields = entity.get("fields", [])

        lines.append(f"    {name} {{")
        for field in fields:
            field_type = field.get("type", "string")
            field_name = field.get("name", "field")
            pk = " PK" if field.get("primary_key") else ""
            fk = " FK" if field.get("foreign_key") else ""
            lines.append(f"        {field_type} {field_name}{pk}{fk}")
        lines.append("    }")

    # Add relationships
    for entity in entities:
        for rel in entity.get("relationships", []):
            target = rel.get("target", "")
            rel_type = rel.get("type", "one-to-many")
            label = rel.get("label", "has")

            if rel_type == "one-to-one":
                lines.append(f'    {entity["name"]} ||--|| {target} : "{label}"')
            elif rel_type == "one-to-many":
                lines.append(f'    {entity["name"]} ||--o{{ {target} : "{label}"')
            elif rel_type == "many-to-many":
                lines.append(f'    {entity["name"]} }}o--o{{ {target} : "{label}"')

    return "\n".join(lines)
