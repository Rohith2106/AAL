"""
Utility functions for robust JSON parsing from LLM responses.
Handles malformed JSON, markdown code blocks, and common formatting issues.
"""

import json
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def clean_json_string(text: str) -> str:
    """
    Clean and extract JSON from LLM response text.
    Handles markdown code blocks, extra whitespace, and common formatting issues.
    
    Args:
        text: Raw text from LLM response
        
    Returns:
        Cleaned JSON string
    """
    if not text:
        return ""
    
    # Remove markdown code blocks
    if "```json" in text:
        parts = text.split("```json")
        if len(parts) > 1:
            text = parts[1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) > 1:
            # Try to find the JSON part (usually the first code block)
            for part in parts[1:]:
                part = part.strip()
                if part.startswith("{") or part.startswith("["):
                    text = part
                    break
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Find the first { or [ and last } or ]
    first_brace = text.find("{")
    first_bracket = text.find("[")
    
    if first_brace == -1 and first_bracket == -1:
        return text
    
    start_idx = min(
        i for i in [first_brace, first_bracket] if i != -1
    )
    
    # Find matching closing brace/bracket
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        # Looking for JSON object
        brace_count = 0
        in_string = False
        escape_next = False
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
        
        if end_idx > start_idx:
            text = text[start_idx:end_idx]
    else:
        # Looking for JSON array
        bracket_count = 0
        in_string = False
        escape_next = False
        end_idx = -1
        
        for i in range(start_idx, len(text)):
            char = text[i]
            
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\':
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        end_idx = i + 1
                        break
        
        if end_idx > start_idx:
            text = text[start_idx:end_idx]
    
    return text.strip()


def repair_json_string(text: str) -> str:
    """
    Attempt to repair common JSON issues like unterminated strings.
    
    Args:
        text: JSON string that may be malformed
        
    Returns:
        Repaired JSON string
    """
    if not text:
        return "{}"
    
    # Track string state to detect unterminated strings
    in_string = False
    escape_next = False
    last_quote_pos = -1
    result_chars = list(text)
    
    # First pass: identify unterminated strings
    for i, char in enumerate(result_chars):
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"':
            last_quote_pos = i
            in_string = not in_string
    
    # If we're still in a string at the end, try to close it intelligently
    if in_string and last_quote_pos >= 0:
        # Look ahead from the last quote to find where the string should end
        remaining = text[last_quote_pos + 1:]
        
        # Simple heuristic: if we see a colon, comma, or closing brace/bracket soon after,
        # the string probably should have ended before it
        # Look for the first structural character that's likely outside the string
        for i, char in enumerate(remaining[:50]):  # Only look at next 50 chars
            if char in [':', ',', '}', ']']:
                # Check if it's not escaped (simple check - look at previous char)
                if i == 0 or remaining[i-1] != '\\':
                    # Insert closing quote before this character
                    insert_pos = last_quote_pos + 1 + i
                    result_chars.insert(insert_pos, '"')
                    text = ''.join(result_chars)
                    break
        else:
            # No structural character found, just close at the end
            result_chars.append('"')
            text = ''.join(result_chars)
    
    # Try to close unclosed braces/brackets (but be careful not to over-close)
    # Only close if we're at the end of what looks like a complete structure
    open_braces = text.count('{') - text.count('}')
    open_brackets = text.count('[') - text.count(']')
    
    # Only add closing braces/brackets if we're reasonably sure they should be closed
    # (i.e., we're at the end of the text and have unclosed structures)
    if open_braces > 0 and open_braces <= 5:  # Reasonable limit
        text = text + '}' * open_braces
    if open_brackets > 0 and open_brackets <= 5:
        text = text + ']' * open_brackets
    
    return text


def parse_llm_json_response(response_text: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Robustly parse JSON from LLM response.
    Handles markdown, malformed JSON, and common formatting issues.
    
    Args:
        response_text: Raw text from LLM response
        default: Default value to return if parsing fails
        
    Returns:
        Parsed JSON object (dict)
    """
    if default is None:
        default = {}
    
    if not response_text:
        logger.warning("Empty response text, returning default")
        return default
    
    try:
        # Step 1: Clean the text
        cleaned = clean_json_string(response_text)
        
        if not cleaned:
            logger.warning("No JSON found in response text")
            return default
        
        # Step 2: Try to parse directly
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.debug(f"Initial JSON parse failed: {e}, attempting repair...")
            
            # Step 3: Try to repair common issues
            repaired = repair_json_string(cleaned)
            
            try:
                return json.loads(repaired)
            except json.JSONDecodeError as e2:
                logger.debug(f"Repaired JSON parse failed: {e2}, trying regex extraction...")
                
                # Step 4: Try regex extraction as last resort
                # Look for JSON object pattern - be more aggressive
                # Try to find the largest JSON-like structure
                json_patterns = [
                    r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested objects
                    r'\{.*?"status".*?\}',  # Object with "status" field
                    r'\{.*?"items".*?\}',  # Object with "items" field
                    r'\{[^}]*\}',  # Simple object
                ]
                
                for pattern in json_patterns:
                    json_match = re.search(pattern, cleaned, re.DOTALL)
                    if json_match:
                        try:
                            candidate = json_match.group(0)
                            # Try to repair and parse
                            repaired_candidate = repair_json_string(candidate)
                            return json.loads(repaired_candidate)
                        except json.JSONDecodeError:
                            continue
                
                # Try to extract just the fields we need
                logger.error(f"Failed to parse JSON after all attempts: {e2}")
                logger.debug(f"Problematic text (first 500 chars): {cleaned[:500]}")
                return default
                
    except Exception as e:
        logger.error(f"Unexpected error parsing JSON: {e}", exc_info=True)
        return default

