from typing import Optional
from rapidfuzz import process, fuzz


class ChatbotProfile:
    def __init__(self):
        self.identity_data = {
            "name": "NPGC Assistant",
            "creator": "BCA 2026 graduates of NPGC — Krishna, Pushpesh, Akshat, and Aditi",
            "purpose": "I am here to assist you with information about National Post Graduate College (NPGC), academic guidance, and general support.",
            "capabilities": [
                "Answer FAQs about NPGC admissions, courses, and facilities.",
                "Provide contact details and campus information.",
                "Assist with voice-enabled chat in multiple languages.",
                "Handle semantic search for complex college-related queries."
            ],
            "description": "I am an advanced AI assistant designed to provide accurate and real-time information to students and visitors of NPGC.",
        }

    def _is_hindi(self, language: str) -> bool:
        return "hi" in language.lower()

    def get_identity_response(self, query: str, language: str = "en-US") -> Optional[str]:
        """
        Handles direct identity-related questions from the user.
        Returns response in the detected language.
        """
        query_lower = query.lower()
        hi = self._is_hindi(language)

        # Identity
        if any(word in query_lower for word in ["who are you", "what is your name", "what are you", "introduce yourself",
                                                 "tum kaun ho", "aap kaun ho", "apna parichay", "naam kya hai"]):
            if hi:
                return f"मैं {self.identity_data['name']} हूँ। मैं NPGC (नेशनल पोस्ट ग्रेजुएट कॉलेज), लखनऊ के छात्रों और आगंतुकों को सटीक और वास्तविक समय की जानकारी प्रदान करने के लिए डिज़ाइन की गई एक एडवांस्ड AI असिस्टेंट हूँ।"
            return f"I am {self.identity_data['name']}. {self.identity_data['description']}"

        # Creator
        if any(word in query_lower for word in ["who made you", "who created you", "who is your developer",
                                                 "who built you", "kisne banaya", "developer kaun",
                                                 "kisne banaaya", "tumhe kisne banaya", "aapko kisne banaya"]):
            if hi:
                return f"मुझे NPGC के BCA 2026 बैच के छात्रों — कृष्णा, पुष्पेश, अक्षत और अदिति — ने अपने फाइनल ईयर प्रोजेक्ट के रूप में बनाया है। 🎓"
            return f"I was built by {self.identity_data['creator']} as their final year project. 🎓"

        # Capabilities
        if any(word in query_lower for word in ["what can you do", "features", "capabilities",
                                                 "what can you help with", "kya kar sakte ho",
                                                 "kya karta hai", "tumhari khasiyat"]):
            if hi:
                return (
                    "मैं निम्नलिखित कार्यों में आपकी सहायता कर सकती हूँ:\n"
                    "- NPGC प्रवेश, पाठ्यक्रम और सुविधाओं से संबंधित प्रश्नों के उत्तर देना।\n"
                    "- संपर्क विवरण और कैंपस की जानकारी प्रदान करना।\n"
                    "- कई भाषाओं में वॉइस-सक्षम चैट में सहायता करना।\n"
                    "- जटिल कॉलेज-संबंधी प्रश्नों के लिए सेमेंटिक सर्च करना।"
                )
            caps = "\n".join([f"- {c}" for c in self.identity_data['capabilities']])
            return f"I have several capabilities, including:\n{caps}"

        # Purpose
        if any(word in query_lower for word in ["purpose", "why were you made", "how can you help me",
                                                 "kyun banaya", "kisliye banaya"]):
            if hi:
                return "मैं NPGC के छात्रों और आगंतुकों को शैक्षणिक मार्गदर्शन और कॉलेज की जानकारी प्रदान करने के लिए यहाँ हूँ।"
            return self.identity_data['purpose']

        # ── Syllabus ──────────────────────────────────────────────────────────
        syllabus_keywords = ["syllabus", "curriculum", "subjects", "subject list", "topics covered",
                             "what topics", "course content", "study material", "semester subjects",
                             "syllabus chahiye", "syllabus kahan", "syllabus download"]
        if any(kw in query_lower for kw in syllabus_keywords):
            q = query_lower
            if "bca" in q:
                if hi:
                    return ("📚 **BCA का सिलेबस** यहाँ से डाउनलोड करें:\n"
                            "🔗 BCA: https://www.npgc.in/assets/Syllabus/UG-BCA.pdf\n"
                            "🔗 BCA (NEP): https://www.npgc.in/assets/Syllabus/UG-BCA_NEP.pdf\n\n"
                            "सभी कोर्स के सिलेबस के लिए: https://www.npgc.in/StudentSupport-Downloads.aspx")
                return ("📚 **BCA Syllabus** is available for direct download here:\n"
                        "🔗 BCA: https://www.npgc.in/assets/Syllabus/UG-BCA.pdf\n"
                        "🔗 BCA (NEP): https://www.npgc.in/assets/Syllabus/UG-BCA_NEP.pdf\n\n"
                        "For all other courses, visit: https://www.npgc.in/StudentSupport-Downloads.aspx")
            elif "bba" in q:
                if hi:
                    return ("📚 **BBA का सिलेबस** यहाँ से डाउनलोड करें:\n"
                            "🔗 https://www.npgc.in/assets/Syllabus/UG-BBA.pdf\n\n"
                            "सभी कोर्स के लिए: https://www.npgc.in/StudentSupport-Downloads.aspx")
                return ("📚 **BBA Syllabus** is available for direct download here:\n"
                        "🔗 https://www.npgc.in/assets/Syllabus/UG-BBA.pdf\n\n"
                        "For all other courses, visit: https://www.npgc.in/StudentSupport-Downloads.aspx")
            elif "b.com" in q or "bcom" in q or "commerce" in q:
                if hi:
                    return ("📚 **B.Com का सिलेबस** यहाँ से डाउनलोड करें:\n"
                            "🔗 https://www.npgc.in/assets/Syllabus/UG-BCom.pdf\n\n"
                            "सभी कोर्स के लिए: https://www.npgc.in/StudentSupport-Downloads.aspx")
                return ("📚 **B.Com Syllabus** is available for direct download here:\n"
                        "🔗 https://www.npgc.in/assets/Syllabus/UG-BCom.pdf\n\n"
                        "For all other courses, visit: https://www.npgc.in/StudentSupport-Downloads.aspx")
            elif "b.sc" in q or "bsc" in q or "computer science" in q:
                if hi:
                    return ("📚 **B.Sc (Computer Science) का सिलेबस** यहाँ से डाउनलोड करें:\n"
                            "🔗 https://www.npgc.in/assets/Syllabus/UG-ComputerScience.pdf\n\n"
                            "सभी कोर्स के लिए: https://www.npgc.in/StudentSupport-Downloads.aspx")
                return ("📚 **B.Sc (Computer Science) Syllabus** is available for direct download here:\n"
                        "🔗 https://www.npgc.in/assets/Syllabus/UG-ComputerScience.pdf\n\n"
                        "For all other courses, visit: https://www.npgc.in/StudentSupport-Downloads.aspx")
            else:
                if hi:
                    return ("📚 सभी कोर्स का सेमेस्टर-वार सिलेबस NPGC डाउनलोड पेज से प्राप्त करें:\n"
                            "🔗 https://www.npgc.in/StudentSupport-Downloads.aspx\n\n"
                            "सीधे PDF लिंक:\n"
                            "• BCA: https://www.npgc.in/assets/Syllabus/UG-BCA.pdf\n"
                            "• BCA (NEP): https://www.npgc.in/assets/Syllabus/UG-BCA_NEP.pdf\n"
                            "• BBA: https://www.npgc.in/assets/Syllabus/UG-BBA.pdf\n"
                            "• B.Com: https://www.npgc.in/assets/Syllabus/UG-BCom.pdf\n"
                            "• B.Sc (CS): https://www.npgc.in/assets/Syllabus/UG-ComputerScience.pdf\n"
                            "• B.Voc (SD): https://www.npgc.in/assets/Syllabus/UG-BVocSD.pdf")
                return ("📚 You can download the semester-wise syllabus for all courses from the NPGC Downloads page:\n"
                        "🔗 https://www.npgc.in/StudentSupport-Downloads.aspx\n\n"
                        "Direct PDF links:\n"
                        "• BCA: https://www.npgc.in/assets/Syllabus/UG-BCA.pdf\n"
                        "• BCA (NEP): https://www.npgc.in/assets/Syllabus/UG-BCA_NEP.pdf\n"
                        "• BBA: https://www.npgc.in/assets/Syllabus/UG-BBA.pdf\n"
                        "• B.Com: https://www.npgc.in/assets/Syllabus/UG-BCom.pdf\n"
                        "• B.Sc (CS): https://www.npgc.in/assets/Syllabus/UG-ComputerScience.pdf\n"
                        "• B.Voc (SD): https://www.npgc.in/assets/Syllabus/UG-BVocSD.pdf")

        # ── PG Course Groups ──────────────────────────────────────────────────
        pg_courses_keywords = ["pg course", "postgraduate", "master", "ma ", "msc", "m.com", "mcom", "m.voc", "mvoc", "mph ", "public health", "post graduate courses", "स्नातकोत्तर", "pg "]
        
        # If user asks about PG courses (broadly)
        if any(kw in query_lower for kw in pg_courses_keywords):
            # Check for information intent keywords
            info_keywords = ["available", "list", "offer", "which", "kya", "batao", "kaun", "bataiye", "courses", "group"]
            if any(kw in query_lower for kw in info_keywords) or len(query_lower.split()) <= 3:
                if hi:
                    return (
                        "🎓 **NPGC में स्नातकोत्तर (PG) पाठ्यक्रम:**\n\n"
                        "**1. मास्टर ऑफ आर्ट्स (M.A.):**\n"
                        "   • अर्थशास्त्र, अंग्रेज़ी, भूगोल, राजनीति विज्ञान, मनोविज्ञान, नृविज्ञान।\n\n"
                        "**2. मास्टर ऑफ साइंस (M.Sc.):**\n"
                        "   • भौतिक विज्ञान, रसायन विज्ञान, जंतु विज्ञान, वनस्पति विज्ञान, नृविज्ञान।\n\n"
                        "**3. मास्टर ऑफ कॉमर्स (M.Com):**\n"
                        "   • वाणिज्य में विशेषज्ञता।\n\n"
                    "**4. मास्टर ऑफ वोकेशन (M.Voc):**\n"
                    "   • बैंकिंग और बीमा, सॉफ्टवेयर और ई-गवर्नेंस।\n\n"
                    "**5. मास्टर ऑफ पब्लिक हेल्थ (MPH):**\n"
                    "   • लोक स्वास्थ्य प्रबंधन।\n\n"
                    "📝 **योग्यता:** संबंधित विषय में स्नातक (न्यूनतम 45-50% अंक)।\n"
                    "🌐 अधिक जानकारी: https://www.npgc.in/Academics-CoursesPG.aspx"
                )
            return (
                "🎓 **Postgraduate (PG) Courses at NPGC:**\n\n"
                "**1. Master of Arts (M.A.):**\n"
                "   • Economics, English, Geography, Political Science, Psychology, Anthropology.\n\n"
                "**2. Master of Science (M.Sc.):**\n"
                "   • Physics, Chemistry, Zoology, Botany, Anthropology.\n\n"
                "**3. Master of Commerce (M.Com):**\n"
                "   • Specialization in Commerce.\n\n"
                "**4. Master of Vocational Studies (M.Voc):**\n"
                "   • Banking & Insurance, Software & E-Governance.\n\n"
                "**5. Master of Public Health (MPH):**\n"
                "   • Public Health Management.\n\n"
                "📝 **Eligibility:** Bachelor's degree in a relevant stream with 45-50% aggregate marks.\n"
                "🌐 More info: https://www.npgc.in/Academics-CoursesPG.aspx"
            )

        # ── B.Sc Subject Groups ───────────────────────────────────────────────
        bsc_keywords = ["b.sc subjects", "bsc subjects", "b.sc courses", "what subjects in b.sc",
                        "b.sc maths", "b.sc biology", "b.sc science", "bachelor of science subjects",
                        "science subjects", "b.sc groups", "bsc group"]
        if any(kw in query_lower for kw in bsc_keywords) or \
           (any(k in query_lower for k in ["b.sc", "bsc", "bachelor of science"]) and
            any(k in query_lower for k in ["subject", "group", "option", "combination", "offer", "available", "which",
                                            "kya", "kaun", "batao", "bataiye"])):
            if hi:
                return (
                    "🔬 **NPGC में B.Sc** दो ग्रुप में उपलब्ध है:\n\n"
                    "**जीव विज्ञान ग्रुप** (120 स्व-वित्त सीटें):\n"
                    "  • जंतु विज्ञान (Zoology)\n"
                    "  • वनस्पति विज्ञान (Botany)\n"
                    "  • रसायन विज्ञान (Chemistry)\n\n"
                    "**गणित ग्रुप** (240 स्व-वित्त सीटें):\n"
                    "  • भौतिक विज्ञान (Physics)\n"
                    "  • रसायन विज्ञान (Chemistry)\n"
                    "  • गणित (Mathematics)\n"
                    "  • सांख्यिकी (Statistics)\n"
                    "  • कंप्यूटर विज्ञान (Computer Science)\n\n"
                    "📋 पूर्ण सिलेबस: https://www.npgc.in/StudentSupport-Downloads.aspx\n"
                    "🌐 अधिक जानकारी: https://www.npgc.in/Academics-CoursesUG.aspx"
                )
            return (
                "🔬 **B.Sc programs at NPGC** are offered in two groups:\n\n"
                "**Biology Group** (120 Self-Finance seats):\n"
                "  • Zoology\n"
                "  • Botany\n"
                "  • Chemistry\n\n"
                "**Mathematics Group** (240 Self-Finance seats):\n"
                "  • Physics\n"
                "  • Chemistry\n"
                "  • Mathematics\n"
                "  • Statistics\n"
                "  • Computer Science\n\n"
                "📋 For the full syllabus: https://www.npgc.in/StudentSupport-Downloads.aspx\n"
                "🌐 More info: https://www.npgc.in/Academics-CoursesUG.aspx"
            )

        # ── B.A Subject Options ───────────────────────────────────────────────
        ba_keywords = ["b.a subjects", "ba subjects", "b.a courses", "what subjects in b.a",
                       "arts subjects", "bachelor of arts subjects", "ba options", "b.a options",
                       "arts options", "which subjects in arts"]
        if any(kw in query_lower for kw in ba_keywords) or \
           (any(k in query_lower for k in ["b.a", " ba ", "bachelor of arts"]) and
            any(k in query_lower for k in ["subject", "option", "offer", "available", "which",
                                            "kya", "kaun", "batao", "bataiye"])):
            if hi:
                return (
                    "🎓 **NPGC में B.A (बैचलर ऑफ आर्ट्स)** में निम्नलिखित विषय उपलब्ध हैं:\n\n"
                    "**उपलब्ध विषय:**\n"
                    "  • नृविज्ञान (Anthropology)\n"
                    "  • अर्थशास्त्र (Economics)\n"
                    "  • शिक्षा (Education)\n"
                    "  • अंग्रेज़ी (English)\n"
                    "  • भूगोल (Geography)\n"
                    "  • हिंदी (Hindi)\n"
                    "  • इतिहास — प्राचीन, मध्यकालीन व आधुनिक भारतीय, पश्चिमी (History)\n"
                    "  • राजनीति विज्ञान (Political Science)\n"
                    "  • मनोविज्ञान (Psychology)\n"
                    "  • शारीरिक शिक्षा (Physical Education)\n"
                    "  • संस्कृत (Sanskrit)\n"
                    "  • समाजशास्त्र (Sociology)\n\n"
                    "**विशेष कार्यक्रम:**\n"
                    "  • B.A.J.M.C. — पत्रकारिता एवं जनसंचार (60 स्व-वित्त सीटें)\n\n"
                    "📋 सिलेबस: https://www.npgc.in/StudentSupport-Downloads.aspx\n"
                    "🌐 अधिक जानकारी: https://www.npgc.in/Academics-CoursesUG.aspx"
                )
            return (
                "🎓 **B.A (Bachelor of Arts) at NPGC** offers a wide range of subjects:\n\n"
                "**Available Subjects:**\n"
                "  • Anthropology\n"
                "  • Economics\n"
                "  • Education\n"
                "  • English\n"
                "  • Geography\n"
                "  • Hindi\n"
                "  • History (Ancient Indian, Medieval & Modern Indian, Western)\n"
                "  • Political Science\n"
                "  • Psychology\n"
                "  • Physical Education\n"
                "  • Sanskrit\n"
                "  • Sociology\n\n"
                "**Specialized Program:**\n"
                "  • B.A.J.M.C. — Journalism & Mass Communication (60 Self-Finance seats)\n\n"
                "📋 For the full syllabus: https://www.npgc.in/StudentSupport-Downloads.aspx\n"
                "🌐 More info: https://www.npgc.in/Academics-CoursesUG.aspx"
            )

        # ── B.Voc Programs ────────────────────────────────────────────────────
        bvoc_keywords = ["b.voc", "bvoc", "vocational", "vocational courses", "b.voc programs",
                         "vocational programs", "ddukk", "kaushal kendra", "b voc"]
        if any(kw in query_lower for kw in bvoc_keywords):
            if hi:
                return (
                    "🛠️ **NPGC में B.Voc (बैचलर ऑफ वोकेशन)** कौशल-आधारित डिग्री कोर्स हैं,\n"
                    "जो दीन दयाल उपाध्याय कौशल केंद्र (DDUKK) के अंतर्गत संचालित हैं:\n\n"
                    "**उपलब्ध कार्यक्रम:**\n"
                    "  • B.Voc — बैंकिंग एवं वित्त (Banking & Finance)\n"
                    "  • B.Voc — अस्पताल प्रबंधन (Hospital Management)\n"
                    "  • B.Voc — होटल प्रबंधन (Hotel Management)\n"
                    "  • B.Voc — मेडिकल लैब टेक्नोलॉजी (Medical Lab Technology)\n"
                    "  • B.Voc — ऑपरेशन थिएटर टेक्नोलॉजी (Operation Theatre Technology)\n"
                    "  • B.Voc — फिजियोथेरेपी (Physiotherapy)\n"
                    "  • B.Voc — सॉफ्टवेयर डेवलपमेंट एवं ई-गवर्नेंस (Software Development & E-Governance)\n\n"
                    "ये कार्यक्रम सर्टिफिकेट, डिप्लोमा और डिग्री स्तर पर निकास विकल्पों के साथ उपलब्ध हैं।\n\n"
                    "🌐 अधिक जानकारी: https://www.npgc.in/Academics-CVFS.aspx\n"
                    "📋 सिलेबस: https://www.npgc.in/assets/Syllabus/UG-BVocSD.pdf"
                )
            return (
                "🛠️ **B.Voc (Bachelor of Vocation) programs at NPGC** are industry-aligned degree courses\n"
                "offered under the Deen Dayal Upadhyay Kaushal Kendra (DDUKK):\n\n"
                "**Available Programs:**\n"
                "  • B.Voc — Banking & Finance\n"
                "  • B.Voc — Hospital Management\n"
                "  • B.Voc — Hotel Management\n"
                "  • B.Voc — Medical Lab Technology\n"
                "  • B.Voc — Operation Theatre Technology\n"
                "  • B.Voc — Physiotherapy\n"
                "  • B.Voc — Software Development & E-Governance\n\n"
                "These programs provide skill-based education with exit options at Certificate,\n"
                "Diploma, and Degree levels.\n\n"
                "🌐 More info: https://www.npgc.in/Academics-CVFS.aspx\n"
                "📋 Syllabus: https://www.npgc.in/assets/Syllabus/UG-BVocSD.pdf"
            )

        # ── PG Diploma & Certificate Courses ──────────────────────────────────
        pg_keywords = ["pgdrs", "gis", "remote sensing", "post graduate diploma", "pg diploma", "certificate course", "specialized course"]
        if any(kw in query_lower for kw in pg_keywords):
            if hi:
                return (
                    "🎓 **NPGC में PG डिप्लोमा और सर्टिफिकेट कोर्स:**\n\n"
                    "**PGDRS & GIS (रिमोट सेंसिंग और जीआईएस):**\n"
                    "  • **अवधि:** 1 वर्ष (पूर्णकालिक)\n"
                    "  • **योग्यता:** स्नातक (Graduation) — विज्ञान, भूगोल, वाणिज्य, या इंजीनियरिंग (न्यूनतम 45-50%)\n"
                    "  • **सुविधाएँ:** आधुनिक GIS लैब (ArcGIS/QGIS), सैटेलाइट डेटा और फील्ड ट्रेनिंग।\n"
                    "  • **करियर:** GIS एनालिस्ट, कार्टोग्राफर, अर्बन प्लानर।\n\n"
                    "**अन्य सर्टिफिकेट कोर्स (6 महीने):**\n"
                    "  • कंप्यूटर साइंस (Computer Science)\n"
                    "  • फॉरेंसिक साइंस (Forensic Science)\n"
                    "  • मनोवैज्ञानिक परामर्श (Psychological Counseling)\n"
                    "  • रोबोटिक्स और AI (Robotics & AI)\n\n"
                    "🌐 अधिक जानकारी: https://www.npgc.in"
                )
            return (
                "🎓 **PG Diploma & Certificate Courses at NPGC:**\n\n"
                "**PGDRS & GIS (Remote Sensing & GIS):**\n"
                "  • **Duration:** 1 Year (Full-time)\n"
                "  • **Eligibility:** Graduate in any discipline (Science, Arts with Geography, Commerce, or B.Tech) with 45-50% marks.\n"
                "  • **Facilities:** Specialized GIS lab (ArcGIS/QGIS), satellite imagery access, and field GPS training.\n"
                "  • **Career:** GIS Analyst, Geospatial Scientist, Urban Planner, Cartographer.\n\n"
                "**Other Certificate Courses (6 Months):**\n"
                "  • Computer Science\n"
                "  • Forensic Science\n"
                "  • Psychological Counseling\n"
                "  • Robotics and Artificial Intelligence\n\n"
                "🌐 More info: https://www.npgc.in"
            )

        # ── Scholarship Info ──────────────────────────────────────────────────
        scholarship_keywords = ["scholarship", "financial aid", "stipend", "छात्रवृत्ति", "scholarship kab aayegi"]
        if any(kw in query_lower for kw in scholarship_keywords):
            if hi:
                return (
                    "💰 **NPGC में छात्रवृत्ति (Scholarship) के अवसर:**\n\n"
                    "1. **सरकारी छात्रवृत्ति:** कॉलेज यूपी राज्य सरकार (SC/ST/OBC/EWS) और राष्ट्रीय छात्रवृत्ति पोर्टल (NSP) योजनाओं में सहायता करता है।\n"
                    "2. **कॉलेज विशिष्ट छात्रवृत्ति:**\n"
                    "   • **अमित सिंह चौहान मेमोरियल:** B.Com के मेधावी छात्रों के लिए।\n"
                    "   • **राम दुलारी जी.पी. दीक्षित मेमोरियल:** B.A. (भूगोल) के छात्रों के लिए।\n"
                    "   • **मेधा छात्रवृत्ति:** स्व-वित्तपोषित पाठ्यक्रमों के टॉपर्स के लिए।\n\n"
                    "📝 **आवेदन प्रक्रिया:** सरकारी पोर्टल (UP Scholarship/NSP) पर ऑनलाइन आवेदन करें और फॉर्म कॉलेज कार्यालय में सत्यापित (verify) कराएं।\n"
                    "🌐 अधिक जानकारी के लिए: https://www.npgc.in"
                )
            return (
                "💰 **Scholarship Opportunities at NPGC:**\n\n"
                "1. **Government Scholarships:** The college facilitates UP State (SC/ST/OBC/EWS) and National Scholarship Portal (NSP) schemes.\n"
                "2. **College-Specific Awards:**\n"
                "   • **Amit Singh Chauhan Memorial:** For meritorious B.Com students.\n"
                "   • **Ram Dulari G.P. Dixit Memorial:** For B.A. (Geography) students.\n"
                "   • **Merit Scholarships:** For top performers in self-financed courses.\n\n"
                "📝 **How to Apply:** Apply online via government portals (UP Scholarship/NSP) and submit the hard copy to the college office for verification.\n"
                "🌐 Website: https://www.npgc.in"
            )

        # ── Faculty & Staff ───────────────────────────────────────────────────
        faculty_keywords = ["faculty", "hod", "teacher", "professor", "principal", "staff", "head of dept", "head of department"]
        if any(kw in query_lower for kw in faculty_keywords):
            if hi:
                return (
                    "🏛️ **NPGC संकाय और प्रशासन (Faculty & Staff):**\n\n"
                    "**नेतृत्व (Leadership):**\n"
                    "• **प्राचार्य (Principal):** प्रो. देवेंद्र कुमार सिंह\n\n"
                    "**विभागाध्यक्ष (HODs):**\n"
                    "• **BCA/Software Dev:** श्री राघवेंद्र कुशवाहा\n"
                    "• **BBA/Management:** डॉ. श्वेता सिंह\n"
                    "• **Commerce:** डॉ. ज्योति भार्गवा\n"
                    "• **Science (Physics):** डॉ. अर्चना सिंह\n\n"
                    "🔗 **पूरा संकाय विवरण यहाँ देखें:**\n"
                    "https://www.npgc.in/Academics-Department.aspx\n\n"
                    "आप विशिष्ट विभाग के शिक्षकों के बारे में भी पूछ सकते हैं!"
                )
            return (
                "🏛️ **NPGC Faculty & Administration:**\n\n"
                "**Senior Leadership:**\n"
                "• **Principal:** Prof. Devendra Kumar Singh\n\n"
                "**Heads of Departments (HODs):**\n"
                "• **BCA / Software Dev:** Mr. Raghvendra Kushwaha\n"
                "• **BBA / Management:** Dr. Shweta Singh\n"
                "• **Commerce:** Dr. Jyoti Bhargava\n"
                "• **Science (Physics):** Dr. Archana Singh\n\n"
                "🔗 **Official Faculty Directory:**\n"
                "https://www.npgc.in/Academics-Department.aspx\n\n"
                "Feel free to ask about specific departmental teachers!"
            )

        # ── Greetings & Acknowledgments ───────────────────────────────────────
        greetings = ["hi", "hello", "hey", "greetings", "namaste", "pranam", "hola",
                     "ok", "thanks", "thank you", "cool", "nice", "bye", "shukriya",
                     "dhanyavaad", "theek hai", "accha", "acha"]

        # Use a stricter check for very short queries to avoid false positives
        q_strip = query_lower.strip('?.! ')
        if q_strip in greetings or (len(q_strip) < 10 and any(g in q_strip for g in greetings)):
            match = process.extractOne(q_strip, greetings, scorer=fuzz.WRatio)
            if match and match[1] >= 85:
                if hi:
                    return f"नमस्ते! मैं {self.identity_data['name']} हूँ। NPGC के बारे में मैं आपकी किस प्रकार सहायता कर सकती हूँ?"
                return f"Hello! I am {self.identity_data['name']}. How can I assist you with NPGC today?"

        return None


# Global singleton
chatbot_profile = ChatbotProfile()
