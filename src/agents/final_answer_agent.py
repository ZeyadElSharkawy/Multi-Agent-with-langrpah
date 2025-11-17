# File: src/agents/final_answer_agent.py (FIXED VERSION)
"""
Final Answer Agent - Fixed to properly parse fact checker results
"""

import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv
load_dotenv()

# Gemini Setup
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("⚠️ Missing Google API key.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

def extract_json_from_text(text: str) -> dict:
    """Extract JSON from text, handling markdown code blocks and malformed JSON."""
    # Remove markdown code blocks
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    
    # Try to find JSON pattern
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Try to fix common JSON issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            try:
                return json.loads(json_str)
            except:
                pass
    return {}

def generate_final_answer(original_query: str, verified_claims: dict, context_docs: list) -> dict:
    """
    Generate a final answer incorporating verified claims and citations.
    Returns a dict with the answer and metadata.
    """
    
    print(f"🔍 Final Answer Agent received verified_claims type: {type(verified_claims)}")
    print(f"🔍 Verified claims keys: {list(verified_claims.keys()) if verified_claims else 'EMPTY'}")
    
    # Debug: Print what we actually received
    if verified_claims:
        print("📊 Verified claims structure (first 2 items):")
        for i, (key, value) in enumerate(list(verified_claims.items())[:2]):
            print(f"  Key {i}: '{key}'")
            print(f"  Value type: {type(value)}")
            if isinstance(value, dict):
                print(f"  Status: {value.get('verification_status', 'MISSING')}")
                print(f"  Confidence: {value.get('confidence', 'MISSING')}")
    
    # Prepare verification summary
    verification_summary = []
    supported_claims = []
    partially_supported_claims = []
    not_supported_claims = []
    contradicted_claims = []
    
    # Handle the verified claims structure
    if verified_claims:
        for claim_key, verification_data in verified_claims.items():
            # The claim_key might be the actual claim text or a reference
            actual_claim = claim_key
            
            # Extract verification data
            if isinstance(verification_data, dict):
                status = verification_data.get('verification_status', 'UNKNOWN')
                confidence = verification_data.get('confidence', 0)
                evidence = verification_data.get('evidence', '')
                explanation = verification_data.get('explanation', '')
            else:
                # Fallback if structure is different
                status = 'UNKNOWN'
                confidence = 0
                evidence = ''
                explanation = ''
            
            verification_summary.append(f"- {actual_claim} [{status}, Confidence: {confidence}%]")
            
            if status == 'SUPPORTED':
                supported_claims.append(actual_claim)
            elif status == 'PARTIALLY_SUPPORTED':
                partially_supported_claims.append(actual_claim)
            elif status == 'NOT_SUPPORTED':
                not_supported_claims.append(actual_claim)
            elif status == 'CONTRADICTED':
                contradicted_claims.append(actual_claim)
            else:
                not_supported_claims.append(actual_claim)
    
    print(f"📊 Claim breakdown: {len(supported_claims)} supported, {len(partially_supported_claims)} partial, {len(not_supported_claims)} not supported, {len(contradicted_claims)} contradicted")
    
    # Prepare context with sources
    context_with_sources = []
    sources_used = set()
    for i, doc in enumerate(context_docs):
        source = ""
        content = ""
        
        if hasattr(doc, 'metadata'):
            source = doc.metadata.get('source', f'Document {i+1}')
            content = doc.page_content
        elif isinstance(doc, dict):
            source = doc.get('metadata', {}).get('source', f'Document {i+1}')
            content = doc.get('content', '')
        else:
            source = f'Document {i+1}'
            content = str(doc)
            
        sources_used.add(source)
        context_with_sources.append(f"[Source: {source}]\n{content}")
    
    # Calculate overall confidence
    overall_confidence = calculate_overall_confidence(verified_claims)
    
    print(f"🎯 Overall confidence calculated: {overall_confidence}%")
    
    # Generate appropriate prompt based on verification results
    if len(supported_claims) > 0:
        # We have supported claims - create a positive answer
        prompt = f"""
**TASK**: You are a final answer synthesizer. Create a comprehensive, well-structured answer to the user's query using the verified claims and context provided.

**ORIGINAL QUERY**: {original_query}

**VERIFICATION RESULTS**:
- SUPPORTED Claims: {len(supported_claims)}
- PARTIALLY SUPPORTED: {len(partially_supported_claims)} 
- NOT SUPPORTED: {len(not_supported_claims)}
- CONTRADICTED: {len(contradicted_claims)}

**SUPPORTED CLAIMS**:
{chr(10).join([f"- {claim}" for claim in supported_claims])}

**SUPPORTING CONTEXT DOCUMENTS**:
{chr(10).join(context_with_sources)}

**INSTRUCTIONS**:
1. Create a clear, well-structured answer focusing on the SUPPORTED claims
2. Include specific details and examples from the context
3. Cite your sources using [Source: ...] notation
4. Be honest about any limitations or uncertainties
5. The overall confidence in this answer is {overall_confidence}%

**FINAL ANSWER**:
"""
    else:
        # No supported claims - be honest about limitations
        prompt = f"""
**TASK**: You are a final answer synthesizer. The fact-checking process found limited support for claims related to the user's query.

**ORIGINAL QUERY**: {original_query}

**VERIFICATION RESULTS**:
- SUPPORTED Claims: {len(supported_claims)}
- PARTIALLY SUPPORTED: {len(partially_supported_claims)}
- NOT SUPPORTED: {len(not_supported_claims)} 
- CONTRADICTED: {len(contradicted_claims)}

**CONTEXT DOCUMENTS**:
{chr(10).join(context_with_sources)}

**INSTRUCTIONS**:
1. Honestly state that limited verified information was found
2. Mention what the documents do contain that might be related
3. Suggest what additional information would be needed
4. The overall confidence in available information is {overall_confidence}%

**FINAL ANSWER**:
"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Create result structure
        result = {
            "final_answer": response_text,
            "confidence_score": overall_confidence,
            "verified_sources": list(sources_used),
            "limitations": f"Based on verification: {len(supported_claims)} supported, {len(not_supported_claims)} not supported claims"
        }
        
        # Add claim breakdown for transparency
        result["claim_breakdown"] = {
            "supported": len(supported_claims),
            "partially_supported": len(partially_supported_claims),
            "not_supported": len(not_supported_claims),
            "contradicted": len(contradicted_claims)
        }
        
        return result
        
    except Exception as e:
        print(f"❌ Final answer generation error: {e}")
        # Fallback structure
        return {
            "final_answer": f"I encountered an error while generating the final answer: {str(e)}",
            "confidence_score": overall_confidence,
            "verified_sources": list(sources_used),
            "limitations": "System error during answer generation",
            "claim_breakdown": {
                "supported": len(supported_claims),
                "partially_supported": len(partially_supported_claims), 
                "not_supported": len(not_supported_claims),
                "contradicted": len(contradicted_claims)
            }
        }

def calculate_overall_confidence(verified_claims: dict) -> float:
    """Calculate overall confidence score from individual claim verifications."""
    if not verified_claims:
        return 0.0
    
    total_confidence = 0
    valid_claims = 0
    
    for claim_key, verification_data in verified_claims.items():
        if isinstance(verification_data, dict):
            confidence = verification_data.get('confidence', 0)
            status = verification_data.get('verification_status', 'NOT_SUPPORTED')
            
            # Only count claims that were actually verified
            if status in ['SUPPORTED', 'PARTIALLY_SUPPORTED', 'NOT_SUPPORTED', 'CONTRADICTED']:
                # For SUPPORTED claims, use the confidence directly
                if status == 'SUPPORTED':
                    total_confidence += confidence
                # For PARTIALLY_SUPPORTED, use reduced confidence
                elif status == 'PARTIALLY_SUPPORTED':
                    total_confidence += confidence * 0.7
                # For NOT_SUPPORTED and CONTRADICTED, they don't contribute positively
                valid_claims += 1
    
    if valid_claims == 0:
        return 0.0
    
    return min(100.0, round(total_confidence / valid_claims, 2))

if __name__ == "__main__":
    # Test with the actual fact checker results structure
    print("🧪 Testing Final Answer Agent with actual structure...")
    
    test_verified_claims = {
        "The text mentions a script named \"Workflow Status Check (Pre-Escalation)\" as Script 1.": {
            "verification_status": "SUPPORTED", 
            "confidence": 100,
            "evidence": "Script 1: Workflow Status Check (Pre-Escalation)",
            "explanation": "The context document explicitly states this."
        },
        "The workflow status check script for chatbots resolves L0 issues": {
            "verification_status": "SUPPORTED",
            "confidence": 95, 
            "evidence": "Objective: Resolve L0 (low-complexity) issues and efficiently triage/collect data for L1 escalation.",
            "explanation": "The objective of the script is mentioned in the overview"
        }
    }
    
    test_docs = [{"content": "Test content", "metadata": {"source": "Test Source"}}]
    
    result = generate_final_answer("Test query", test_verified_claims, test_docs)
    print(f"✅ Test result: {result['confidence_score']}% confidence")
    print(f"✅ Claim breakdown: {result['claim_breakdown']}")