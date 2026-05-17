"""
Mermaid Renderer Module

Provides robust Mermaid diagram cleaning, validation, and rendering utilities.
Fixes common LLM-generated Mermaid syntax errors before they reach the UI.

Classes:
    MermaidCleaner: Strips/fixes bad syntax before rendering
    MermaidValidator: Catches errors before they reach the UI

Functions:
    extract_mermaid_blocks(): Finds all Mermaid code blocks in LLM response

Usage:
    from mermaid_renderer import MermaidCleaner, MermaidValidator, extract_mermaid_blocks
    
    # Extract and clean
    blocks = extract_mermaid_blocks(llm_response)
    for block in blocks:
        cleaned = MermaidCleaner.clean(block)
        is_valid, error = MermaidValidator.validate(cleaned)
        if is_valid:
            render(cleaned)
        else:
            show_error(error)
"""

from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)


# ── 1A. KNOWN VALID DIAGRAM TYPES ────────────────────────────────────────────

VALID_DIAGRAM_TYPES = {
    "flowchart",
    "graph",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "gantt",
    "pie",
    "gitGraph",
    "mindmap",
    "timeline",
    "quadrantChart",
    "xychart-beta",
    "block-beta",
    "journey",
    "C4Context",
}

# ── 1B. MERMAID CLEANER ───────────────────────────────────────────────────────

class MermaidCleaner:
    """
    Cleans LLM-generated Mermaid syntax before it reaches the renderer.
    Fixes every known category of syntax error without altering the diagram meaning.
    """

    @staticmethod
    def clean(raw: str) -> str:
        """
        Master cleaning pipeline. Returns cleaned Mermaid code string.
        Call this on any LLM output before passing to the renderer.
        """
        code = raw.strip()

        # Step 1 — Strip markdown fences (```mermaid ... ``` or ``` ... ```)
        code = MermaidCleaner._strip_fences(code)

        # Step 2 — Strip leading/trailing whitespace again after fence removal
        code = code.strip()

        # Step 3 — Fix diagram type keyword on first line
        code = MermaidCleaner._fix_diagram_type(code)

        # Step 4 — Fix node label special characters
        code = MermaidCleaner._fix_node_labels(code)

        # Step 5 — Fix arrow syntax (LLMs often use wrong arrow types)
        code = MermaidCleaner._fix_arrows(code)

        # Step 6 — Fix indentation (tabs → spaces, normalize)
        code = MermaidCleaner._fix_indentation(code)

        # Step 7 — Remove blank lines inside node/edge definitions
        code = MermaidCleaner._remove_consecutive_blanks(code)

        # Step 8 — Fix subgraph syntax
        code = MermaidCleaner._fix_subgraphs(code)

        # Step 9 — Force Hierarchical Tree (No mindmaps/circles allowed)
        code = MermaidCleaner._enforce_tree_hierarchy(code)

        # Step 9.5 — Fix triple quotes and other label nesting
        code = MermaidCleaner._fix_nested_labels(code)

        # Step 10 — Normalize whitespace
        code = MermaidCleaner._normalize_whitespace(code)

        # Step 11 — Ensure diagram ends with a newline
        code = code.rstrip() + "\n"

        return code

    # ── Private cleaners ─────────────────────────────────────────────────────

    @staticmethod
    def _normalize_whitespace(code: str) -> str:
        """Removes excessive spaces while preserving indentation."""
        lines = code.split("\n")
        fixed = []
        for line in lines:
            indent = len(line) - len(line.lstrip())
            content = " ".join(line.split())
            if not content:
                fixed.append("")
                continue
            fixed.append(" " * indent + content)
        return "\n".join(fixed)

    @staticmethod
    def _fix_nested_labels(code: str) -> str:
        """Fixes labels like [""Text""] or ["'Text'"] which break the parser."""
        # Fix triple quotes
        code = code.replace('"""', '"').replace("'''", "'")
        # Fix double quotes at edges inside brackets
        code = re.sub(r'(\[|\(|\{)""', r'\1"', code)
        code = re.sub(r'""(\]|\)|\})', r'"\1', code)
        return code

    @staticmethod
    def _enforce_tree_hierarchy(code: str) -> str:
        """
        Converts indented lists or mindmap syntax into a valid 
        Top-Down (TD) flowchart with explicit arrows.
        Bails out if the code already looks like a valid graph/flowchart.
        """
        stripped_code = code.strip()
        
        # If it already has arrows, it's a handcrafted diagram.
        # Don't try to re-parse it as a list, as that will destroy the labels.
        if "-->" in stripped_code or "---" in stripped_code or "==>" in stripped_code:
            # Just ensure it's TD (handled by _fix_diagram_type mostly, but be safe)
            return code
            
        lines = code.split("\n")
        if not lines: return code
        
        is_mindmap = False
        fixed_lines = ["flowchart TD"]
        stack = []  # To track (indent, node_id)
        
        # Check if the first non-empty line is 'mindmap'
        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("%%"): continue
            if trimmed.lower().startswith("mindmap"):
                is_mindmap = True
            break

        for line in lines:
            trimmed = line.strip()
            if not trimmed or trimmed.startswith("%%"):
                continue
                
            stripped_lower = trimmed.lower()
            # Skip headers during conversion
            if any(stripped_lower.startswith(t) for t in ["flowchart", "graph", "mindmap"]):
                continue
            
            # If we don't see an arrow --> but we see indentation, it's a tree-as-list
            indent = len(line) - len(line.lstrip())
            
            # Clean up the content (remove bullet points, quotes, brackets etc.)
            content = trimmed.lstrip("-*•+").strip()
            
            # Remove node shape symbols common in mindmaps
            content = re.sub(r'[\(\[\{\}\]\)]+', '', content).strip()
            
            # AGGRESSIVE STRIP: Remove all internal quotes and colons that break labels
            content = content.replace('"', '').replace("'", '').replace(":", " - ").replace("<", " ").replace(">", " ").strip()
            
            if not content: continue

            # Generate a stable ID for the node
            node_id_seed = re.sub(r'\W+', '', content)[:20]
            node_id = f"node_{node_id_seed}_{str(hash(content))[-4:]}"
            
            # Find parent in stack
            while stack and stack[-1][0] >= indent:
                stack.pop()
            
            if stack:
                parent_id = stack[-1][1]
                fixed_lines.append(f'    {parent_id} --> {node_id}["{content}"]')
            else:
                fixed_lines.append(f'    {node_id}["{content}"]')
                
            stack.append((indent, node_id))
                
        # Only return the converted version if we actually found something to convert
        if len(fixed_lines) > 1:
            return "\n".join(fixed_lines)
        return code


    @staticmethod
    def _strip_fences(code: str) -> str:
        """Remove ```mermaid ... ``` and ``` ... ``` wrappers."""
        # Remove opening fence: ```mermaid or ```
        code = re.sub(r"^```(?:mermaid)?\s*\n?", "", code, flags=re.IGNORECASE)
        # Remove closing fence: ```
        code = re.sub(r"\n?```\s*$", "", code)
        return code

    @staticmethod
    def _fix_diagram_type(code: str) -> str:
        """
        Ensures the first non-empty line is a valid Mermaid diagram type.
        Forces flowchart TD or graph TD to ensure tree structure.
        """
        lines = code.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue

            first_word = stripped.split()[0].lower()

            # Fix orientation: Force all graphs/flowcharts to TD (Top-Down)
            if first_word in ["graph", "flowchart"]:
                # Force TD for tree structure
                if any(x in stripped for x in [" LR", " RL", " BT", " TB"]):
                    lines[i] = re.sub(r"\s(LR|RL|BT|TB)", " TD", stripped, flags=re.IGNORECASE)
                elif stripped == "graph" or stripped == "flowchart":
                    lines[i] = stripped + " TD"
                
                # Ensure lowercase keywords
                lines[i] = lines[i].replace("graph", "graph").replace("flowChart", "flowchart").replace("Flowchart", "flowchart")
                break

            # Fix case variations for other types
            case_fixes = {
                "sequence": "sequenceDiagram",
                "sequencediagram": "sequenceDiagram",
                "classdiagram": "classDiagram",
                "statediagram": "stateDiagram-v2",
                "erdiagram": "erDiagram",
                "gitgraph": "gitGraph",
                "mindmap": "mindmap",
                "timeline": "timeline",
            }

            for wrong, correct in case_fixes.items():
                if first_word == wrong.lower() and stripped.lower().startswith(wrong.lower()):
                    lines[i] = line.replace(stripped.split()[0], correct, 1)
                    break

            break  # only process first non-empty line

        result = "\n".join(lines)
        return result

    @staticmethod
    def _fix_node_labels(code: str) -> str:
        """
        Fixes special characters inside node labels that break the parser.

        Mermaid node label rules:
          - Square bracket labels: A[label]   — safe chars: letters, spaces, hyphens
          - Parenthesis labels:    A(label)   — same rules
          - Curly labels:          A{label}   — decision nodes
          - Labels must NOT contain: unescaped quotes, colons, angle brackets inside []

        Fixes applied:
          - Quotes inside [] labels → removed
          - Colons inside [] labels → replaced with " —"
          - Unmatched brackets → removed
          - HTML entities inside labels → decoded
        """
        def fix_label_content(match):
            open_bracket = match.group(1)   # [, (, or {
            content = match.group(2)
            close_bracket = match.group(3)  # ], ), or }

            # Replace colons (breaks Mermaid sequence diagrams outside of ->:)
            content = content.replace(":", " —")

            # Replace raw double quotes → remove (We add our own quotes for safety)
            content = content.replace('"', "")
            content = content.replace("'", "")

            # Decode common HTML entities
            content = content.replace("&amp;", "&")
            content = content.replace("<", "less than")
            content = content.replace(">", "greater than")
            content = content.replace("&nbsp;", " ")

            return f'{open_bracket}"{content}"{close_bracket}'

        # Single pass for any bracket type to avoid nested replacements
        # This handles mindmap root((Text)) and flowchart A["Text"]
        # Pattern: matches [[...]] or ((...)) or {{...}} and everything in between
        pattern = r"(\[+)(.*?)(\]+)|(\(+)(.*?)(\)+)|(\{+)(.*?)(\}+)"

        def complex_fix(match):
            # Check which group matched
            for i in (1, 4, 7):
                if match.group(i):
                    open_b = match.group(i)
                    content = match.group(i+1)
                    close_b = match.group(i+2)
                    
                    # Ensure start/end brackets match counts roughly
                    if len(open_b) != len(close_b):
                        # If mismatched, just return original to let validator catch/fix
                        return match.group(0)

                    # Fix label content
                    processed = content.replace('"', "").replace("'", "")
                    processed = processed.replace(":", " —")
                    processed = processed.replace("&amp;", "&").replace("<", "less than").replace(">", "greater than")
                    processed = processed.strip()
                    
                    return f'{open_b}"{processed}"{close_b}'
            return match.group(0)

        code = re.sub(pattern, complex_fix, code)

        return code

    @staticmethod
    def _fix_arrows(code: str) -> str:
        """
        Fixes common arrow syntax mistakes LLMs make.

        Valid Mermaid arrows:
          -->   (normal)
          ---   (no arrowhead)
          --->  (dotted, longer)
          ==>   (thick)
          -.->  (dotted with arrow)
          -->>  (async in sequence)
          ->>   (solid line in sequence)

        Common LLM mistakes:
          ->    (missing one dash)  → -->
          =>    (wrong thick arrow) → ==>
          ~>    (invalid)           → -->
          ──>   (unicode dash)      → -->
          —>    (em dash)           → -->
        """
        # em dash or unicode long dash → double hyphen
        code = code.replace("——>", "-->")
        code = code.replace("—>",  "-->")
        code = code.replace("–>",  "-->")

        # Single dash arrow (outside of node labels)
        code = re.sub(r"(?<![>\-=])->(?!\>)", "-->", code)

        # => not preceded by = → ==>
        code = re.sub(r"(?<!=)=>(?!=)", "==>", code)

        # ~> → -->
        code = code.replace("~>", "-->")

        # Unicode arrow characters
        code = code.replace("→", "-->")
        code = code.replace("⟶", "-->")
        code = code.replace("⇒", "==>")

        return code

    @staticmethod
    def _fix_indentation(code: str) -> str:
        """Convert tabs to 4 spaces. Strip trailing whitespace per line."""
        lines = []
        for line in code.split("\n"):
            line = line.replace("\t", "    ")
            line = line.rstrip()
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _remove_consecutive_blanks(code: str) -> str:
        """Collapse 2+ consecutive blank lines into one."""
        return re.sub(r"\n{3,}", "\n\n", code)

    @staticmethod
    def _fix_subgraphs(code: str) -> str:
        """
        Ensures subgraph blocks are correctly closed.
        LLMs often forget the 'end' keyword.
        """
        lines = code.split("\n")
        open_subgraphs = 0
        fixed = []

        for line in lines:
            stripped = line.strip().lower()
            if stripped.startswith("subgraph"):
                open_subgraphs += 1
            elif stripped == "end":
                if open_subgraphs > 0:
                    open_subgraphs -= 1
            fixed.append(line)

        # Close any unclosed subgraphs
        for _ in range(open_subgraphs):
            fixed.append("end")


        return "\n".join(fixed)

    @staticmethod
    def _fix_mindmap_arrows(code: str) -> str:
        """
        Removes flowchart-style arrows from Mindmaps.
        Mindmaps use indentation/hierarchy only.
        """
        lines = code.split("\n")
        if not lines:
            return code
            
        # Check if it's a mindmap (skip comments)
        is_mindmap = False
        for line in lines:
            stripped = line.strip().lower()
            if not stripped or stripped.startswith("%%"):
                continue
            if "mindmap" in stripped:
                is_mindmap = True
            break
            
        if not is_mindmap:
            return code
            
        fixed = []
        for line in lines:
            # Replace -->, ->, ==>, =>, -.- with a space
            # but ONLY if not inside quotes (heuristic)
            if '"' not in line:
                line = re.sub(r"([-~=.]+>\s*|--\s*)", " ", line)
            fixed.append(line)
        return "\n".join(fixed)


# ── 1C. MERMAID VALIDATOR ─────────────────────────────────────────────────────

class MermaidValidator:
    """
    Lightweight pre-render validation.
    Catches the most common errors before they produce a red error box in the UI.
    Returns (is_valid: bool, error_message: str | None).
    """

    @staticmethod
    def validate(code: str) -> tuple[bool, str | None]:
        """
        Returns (True, None) if code looks valid.
        Returns (False, "reason") if a structural problem is detected.
        """
        lines = [l for l in code.split("\n") if l.strip()]

        if not lines:
            return False, "Empty diagram — no content to render."

        # Check first line is a known diagram type
        first_word = lines[0].strip().split()[0]
        if first_word not in VALID_DIAGRAM_TYPES:
            return False, (
                f"Unknown diagram type '{first_word}'. "
                f"Must be one of: {', '.join(sorted(VALID_DIAGRAM_TYPES))}"
            )

        # Must have at least 2 lines (type + at least one node/step)
        if len(lines) < 2:
            return False, "Diagram has no content after the type declaration."

        # Check for unmatched brackets in node labels
        bracket_pairs = [("(", ")"), ("[", "]"), ("{", "}")]
        for line in lines[1:]:
            # Skip comment lines
            if line.strip().startswith("%%"):
                continue
            for open_b, close_b in bracket_pairs:
                opens = line.count(open_b)
                closes = line.count(close_b)
                if opens != closes:
                    return False, (
                        f"Unbalanced '{open_b}' and '{close_b}' brackets. "
                        f"Check line: {line.strip()[:60]}"
                    )

        # flowchart / graph must have a direction
        if first_word in ("flowchart", "graph"):
            parts = lines[0].strip().split()
            if len(parts) < 2:
                return False, (
                    f"'{first_word}' requires a direction: TD, LR, BT, or RL. "
                    f"E.g. 'flowchart TD'"
                )
            direction = parts[1].upper()
            if direction not in ("TD", "TB", "LR", "RL", "BT", "DT"):
                return False, (
                    f"Invalid direction '{parts[1]}' for {first_word}. "
                    f"Use TD, LR, BT, or RL."
                )

        return True, None


# ── 1D. EXTRACT MERMAID BLOCKS FROM LLM RESPONSE ─────────────────────────────

def extract_mermaid_blocks(text: str) -> list[str]:
    """
    Finds all ```mermaid ... ``` blocks in an LLM response string.
    Returns a list of raw Mermaid code strings (fences not included).
    Also detects bare diagram blocks that start with a known diagram type
    but were not wrapped in fences.
    """
    blocks = []

    # Pattern 1 — fenced blocks: ```mermaid ... ``` - more flexible
    fenced = re.findall(
        r"```(?:mermaid)?\s*?\n?(.*?)```",
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )
    blocks.extend(fenced)

    # Pattern 2 — bare blocks: lines starting with a known diagram type
    # (LLMs sometimes omit the fences)
    if not blocks:
        type_pattern = "|".join(re.escape(t) for t in VALID_DIAGRAM_TYPES)
        bare = re.findall(
            rf"^({type_pattern})\s.*?(?=\n\n|\Z)",
            text,
            flags=re.DOTALL | re.MULTILINE | re.IGNORECASE,
        )
        blocks.extend(bare)

    return blocks



MERMAID_HTML_TEMPLATE = """
<div id="{div_id}-wrapper" class="mermaid-container-wrapper" style="width:100%; min-height:120px; height:auto; position:relative; background:#ffffff; border-radius:12px; border:1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -1px rgba(0,0,0,0.06); margin: 20px 0; overflow: hidden; display: inline-block;">

    <!-- Header/Toolbar -->
    <div style="padding: 10px 15px; border-bottom: 1px solid #f1f5f9; background: #fff; display: flex; justify-content: space-between; align-items: center; min-height: 44px;">
        <div style="color: #64748b; font-size: 13px; font-weight: 500; display: flex; align-items: center; gap: 8px;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>
            Research Tree View (Scroll to explore)
        </div>
        <div style="display: flex; gap: 8px;">
            <button onclick="downloadSvg('{div_id}')"
                    class="mermaid-download-btn"
                    style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:6px; padding: 6px 12px; font-size: 12px; display:flex; align-items:center; gap: 6px; cursor:pointer; color: #475569; transition: all 0.2s ease;"
                    title="Download SVG">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                    <polyline points="7 10 12 15 17 10"></polyline>
                    <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                Download
            </button>
        </div>
    </div>

    <!-- Canvas — dynamic height, no fixed constraint -->
    <div id="{div_id}" class="mermaid-canvas" style="width:100%; overflow:auto; background:#ffffff; padding:20px; max-height:700px;">
        <div id="{div_id}-loading" style="color:#64748b; font-family: Inter, sans-serif; font-size: 14px; display: flex; align-items: center; justify-content: center; gap: 10px; min-height: 80px;">
            <div style="width: 18px; height: 18px; border: 2px solid #e2e8f0; border-top-color: #3b82f6; border-radius: 50%; animation: spin 1s linear infinite;"></div>
            <span>Building Tree Structure...</span>
        </div>
    </div>

    <style>
        @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
        .mermaid-canvas::-webkit-scrollbar {{ width: 10px; height: 10px; }}
        .mermaid-canvas::-webkit-scrollbar-track {{ background: #f8fafc; }}
        .mermaid-canvas::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 10px; border: 3px solid #f8fafc; }}
        .mermaid-canvas::-webkit-scrollbar-thumb:hover {{ background: #94a3b8; }}
        .mermaid-canvas svg {{
            display: block;
            max-width: none !important;
            height: auto !important;
            pointer-events: auto;
        }}
        .mermaid-download-btn:hover {{
            background: #f1f5f9 !important;
            border-color: #cbd5e1 !important;
            color: #1e293b !important;
        }}
    </style>
</div>

<script>
window.downloadSvg = function(divId) {{
    var container = document.getElementById(divId);
    if (!container) return;
    var svg = container.querySelector('svg');
    if (!svg) {{ alert("Diagram not available for download."); return; }}
    try {{
        var svgClone = svg.cloneNode(true);
        svgClone.setAttribute('style', 'background-color: white; padding: 20px;');
        if (!svgClone.getAttribute('xmlns')) svgClone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
        var svgData = new XMLSerializer().serializeToString(svgClone);
        var svgBlob = new Blob([svgData], {{type: 'image/svg+xml;charset=utf-8'}});
        var url = URL.createObjectURL(svgBlob);
        var link = document.createElement('a');
        link.href = url;
        link.download = 'Diagram-' + new Date().getTime() + '.svg';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }} catch (e) {{ console.error("Download failed", e); }}
}};

(function() {{
    var code = {escaped_code};
    var divId = "{div_id}";
    var rendered = false;

    // Timeout fallback — if diagram doesn't render in 8s, show error
    var fallbackTimer = setTimeout(function() {{
        if (!rendered) {{
            var container = document.getElementById(divId);
            if (container && !container.querySelector('svg')) {{
                container.innerHTML =
                    '<div style="color:#92400e;background:#fffbeb;padding:15px;border-radius:8px;font-size:14px;border:1px solid #fbbf24;">'
                    + '<strong>⚠️ Diagram Render Timeout</strong><br>'
                    + 'The diagram could not be rendered within the time limit. '
                    + 'This may be due to complex or invalid syntax.'
                    + '<br><br><strong>Diagram code:</strong>'
                    + '<pre style="background:#fef3c7;padding:10px;overflow-x:auto;font-size:12px;max-height:200px;">'
                    + code.replace(/</g,"&lt;")
                    + '</pre></div>';
            }}
        }}
    }}, 8000);

    async function renderMermaid() {{
        try {{
            if (typeof mermaid === "undefined") {{
                var script = document.createElement('script');
                script.src = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
                document.head.appendChild(script);
                await new Promise(function(resolve) {{
                    script.onload = resolve;
                    script.onerror = function() {{ resolve(); }};
                }});
            }}

            mermaid.initialize({{
                startOnLoad: true,
                theme: "dark",
                themeVariables: {{
                    fontSize: "14px",
                    fontFamily: "Inter, sans-serif",
                    darkMode: true,
                    primaryColor: "#302b63",
                    primaryTextColor: "#e0e0f0",
                    primaryBorderColor: "#4a45a0",
                    lineColor: "#8b85c8",
                    secondaryColor: "#24243e",
                    tertiaryColor: "#1e1e2e",
                    edgeLabelBackground: "#24243e",
                    textColor: "#e0e0f0",
                    mainBkg: "#1e1e2e",
                    nodeBorder: "#4a45a0",
                    clusterBkg: "#24243e",
                    clusterBorder: "#4a45a0",
                    titleColor: "#a8edea",
                }},
                flowchart: {{ useMaxWidth: false, htmlLabels: true, curve: "basis" }},
                mindmap: {{ useMaxWidth: false, htmlLabels: true }},
                sequence: {{ useMaxWidth: false }},
                gantt: {{ useMaxWidth: false }},
                securityLevel: "loose",
            }});

            var id = "mermaid-svg-" + Math.random().toString(36).substr(2,9);
            var result = await mermaid.render(id, code);

            var container = document.getElementById(divId);
            container.innerHTML = result.svg;
            rendered = true;
            clearTimeout(fallbackTimer);

            // Auto-resize: fit wrapper to actual SVG dimensions
            var svg = container.querySelector('svg');
            if (svg) {{
                svg.removeAttribute('style');
                svg.style.maxWidth = 'none';
                svg.style.height = 'auto';
                svg.style.display = 'block';

                var box = svg.viewBox && svg.viewBox.baseVal;
                if (box && box.width > 0) {{
                    svg.style.width = Math.max(box.width, 300) + 'px';
                    svg.style.height = (box.height + 40) + 'px';
                }}

                // Auto-resize the iframe to fit content (notify Streamlit)
                var wrapper = document.getElementById(divId + '-wrapper');
                if (wrapper) {{
                    var actualH = container.scrollHeight + 64;
                    wrapper.style.height = Math.min(actualH, 750) + 'px';
                }}

                // Send height to Streamlit iframe
                try {{
                    var totalH = document.body.scrollHeight;
                    window.parent.postMessage({{ type: 'streamlit:setFrameHeight', height: totalH }}, '*');
                }} catch(ignore) {{}}
            }}
        }} catch(e) {{
            rendered = true;
            clearTimeout(fallbackTimer);
            document.getElementById(divId).innerHTML =
                '<div style="color:#f87171;background:#1e1e2e;padding:15px;border-radius:8px;font-size:14px;border:1px solid #4a45a0;">'
                + '<strong>⚠️ Mermaid Render Error:</strong><br>'
                + '<span style="color:#fca5a5;">' + e.message + '</span>'
                + '<br><br><strong>Diagram code:</strong>'
                + '<pre style="background:#0f0c29;color:#a8edea;padding:10px;overflow-x:auto;font-size:12px;max-height:200px;border-radius:6px;">'
                + code.replace(/</g,"&lt;")
                + '</pre></div>';
        }}
    }}
    renderMermaid();
}})();
</script>
"""

MERMAID_CDN = """
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
"""


def render_content_with_mermaid(content: str) -> None:
    """
    DROP-IN REPLACEMENT for the existing render_content_with_mermaid() in app.py.

    Finds all Mermaid code blocks in the LLM response, cleans and validates
    each one, then renders them inline using Mermaid.js via Streamlit components.
    Non-Mermaid text is rendered as standard Markdown.

    Parameters
    ----------
    content : str
        The full LLM response string, which may contain ```mermaid ... ``` blocks
        mixed with regular Markdown text.
    """
    import streamlit as st
    import streamlit.components.v1 as components
    import json

    # Split content on ```mermaid ... ``` boundaries - more flexible pattern
    # Matches both ```mermaid and ``` with optional content after
    # More flexible: allows for whitespace and optional newline after opening fence
    parts = re.split(r"(```(?:mermaid)?\s*?\n?.*?```)", content, flags=re.DOTALL | re.IGNORECASE)

    # Inject Mermaid CDN once per session
    if "mermaid_cdn_injected" not in st.session_state:
        components.html(MERMAID_CDN, height=0)
        st.session_state["mermaid_cdn_injected"] = True

    import uuid

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Detect if this segment is a mermaid block - more flexible pattern
        is_mermaid = bool(re.match(r"^```(?:mermaid)?\s*?\n?", part, re.IGNORECASE))

        if is_mermaid:
            # Extract raw code (strip fences) - more flexible pattern
            raw_code = re.sub(r"^```(?:mermaid)?\s*?\n?", "", part, flags=re.IGNORECASE)
            raw_code = re.sub(r"\n?```\s*$", "", raw_code, flags=re.IGNORECASE)

            # Clean the code
            cleaned = MermaidCleaner.clean(raw_code)

            # Validate
            is_valid, error_msg = MermaidValidator.validate(cleaned)

            if not is_valid:
                logger.warning(f"[MermaidRenderer] Validation failed: {error_msg}")
                st.warning(f"⚠️ Diagram syntax issue: {error_msg}")
                with st.expander("Show diagram code"):
                    st.code(cleaned, language="text")
            else:
                div_id = f"mermaid-div-{uuid.uuid4().hex[:8]}"
                escaped = json.dumps(cleaned)

                html = MERMAID_HTML_TEMPLATE.format(
                    div_id=div_id,
                    escaped_code=escaped,
                )
                components.html(html, height=450, scrolling=True)

                # Also show code in expander for copy/debug
                with st.expander("View diagram code", expanded=False):
                    st.code(cleaned, language="text")

        else:
            # Regular Markdown text — render as normal
            st.markdown(part)
