import os
import httpx
import asyncio
import numpy as np
import json
from typing import Optional, List, Dict, Any
from services.database import db
from services.faq import faq_service

class KnowledgeService:
    def __init__(self, threshold: float = 0.65):
        self.threshold = threshold
        self.intent_entries = []
        self.intent_embeddings = None

    async def sync_intents(self):
        """Fetch intents and their embeddings from MySQL."""
        if not db.pool: return

        try:
            self.intent_entries = await db.fetch_all("SELECT * FROM chatbotknowledge")
            
            if self.intent_entries:
                processed_entries = []
                embeddings = []
                for entry in self.intent_entries:
                    # MySQL returns JSON fields as dicts or strings depending on driver config
                    vec = entry.get("Vector")
                    if isinstance(vec, str):
                        vec = json.loads(vec)
                    
                    if vec:
                        entry["Vector"] = vec # Ensure it's a list for internal use
                        processed_entries.append(entry)
                        embeddings.append(vec)
                
                self.intent_entries = processed_entries
                
                if embeddings:
                    self.intent_embeddings = np.array(embeddings, dtype=np.float64)
                    # Normalize
                    norm = np.linalg.norm(self.intent_embeddings, axis=1, keepdims=True)
                    self.intent_embeddings = np.divide(
                        self.intent_embeddings, 
                        norm, 
                        out=np.zeros_like(self.intent_embeddings, dtype=np.float64), 
                        where=norm!=0
                    )

            print(f"Synced {len(self.intent_entries)} Knowledge Intents from MySQL.")
        except Exception as e:
            print(f"Error syncing intents from MySQL: {e}")

    async def get_intent_data(self, query: str) -> Optional[Dict[str, Any]]:
        """Detects intent and fetches relevant academic data."""
        if not db.pool: return None
        if not self.intent_entries: await self.sync_intents()
        if not self.intent_entries or self.intent_embeddings is None: return None

        try:
            query_vec = await faq_service.get_embedding(query, task_type="RETRIEVAL_QUERY")
            norm = np.linalg.norm(query_vec)
            if norm > 0:
                query_vec = query_vec / norm
            else:
                return None
        except Exception as e:
            print(f"Knowledge embedding failed: {e}")
            return None

        if self.intent_embeddings.shape[1] != query_vec.shape[0]:
            print(f"Knowledge Vector Skip: DB({self.intent_embeddings.shape[1]}) != Live({query_vec.shape[0]})")
            return None

        similarities = np.dot(self.intent_embeddings, query_vec.T).flatten()
        best_idx = np.argmax(similarities)
        
        intent_type = self.intent_entries[best_idx]["Intent"]
        score = similarities[best_idx]

        if score >= self.threshold:
            intent_doc = self.intent_entries[best_idx]
            fixed_en = intent_doc.get("FixedResponseEn")
            fixed_hi = intent_doc.get("FixedResponseHi")
            
            # Check for deterministic rules first
            if fixed_en or fixed_hi:
                return {
                    "intent": intent_type,
                    "fixed_response_en": fixed_en,
                    "fixed_response_hi": fixed_hi,
                    "context_string": fixed_en or ""
                }

            if intent_type == "ADMISSION_DEADLINE":
                data = await self._fetch_course_data(query)
                if data: return {"intent": intent_type, "context_string": self._format_deadline_context(data)}

            elif intent_type in ["FACULTY_BY_DEPT", "FACULTY_BY_NAME"]:
                data = await self._fetch_faculty_data(query)
                if data: return {"intent": intent_type, "context_string": self._format_faculty_context(data)}
            
            elif intent_type == "COURSE_INFO":
                data = await self._fetch_course_data(query)
                if data: return {"intent": intent_type, "context_string": self._format_course_context(data)}

        return None

    async def get_intent_data_by_intent(self, intent_type: str, query: str) -> Optional[Dict[str, Any]]:
        """Directly fetches data for a specific intent without vector search."""
        if not db.pool: return None
        if not self.intent_entries: await self.sync_intents()

        intent_doc = next((e for e in self.intent_entries if e["Intent"] == intent_type), None)
        if not intent_doc: return None

        fixed_en = intent_doc.get("FixedResponseEn")
        fixed_hi = intent_doc.get("FixedResponseHi")
        
        if fixed_en or fixed_hi:
            return {
                "intent": intent_type,
                "fixed_response_en": fixed_en,
                "fixed_response_hi": fixed_hi,
                "context_string": fixed_en or ""
            }

        data = None
        context_string = ""
        if intent_type == "COURSE_INFO":
            data = await self._fetch_course_data(query)
            context_string = self._format_course_context(data) if data else ""
        elif intent_type == "ADMISSION_DEADLINE":
            data = await self._fetch_course_data(query)
            context_string = self._format_deadline_context(data) if data else ""
        elif intent_type in ["FACULTY_BY_DEPT", "FACULTY_BY_NAME"]:
            data = await self._fetch_faculty_data(query)
            context_string = self._format_faculty_context(data) if data else ""
        elif intent_type == "ALUMNI_INFO":
            data = await self._fetch_alumni_data(query)
            context_string = self._format_alumni_context(data) if data else ""
        elif intent_type in ["LIBRARY_INFRA", "HOSTEL_INFO", "EVENTS_INFO", "CAMPUS_GENERAL", "ADMISSION_PROCEDURE"]:
            # Route to FAQs table for rich text answers
            faq_keywords = {
                "LIBRARY_INFRA": "library",
                "HOSTEL_INFO": "hostel",
                "EVENTS_INFO": "Events By Department",
                "CAMPUS_GENERAL": "placement",
                "ADMISSION_PROCEDURE": "admission process",
            }
            kw = faq_keywords.get(intent_type, "")
            if kw:
                row = await db.fetch_one("SELECT answer FROM faqs WHERE LOWER(question) LIKE %s LIMIT 1", (f"%{kw.lower()}%",))
                if row and row['answer']:
                    context_string = row['answer']
        elif intent_type in ["COLLEGE_CONTACT", "COLLEGE_ADDRESS"]:
            row = await db.fetch_one("SELECT answer FROM faqs WHERE LOWER(question) LIKE %s LIMIT 1", ("%contact%",))
            if row and row['answer']:
                context_string = row['answer']
            else:
                context_string = "Contact NPGC at: Phone: 0522 4021304 | Email: support@npgc.in | Address: 2, Rana Pratap Marg, Lucknow - 226001."

        if context_string:
            return {
                "intent": intent_type,
                "data": data,
                "context_string": context_string
            }
        return None


    async def _fetch_course_data(self, query: str) -> List[Dict]:
        """Fetch course information - specific course if mentioned, else all."""
        all_courses = await db.fetch_all("SELECT * FROM course WHERE isOffered = 1")
        q = query.lower()

        # Comprehensive alias map: keyword -> partial course name to match in DB
        alias_map = [
            # UG Courses
            (["bca", "computer applications", "bachelor of computer"],           "Bachelor of Computer Applications"),
            (["bba ms", "bba management", "business administration ms"],          "Bachelor of Business Administration MS"),
            (["bba digital", "digital business", "bba db"],                       "Bachelor of Business Administration in Digital Business"),
            (["bba"],                                                              "Bachelor of Business Administration"),
            (["b.com ecommerce", "bcom ecommerce", "commerce ecommerce"],         "Bachelor of Commerce Ecommerce"),
            (["b.com hons", "bcom hons", "b.com honours", "commerce honors"],     "Bachelor of Commerce Honors"),
            (["b.com", "bcom", "bachelor of commerce"],                           "Bachelor of Commerce"),
            (["b.sc", "bsc", "bachelor of science"],                              "Bachelor of Science"),
            (["b.a", "ba arts", "bachelor of arts"],                              "Bachelor of Arts"),
            (["bjmc", "journalism", "mass communication"],                        "Bachelor of Journalism"),
            (["bph", "public health", "bachelor of public health"],               "Bachelor of Public Health"),
            (["b.voc software", "bvoc software", "vocation software", "software development", "e-governance"],  "Bachelor of Vocation Software"),
            (["b.voc banking", "bvoc banking", "vocation banking", "banking finance"],                         "Bachelor of Vocation Banking"),
            (["b.voc hospital", "bvoc hospital", "hospital management"],                                       "Bachelor of Vocation Hospital"),
            (["b.voc hotel", "bvoc hotel", "hotel management"],                                                "Bachelor of Vocation Hotel"),
            (["b.voc medical", "bvoc medical", "medical lab", "mlt"],                                          "Bachelor of Vocation Medical"),
            (["b.voc operation", "bvoc operation", "operation theatre", "ott"],                                 "Bachelor of Vocation Operation"),
            (["b.voc physio", "bvoc physio", "physiotherapy"],                                                 "Bachelor of Vocation Physiotherapy"),
            (["b.voc", "bvoc", "bachelor of vocation"],                                                        "Bachelor of Vocation"),
            (["b.sc biology", "bsc biology", "zoology", "botany", "biology group"],                           "Bachelor of Science Biology"),
            (["b.sc maths", "bsc maths", "b.sc mathematics", "physics", "statistics", "maths group"],          "Bachelor of Science Maths"),
            # PG Courses
            (["m.com", "mcom", "master of commerce"],                             "Master of Commerce"),
            (["m.sc chemistry", "msc chemistry"],                                 "Master of Science (M.Sc.) in Chemistry"),
            (["m.sc geo", "msc geoinformatics", "geoinformatics"],                "Master of Science (M.Sc.) in Geoinformatics"),
            (["m.a economics", "ma economics"],                                   "Master of Arts (M.A.) in Economics"),
            (["m.a english", "ma english"],                                       "Master of Arts (M.A.) in English"),
            (["m.a geography", "ma geography"],                                   "Master of Arts (M.A.) in Geography"),
            (["m.a political", "ma political", "political science"],              "Master of Arts (M.A.) in Political Science"),
            (["m.a psychology", "ma psychology"],                                 "Master of Arts (M.A.) in Psychology"),
            (["m.a anthropology", "ma anthropology", "anthropology"],             "Master of Arts/Science (M.A./M.Sc.) in Anthropology"),
            (["m.ph", "mph", "master of public health"],                          "Master of Public Health"),
            (["m.voc software", "mvoc software"],                                 "Master of Vocation (M.Voc.) in Software"),
            (["m.voc banking", "mvoc banking"],                                   "Master of Vocation (M.Voc.) in Banking"),
            # Diploma / Certificate
            (["adatia", "analytical techniques"],                                 "Advanced Diploma in Analytical Techniques"),
            (["adda", "data analytics"],                                          "Advanced Diploma in Data Analytics"),
            (["dbf", "diploma banking"],                                          "Diploma in Banking and Finance"),
            (["doaeg", "office automation", "e-governance"],                      "Diploma in Office Automation"),
            (["pgdrm", "retail management"],                                      "Post Graduate Diploma in Retail Management"),
            (["pgdrs", "remote sensing", "gis"],                                  "Post Graduate Diploma in Remote Sensing"),
            (["ccbta", "blockchain"],                                             "Certificate Course in Blockchain"),
            (["cccs", "certificate computer science"],                            "Certificate Course in Computer Science"),
            (["ccece", "communication english"],                                  "Certificate Course in Effective Communication"),
            (["ccfs", "forensic science"],                                        "Certificate Course in Forensic Science"),
            (["ccpc", "psychological counseling"],                                "Certificate Course in Psychological Counseling"),
            (["ccrai", "ccr ai", "robotics", "artificial intelligence"],          "Certificate Course in Robotics"),
        ]

        # Find the best matching alias
        for keywords, course_name_fragment in alias_map:
            if any(kw in q for kw in keywords):
                matches = [c for c in all_courses if course_name_fragment.lower() in c['course'].lower()]
                if matches:
                    return matches

        # No specific course identified — return all courses (overview mode)
        return all_courses


    async def _fetch_faculty_data(self, query: str) -> List[Dict]:
        """Fetch faculty data from MySQL."""
        all_faculty = await db.fetch_all("SELECT * FROM faculty")
        q_low = query.lower()
        matches = [f for f in all_faculty if f['name'].lower() in q_low]
                
        if not matches:
            dept_keywords = {
                # Computer / BCA
                "computer": [1, 29], "bca": [1, 29],
                # Commerce (B.Com + M.Com)
                "commerce": [2], "b.com": [2], "bcom": [2],
                "m.com": [2], "mcom": [2], "master of commerce": [2],
                # Management / BBA
                "management": [26], "bba": [26],
                # Economics
                "economics": [11],
                # Psychology
                "psychology": [18],
                # Science / B.Sc groups
                "science": [1, 20, 21, 22, 23, 24, 25],
                "physics": [20], "chemistry": [21], "mathematics": [22],
                "statistics": [23], "zoology": [24], "botany": [25],
                # Arts / B.A subjects
                "arts": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                "b.a": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13],
                "english": [3], "hindi": [4], "history": [5],
                "political": [6], "sociology": [7], "geography": [8],
                "anthropology": [9], "education": [10],
                "sanskrit": [12], "physical education": [13],
                # Journalism
                "journalism": [14], "bjmc": [14],
            }
            target_depts = []
            for kw, ids in dept_keywords.items():
                if kw in q_low: target_depts.extend(ids)
            if target_depts:
                matches = [f for f in all_faculty if f.get('deptId') in target_depts]
        
        return matches[:12]

    async def _fetch_alumni_data(self, query: str) -> List[Dict]:
        """Fetch alumni from MySQL."""
        if not db.pool: return []
        try:
            all_alumni = await db.fetch_all("SELECT * FROM alumni")
            if not all_alumni: return []
            q_low = query.lower()
            matches = [a for a in all_alumni if a.get('course', '').lower() in q_low or a.get('batch', '') in q_low or any(p.lower() in q_low for p in a.get('name', '').split())]
            return matches or all_alumni[:15]
        except Exception as e:
            print(f"Alumni Fetch Error: {e}")
            return []


    def _format_course_context(self, data: List[Dict]) -> str:
        if not data: return ""
        if len(data) == 1:
            # Single course — show full detail
            c = data[0]
            dur = f"{c.get('duration', 'N/A')} year(s)" if c.get('duration') else "N/A"
            return (
                f"Course: {c.get('course', 'N/A')}\n"
                f"Duration: {dur}\n"
                f"Seats: {c.get('seats', 'N/A')}\n"
                f"Eligibility: {c.get('eligibility', 'N/A')}\n"
                f"Admission Deadline: {c.get('admissionDeadline', 'N/A')}"
            )
        # Multiple courses — compact list
        ctx = f"Course overview ({len(data)} courses):\n"
        for item in data[:10]:
            ctx += f"- {item.get('course','Course')}: {item.get('duration','N/A')} yr(s), {item.get('seats','N/A')} seats. Eligibility: {item.get('eligibility','N/A')}\n"
        return ctx


    def _format_faculty_context(self, data: List[Dict]) -> str:
        if not data: return ""
        ctx = "Faculty members (top matches):\n"
        for item in data[:6]:
            ctx += f"- {item.get('name', 'Faculty')} ({item.get('designation', 'Faculty')})\n"
        return ctx

    def _format_deadline_context(self, data: List[Dict]) -> str:
        if not data: return ""
        ctx = "Key Deadlines:\n"
        for item in data[:5]: ctx += f"- {item.get('course', 'Course')}: {item.get('admissionDeadline', 'N/A')}.\n"
        return ctx

    def _format_alumni_context(self, data: List[Dict]) -> str:
        if not data: return ""
        ctx = "Notable Alumni (top 3):\n"
        for item in data[:3]: ctx += f"- {item.get('name', 'Alumnus')} ({item.get('course', 'N/A')}, {item.get('batch', 'N/A')})\n"
        return ctx

knowledge_service = KnowledgeService()
