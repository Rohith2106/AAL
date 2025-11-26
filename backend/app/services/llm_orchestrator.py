from typing import Dict, Any, Optional, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.schema import HumanMessage, SystemMessage
from app.core.config import settings
import json
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

from app.core.llm import get_llm


async def validate_record(
    structured_data: Dict[str, Any],
    reconciliation_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Validate extracted record using LLM
    
    Returns:
        Validation result with status, issues, confidence, and reasoning
    """
    llm = get_llm()
    
    record_json = json.dumps(structured_data, indent=2)
    recon_json = json.dumps(reconciliation_info, indent=2) if reconciliation_info else "No reconciliation data"
    
    prompt = f"""You are an expert accounting validation system. Your task is to validate extracted financial records.

Given a structured JSON record, analyze it for:
1. Completeness: Are all critical fields present?
2. Consistency: Do the numbers add up correctly (amount + tax = total)?
3. Format: Are dates, amounts, and other fields in correct format?
4. Reasonableness: Are the values within expected ranges?
5. Business logic: Does the record make business sense?

Extracted Record:
{record_json}

Reconciliation Information:
{recon_json}

Provide your validation in the following JSON format:
{{
    "status": "valid|invalid|warning|needs_review",
    "issues": ["list of issues found"],
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of validation"
}}

Be thorough and precise. Flag any potential issues."""
    
    try:
        logger.info("Calling LLM for validation...")
        # Run LLM call in executor with timeout (30 seconds)
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=30.0
        )
        response_text = response.content
        logger.info(f"LLM validation response received (length: {len(response_text)})")
        
        # Parse JSON from response (handle markdown code blocks)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        try:
            validation_data = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            logger.error(f"JSON parsing failed: {json_err}")
            logger.debug(f"Malformed JSON response: {response_text[:500]}...")
            # Try to extract JSON using regex as fallback
            import re
            json_match = re.search(r'\{[^}]*"status"[^}]*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    validation_data = json.loads(json_match.group(0))
                except:
                    raise ValueError("Could not parse JSON from LLM response")
            else:
                raise ValueError("Could not find valid JSON in LLM response")
        
        return {
            "status": validation_data.get("status", "needs_review"),
            "issues": validation_data.get("issues", []),
            "confidence": validation_data.get("confidence", 0.5),
            "reasoning": validation_data.get("reasoning", "")
        }
    
    except json.JSONDecodeError as json_err:
        logger.error(f"JSON parsing error in validation: {json_err}", exc_info=True)
        return {
            "status": "needs_review",
            "issues": [f"JSON parsing error: {str(json_err)}"],
            "confidence": 0.0,
            "reasoning": "LLM returned malformed JSON response"
        }
    except asyncio.TimeoutError:
        logger.error("LLM validation timed out after 30 seconds")
        return {
            "status": "needs_review",
            "issues": ["LLM validation timed out"],
            "confidence": 0.0,
            "reasoning": "Validation request timed out after 30 seconds"
        }
    except Exception as e:
        logger.error(f"Validation error: {e}", exc_info=True)
        return {
            "status": "needs_review",
            "issues": [f"Validation error: {str(e)}"],
            "confidence": 0.0,
            "reasoning": f"Error during validation: {str(e)}"
        }


async def generate_reasoning_trace(
    structured_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    reconciliation_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Generate reasoning trace for a record"""
    llm = get_llm()
    
    record_json = json.dumps(structured_data, indent=2)
    recon_json = json.dumps(reconciliation_info, indent=2) if reconciliation_info else "No reconciliation data"
    validation_json = json.dumps(validation_result, indent=2)
    
    prompt = f"""You are an AI reasoning system for accounting records. Generate a step-by-step reasoning trace.

Record:
{record_json}

Reconciliation Info:
{recon_json}

Validation Result:
{validation_json}

Generate a detailed reasoning trace showing:
1. Initial analysis of the record
2. Field-by-field examination
3. Cross-field consistency checks
4. Reconciliation analysis (if applicable)
5. Final conclusion

Format as JSON:
{{
    "steps": [
        {{"step": 1, "action": "analyzed field X", "observation": "...", "conclusion": "..."}},
        ...
    ],
    "final_conclusion": "summary of reasoning",
    "confidence_score": 0.0-1.0
}}"""
    
    try:
        logger.info("Calling LLM for reasoning trace...")
        # Run LLM call in executor with timeout (30 seconds)
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=30.0
        )
        response_text = response.content
        logger.info(f"LLM reasoning trace response received (length: {len(response_text)})")
        
        # Parse JSON
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()
        
        trace_data = json.loads(response_text)
        
        return {
            "steps": trace_data.get("steps", []),
            "final_conclusion": trace_data.get("final_conclusion", ""),
            "confidence_score": trace_data.get("confidence_score", 0.5),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except asyncio.TimeoutError:
        logger.error("LLM reasoning trace timed out after 30 seconds")
        return {
            "steps": [{"step": 1, "action": "timeout", "observation": "Request timed out", "conclusion": "Error occurred"}],
            "final_conclusion": "Reasoning trace generation timed out after 30 seconds",
            "confidence_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Reasoning trace error: {e}", exc_info=True)
        return {
            "steps": [{"step": 1, "action": "error", "observation": str(e), "conclusion": "Error occurred"}],
            "final_conclusion": f"Error generating reasoning trace: {str(e)}",
            "confidence_score": 0.0,
            "timestamp": datetime.utcnow().isoformat()
        }


async def generate_explanation(
    structured_data: Dict[str, Any],
    validation_result: Dict[str, Any],
    reasoning_trace: Dict[str, Any]
) -> str:
    """Generate human-readable explanation"""
    llm = get_llm()
    
    record_json = json.dumps(structured_data, indent=2)
    validation_json = json.dumps(validation_result, indent=2)
    trace_json = json.dumps(reasoning_trace, indent=2)
    
    prompt = f"""Generate a clear, human-readable explanation of the validation and reasoning process.

Record:
{record_json}

Validation Result:
{validation_json}

Reasoning Trace:
{trace_json}

Provide:
1. A summary of what was analyzed
2. Key findings
3. Any issues or concerns
4. Recommendations for next steps

Write in clear, professional language suitable for accounting professionals."""
    
    try:
        logger.info("Calling LLM for explanation...")
        # Run LLM call in executor with timeout (30 seconds)
        def call_llm():
            return llm.invoke([HumanMessage(content=prompt)])
        
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(None, call_llm),
            timeout=30.0
        )
        logger.info(f"LLM explanation response received (length: {len(response.content)})")
        return response.content
    except asyncio.TimeoutError:
        logger.error("LLM explanation timed out after 30 seconds")
        return "Explanation generation timed out after 30 seconds. Please try again."
    except Exception as e:
        logger.error(f"Explanation generation error: {e}", exc_info=True)
        return f"Error generating explanation: {str(e)}"


async def orchestrate(
    structured_data: Dict[str, Any],
    reconciliation_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Main orchestration method
    
    Returns:
        Complete orchestration output with validation, reasoning, and explanation
    """
    record_id = structured_data.get("record_id", f"record_{datetime.now().timestamp()}")
    structured_data["record_id"] = record_id
    
    # Step 1: Validate
    logger.info(f"Validating record {record_id}...")
    validation_result = await validate_record(structured_data, reconciliation_info)
    
    # Step 2: Generate reasoning trace
    logger.info(f"Generating reasoning trace for record {record_id}...")
    reasoning_trace = await generate_reasoning_trace(structured_data, validation_result, reconciliation_info)
    
    # Step 3: Generate explanation
    logger.info(f"Generating explanation for record {record_id}...")
    explanation = await generate_explanation(structured_data, validation_result, reasoning_trace)
    
    # Step 4: Generate recommendations
    recommendations = []
    if validation_result["status"] == "invalid":
        recommendations.append("Record requires manual review before processing")
    elif validation_result["status"] == "warning":
        recommendations.append("Review flagged issues before finalizing")
    if validation_result["confidence"] < 0.7:
        recommendations.append("Low confidence score - consider manual verification")
    if not recommendations:
        recommendations.append("Record appears valid and ready for ledger entry")
    
    return {
        "record_id": record_id,
        "validation_result": validation_result,
        "reasoning_trace": reasoning_trace,
        "explanation": explanation,
        "recommendations": recommendations,
        "timestamp": datetime.utcnow().isoformat()
    }

