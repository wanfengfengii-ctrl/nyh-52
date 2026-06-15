import difflib
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass


@dataclass
class TextDiff:
    diff_type: str
    position_start: int
    position_end: int
    text: str
    reference_text: str
    description: str


DIFF_TYPE_MISSING = "missing"
DIFF_TYPE_VARIANT = "variant"
DIFF_TYPE_ADDED = "added"
DIFF_TYPE_REVERSED = "reversed"

DIFF_TYPE_LABELS = {
    DIFF_TYPE_MISSING: "缺字",
    DIFF_TYPE_VARIANT: "异体字",
    DIFF_TYPE_ADDED: "衍文",
    DIFF_TYPE_REVERSED: "倒置"
}

DIFF_TYPE_COLORS = {
    DIFF_TYPE_MISSING: "#e74c3c",
    DIFF_TYPE_VARIANT: "#f39c12",
    DIFF_TYPE_ADDED: "#8e44ad",
    DIFF_TYPE_REVERSED: "#2980b9"
}


def align_texts(texts: Dict[str, str]) -> Dict[str, List[Any]]:
    version_names = list(texts.keys())
    if len(version_names) < 2:
        result = {}
        for name, text in texts.items():
            result[name] = [{"type": "equal", "text": text, "diffs": []}]
        return result

    base_name = version_names[0]
    base_text = texts[base_name]
    
    result = {}
    result[base_name] = _split_to_segments(base_text, [])
    
    for other_name in version_names[1:]:
        other_text = texts[other_name]
        diffs = compare_two_texts(base_text, other_text)
        result[other_name] = _split_to_segments(other_text, diffs)
    
    return result


def _split_to_segments(text: str, diffs: List[TextDiff]) -> List[Dict[str, Any]]:
    segments = []
    
    if not diffs:
        if text:
            segments.append({"type": "equal", "text": text, "diffs": []})
        return segments
    
    diffs_sorted = sorted(diffs, key=lambda d: d.position_start)
    
    current_pos = 0
    for diff in diffs_sorted:
        if diff.position_start > current_pos:
            segments.append({
                "type": "equal",
                "text": text[current_pos:diff.position_start],
                "diffs": []
            })
        
        segments.append({
            "type": "diff",
            "text": diff.text,
            "diffs": [diff]
        })
        current_pos = diff.position_end
    
    if current_pos < len(text):
        segments.append({
            "type": "equal",
            "text": text[current_pos:],
            "diffs": []
        })
    
    return segments


def compare_two_texts(text_a: str, text_b: str) -> List[TextDiff]:
    diffs = []
    
    if not text_a or not text_b:
        if text_b and not text_a:
            diffs.append(TextDiff(
                diff_type=DIFF_TYPE_ADDED,
                position_start=0,
                position_end=len(text_b),
                text=text_b,
                reference_text="",
                description=f"衍文: '{text_b}'"
            ))
        return diffs
    
    matcher = difflib.SequenceMatcher(None, text_a, text_b)
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        elif tag == "replace":
            chunk_a = text_a[i1:i2]
            chunk_b = text_b[j1:j2]
            
            if len(chunk_a) == len(chunk_b) and len(chunk_a) == 1:
                diff_type = DIFF_TYPE_VARIANT
                desc = f"异体字: 原 '{chunk_a}' vs 异 '{chunk_b}'"
            elif _is_reversed(chunk_a, chunk_b):
                diff_type = DIFF_TYPE_REVERSED
                desc = f"倒置: '{chunk_a}' vs '{chunk_b}'"
            else:
                diff_type = DIFF_TYPE_VARIANT
                desc = f"异文: '{chunk_a}' vs '{chunk_b}'"
            
            diffs.append(TextDiff(
                diff_type=diff_type,
                position_start=j1,
                position_end=j2,
                text=chunk_b,
                reference_text=chunk_a,
                description=desc
            ))
            
        elif tag == "delete":
            chunk_a = text_a[i1:i2]
            if j1 <= len(text_b):
                diffs.append(TextDiff(
                    diff_type=DIFF_TYPE_MISSING,
                    position_start=j1,
                    position_end=j1,
                    text="",
                    reference_text=chunk_a,
                    description=f"缺字: 缺少 '{chunk_a}'"
                ))
            
        elif tag == "insert":
            chunk_b = text_b[j1:j2]
            diffs.append(TextDiff(
                diff_type=DIFF_TYPE_ADDED,
                position_start=j1,
                position_end=j2,
                text=chunk_b,
                reference_text="",
                description=f"衍文: 多出 '{chunk_b}'"
            ))
    
    return diffs


def _is_reversed(text_a: str, text_b: str) -> bool:
    if len(text_a) != len(text_b) or len(text_a) < 2:
        return False
    return text_a == text_b[::-1]


def get_all_diffs_for_passage(texts: Dict[str, str], passage_id: int, 
                              project_id: int, version_ids: Dict[str, int]) -> List[Dict[str, Any]]:
    all_diffs = []
    version_names = list(texts.keys())
    
    if len(version_names) < 2:
        return all_diffs
    
    base_name = version_names[0]
    base_text = texts[base_name]
    base_version_id = version_ids[base_name]
    
    for other_name in version_names[1:]:
        other_text = texts[other_name]
        other_version_id = version_ids[other_name]
        text_diffs = compare_two_texts(base_text, other_text)
        
        for td in text_diffs:
            all_diffs.append({
                "project_id": project_id,
                "passage_id": passage_id,
                "version_id": other_version_id,
                "diff_type": td.diff_type,
                "position_start": td.position_start,
                "position_end": td.position_end,
                "text": td.text,
                "reference_text": td.reference_text,
                "description": td.description,
                "version_name": other_name,
                "base_version_name": base_name
            })
    
    return all_diffs


def render_segment_html(segment: Dict[str, Any]) -> str:
    if segment["type"] == "equal":
        return segment["text"]
    
    html_parts = []
    for diff in segment["diffs"]:
        color = DIFF_TYPE_COLORS.get(diff.diff_type, "#333")
        label = DIFF_TYPE_LABELS.get(diff.diff_type, diff.diff_type)
        
        if diff.diff_type == DIFF_TYPE_MISSING:
            html_parts.append(
                f'<span class="diff-mark diff-missing" style="color:{color};border-bottom:2px dashed {color};" '
                f'title="{label}: {diff.description}">□</span>'
            )
        else:
            html_parts.append(
                f'<span class="diff-mark diff-{diff.diff_type}" style="background-color:{color}20;border-bottom:2px solid {color};" '
                f'title="{label}: {diff.description}">{segment["text"]}</span>'
            )
    
    return "".join(html_parts)
