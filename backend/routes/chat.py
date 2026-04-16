from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from services.ai import ai_service
from services.faq import faq_service
from services.knowledge import knowledge_service
from services.chatbot_profile import chatbot_profile
from services.session import session_service
from services.database import db
from utils.resilience import fallback_string
import re

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"
    language: str = "en-US"
    is_explicit: bool = False


class ChatResponse(BaseModel):
    response: str
    source: str
    language: str
    suggestions: List[str] = []

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    query = request.query
    session_id = request.session_id
    
    # Get/Update Session
    context = await session_service.get_context(session_id)
    language = request.language if request.is_explicit else context.get("language", "en-US")
    
    # High-Reliability Devanagari "Sensing" (Regex → AI)
    is_hindi_query = False
    if re.search(r'[\u0900-\u097F]', query) or any(m in query for m in ['।', '॥']):
        is_hindi_query = True
    else:
        # Ask AI for detection (handles Hinglish and informal Hindi)
        detected_lang = await ai_service.detect_language(query)
        if "hi" in detected_lang.lower():
            is_hindi_query = True

    # Deterministic Logic: If the user explicitly locked a language, use it. 
    # Otherwise, follow the sensing results.
    if request.is_explicit:
        language = request.language
    elif is_hindi_query:
        language = "hi-IN"
    else:
        language = "en-US"


    await session_service.update_context(session_id, language=language)

    search_query = query 
    final_response = ""
    source = "fallback"
    detected_intent = None

    # Known course keywords — if any appear in the query, skip contextual enrichment
    KNOWN_COURSE_KEYWORDS = [
        "bca", "bba", "b.com", "bcom", "b.sc", "bsc", "m.com", "mcom",
        "b.voc", "bvoc", "bjmc", "m.sc", "msc", "m.voc", "mvoc", "bph",
        "arts", "commerce", "science", "vocational", "zoology", "botany",
        "physiotherapy", "journalism", "anthropology",
    ]

    last_course = context.get("last_course")
    query_lower_for_ctx = query.lower()
    query_has_course = any(kw in query_lower_for_ctx for kw in KNOWN_COURSE_KEYWORDS)

    if last_course and not query_has_course and \
       any(kw in query_lower_for_ctx for kw in ["duration", "faculty", "seats", "eligibility", "deadline"]):

        # Special case for 'faculty' - make it 'faculty of BCA' instead of 'faculty for BCA'
        connector = "of" if "faculty" in query_lower_for_ctx else "for"
        query = f"{query} {connector} {last_course}"
        # print(f"Contextual Enrichment: {query}")

    # 1. Identity Module (Highest Priority)
    try:
        profile_response = chatbot_profile.get_identity_response(query, language)
        if profile_response:
            final_response = profile_response
            source = "profile"
    except Exception as e:
        print(f"Profile check failed: {e}")

    # 2. Fast-Path Keyword Matcher (Zero-Failure Stability Layer)
    if not final_response:
        q_clean = query.lower().strip()

        # Priority-ordered list: most specific first
        kw_priority = [
            # --- Admission ---

            ("admission deadline", "ADMISSION_DEADLINE"),
            ("kab se start", "ADMISSION_DEADLINE"),
            ("admission kab", "ADMISSION_DEADLINE"),
            ("last date", "ADMISSION_DEADLINE"),
            ("अंतिम तिथि", "ADMISSION_DEADLINE"),
            ("एडमिशन", "ADMISSION_PROCEDURE"),
            ("admission process", "ADMISSION_PROCEDURE"),
            ("how to apply", "ADMISSION_PROCEDURE"),
            ("kaise apply", "ADMISSION_PROCEDURE"),
            # --- Faculty ---
            ("who is", "FACULTY_BY_NAME"),
            ("dr.", "FACULTY_BY_NAME"),
            ("professor", "FACULTY_BY_NAME"),
            ("शिक्षक", "FACULTY_BY_DEPT"),
            ("hod", "FACULTY_BY_DEPT"),
            ("faculty", "FACULTY_BY_DEPT"),
            # --- Assets & Facilities ---
            ("scholarship", "SCHOLARSHIP_INFO"),
            ("छात्रवृत्ति", "SCHOLARSHIP_INFO"),
            ("library", "LIBRARY_INFRA"),
            ("पुस्तकालय", "LIBRARY_INFRA"),
            ("hostel", "HOSTEL_INFO"),
            ("हॉस्टल", "HOSTEL_INFO"),
            # --- Contact & Location ---
            ("संपर्क", "COLLEGE_CONTACT"),
            ("फोन नंबर", "COLLEGE_CONTACT"),
            ("contact", "COLLEGE_CONTACT"),
            ("where is", "COLLEGE_ADDRESS"),
            ("address", "COLLEGE_ADDRESS"),
            ("address", "COLLEGE_ADDRESS"),
            ("kahan", "COLLEGE_ADDRESS"),
            ("पता", "COLLEGE_ADDRESS"),
            # --- Courses (lowest priority) ---
            ("kya course", "COURSE_INFO"),
            ("कोर्स", "COURSE_INFO"),
            ("bca", "COURSE_INFO"),
            ("bba", "COURSE_INFO"),

            ("b.com", "COURSE_INFO"),
            ("b.sc", "COURSE_INFO"),
            ("bsc", "COURSE_INFO"),
            ("b.a", "COURSE_INFO"),
            ("b.voc", "COURSE_INFO"),
            ("bvoc", "COURSE_INFO"),
            ("vocational", "COURSE_INFO"),
            ("zoology", "COURSE_INFO"),
            ("botany", "COURSE_INFO"),
            ("physiotherapy", "COURSE_INFO"),
            ("m.com", "COURSE_INFO"),
            ("msc", "COURSE_INFO"),
            ("ma ", "COURSE_INFO"),
            ("m.voc", "COURSE_INFO"),
            ("mph ", "COURSE_INFO"),
            ("postgraduate", "COURSE_INFO"),
            ("pg course", "COURSE_INFO"),
            ("pgdrs", "COURSE_INFO"),
            ("gis", "COURSE_INFO"),
            ("remote sensing", "COURSE_INFO"),
            ("diploma", "COURSE_INFO"),
            ("certificate", "COURSE_INFO"),
        ]

        for kw, intent in kw_priority:
            if kw in q_clean:
                detected_intent = intent
                break
        
        # 3. Structured Knowledge Engine (Intent-Based)
        try:
            if not detected_intent:
                # Preprocess query for intent matching - Standardize Hinglish/Informal
                search_query = await ai_service.standardize_query(query)
                knowledge_result = await knowledge_service.get_intent_data(search_query)
            else:
                # If keyword matched, ask knowledge_service for specific intent data directly
                knowledge_result = await knowledge_service.get_intent_data_by_intent(detected_intent, query)
            
            if knowledge_result:
                # Check for deterministic fixed responses first
                fixed_en = knowledge_result.get("fixed_response_en")
                fixed_hi = knowledge_result.get("fixed_response_hi")
                
                if "hi" in language.lower() and fixed_hi:
                    final_response = fixed_hi
                    source = f"rule:{knowledge_result['intent'].lower()}:hi"
                elif fixed_en:
                    if "hi" in language.lower():
                        # If we have English fixed response but need Hindi, use AI to translate it
                        final_response = await ai_service.get_response(query, context=fixed_en, language=language)
                        source = f"rule_translated:{knowledge_result['intent'].lower()}:hi"
                    else:
                        final_response = fixed_en
                        source = f"rule:{knowledge_result['intent'].lower()}:en"

                if not final_response:
                    # Try context-augmented AI response
                    ai_resp = await ai_service.get_response(
                        query, 
                        context=knowledge_result.get("context_string", ""), 
                        language=language
                    )
                    
                    # Zero-Failure: If AI fails, use the raw context string directly
                    if ai_resp == "__AI_FAILURE__":
                        final_response = knowledge_result.get("context_string", "")
                        source = f"knowledge:db_fallback:{knowledge_result['intent'].lower()}"
                    else:
                        final_response = ai_resp
                        source = f"knowledge:{knowledge_result['intent'].lower()}"
                
                detected_intent = knowledge_result["intent"]

            # Always update last_course if the query mentions a known course
            # (moved outside knowledge_result block so it works even when AI/knowledge fails)
            COURSE_SESSION_MAP = [
                ("m.com", "M.Com"), ("mcom", "M.Com"),
                ("bca", "BCA"),
                ("bba", "BBA"),
                ("b.com", "B.Com"), ("bcom", "B.Com"),
                ("b.sc", "B.Sc"), ("bsc", "B.Sc"),
                ("b.a", "B.A"), (" ba ", "B.A"),
                ("b.voc", "B.Voc"), ("bvoc", "B.Voc"),
                ("m.sc", "M.Sc"), ("msc", "M.Sc"),
                ("m.a", "M.A"),
            ]
            q_for_session = query.lower()
            for kw, course_label in COURSE_SESSION_MAP:
                if kw in q_for_session:
                    await session_service.update_context(session_id, last_course=course_label)
                    break
            # print(f"Handled by Knowledge Engine: {detected_intent} (Source: {source})")

        except Exception as e:
            # print(f"Knowledge Engine failed: {e}")
            pass


    # 3. FAQ / Semantic Search
    if not final_response:
        try:
            # Fallback to semantic FAQ search using standardized query
            faq_answer = await faq_service.get_answer(search_query)
            if faq_answer:
                if "hi" in language.lower():
                    # Translate FAQ answer to Hindi using context-aware rephrasing
                    ai_fa_resp = await ai_service.get_response(query, context=faq_answer, language=language)
                    if ai_fa_resp == "__AI_FAILURE__":
                        final_response = faq_answer
                        source = "faq_search:db_fallback:hi"
                    else:
                        final_response = ai_fa_resp
                        source = "faq_search:hi"
                else:
                    final_response = faq_answer
                    source = "faq_search"
                # print(f"Handled by FAQ Search: {search_query}")

        except Exception as e:
            print(f"FAQ lookup failed: {e}")

    # 4. General AI Case (Last Resort)
    if not final_response:
        try:
            ai_gen_resp = await ai_service.get_response(query, language=language)
            if ai_gen_resp == "__AI_FAILURE__":
                # Emergency Keyword Fallback - If AI is dead, try one last local database keyword scan
                keywords = {
                    "admission": "ADMISSION_GENERAL",
                    "course": "COURSE_INFO",

                    "hostel": "CAMPUS_GENERAL",
                    "library": "CAMPUS_GENERAL",
                    "placement": "CAMPUS_GENERAL",
                    "contact": "CAMPUS_GENERAL"
                }
                match = next((v for k, v in keywords.items() if k in query.lower()), None)
                if match:
                   res = await knowledge_service.get_intent_data_by_intent(match, query)
                   final_response = res.get("context_string", "I'm having trouble rephrasing, but here is some data: " + res.get("context_string", ""))
                   source = "emergency_keyword_fallback"
                else:
                    final_response = (
                        "I'm sorry, I'm unable to process your query right now. "
                        "Please feel free to reach out to our college support directly:\n\n"
                        "📧 Email: support@npgc.in\n"
                        "📞 Phone: 0522 4021304\n\n"
                        "Our team will be happy to assist you!"
                    )
                    source = "ai_total_failure_contact"
            else:
                final_response = ai_gen_resp
                source = "ai"
                # Best-effort: save learned query
                await faq_service.save_resolved_query(query, final_response)
        except Exception as e:
            print(f"AI service failed: {e}")
            final_response = (
                "I'm sorry, I'm unable to process your query right now. "
                "Please feel free to reach out to our college support directly:\n\n"
                "📧 Email: support@npgc.in\n"
                "📞 Phone: 0522 4021304\n\n"
                "Our team will be happy to assist you!"
            )
            source = "ai_exception_contact"

    # 5. Hybrid Suggestions (Static Map + AI Fallback)
    suggestions = []
    static_suggestions = {

        "COURSE_INFO": ["What are the available courses?", "Tell me about the BCA syllabus", "Which course is best for me?"],
        "ADMISSION_DEADLINE": ["When is the last date to apply?", "How can I apply online?", "What are the eligibility criteria?"],
        "FACULTY_BY_DEPT": ["Who are the faculty members in BCA?", "Tell me about the science faculty", "Who is the HOD?"],
        "ALUMNI_INFO": ["What is the placement record?", "Tell me about notable alumni", "What are the career prospects?"]
    }
    
    if detected_intent in static_suggestions:
        suggestions = static_suggestions[detected_intent]
    else:
        try:
            # Only call AI for suggestions if no static match (saves quota)
            suggestions = await ai_service.get_suggestions(query, final_response, intent=detected_intent)
        except Exception as e:
            suggestions = ["Admission info", "About NPGC", "Contact details"]

    return ChatResponse(
        response=final_response, 
        source=source, 
        language="hi-IN" if any('\u0900' <= char <= '\u097f' for char in final_response) else language,
        suggestions=suggestions
    )

@router.get("/autocomplete")
async def autocomplete(q: str):
    """
    Returns auto-suggestions based on partial query.
    Searches FAQs and Course names in MySQL.
    """
    if not q or len(q) < 2:
        return []
    
    suggestions = []
    try:
        # 1. Search in Course Names using SQL LIKE
        search_term = f"%{q}%"
        courses = await db.fetch_all("SELECT course FROM course WHERE course LIKE %s LIMIT 3", (search_term,))
        for c in courses:
            suggestions.append(f"Tell me about {c['course']}")


        # 2. Search in FAQ questions using SQL LIKE
        faqs = await db.fetch_all("SELECT question FROM faqs WHERE question LIKE %s LIMIT 5", (search_term,))
        for f in faqs:
            suggestions.append(f['question'])
            
    except Exception as e:
        print(f"Autocomplete error: {e}")
        
    # De-duplicate and limit
    return list(dict.fromkeys(suggestions))[:8]
