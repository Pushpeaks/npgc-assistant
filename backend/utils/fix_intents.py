import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import certifi
from dotenv import load_dotenv

load_dotenv()

async def fix():
    client = AsyncIOMotorClient(os.getenv("MONGO_URI"), tlsCAFile=certifi.where())
    db = client[os.getenv("DATABASE_NAME")]
    
    # Add Fixed Responses for high-frequency intents to bypass AI
    await db.chatbotknowledge.update_one(
        {"Intent": "COURSE_INFO"},
        {"$set": {
            "FixedResponseEn": "NPGC offers various UG and PG courses including B.A., B.Com, B.Sc, BBA, BCA, and M.A., M.Com, M.Sc. You can find detailed seat and eligibility info in our courses section.",
            "FixedResponseHi": "NPGC विभिन्न स्नातक और स्नातकोत्तर पाठ्यक्रम प्रदान करता है जैसे बीए, बीकॉम, बीएससी, बीबीए, बीसीए, और एमए, एमकॉम, एमएससी।"
        }}
    )
    
    await db.chatbotknowledge.update_one(
        {"Intent": "ADMISSION_DEADLINE"},
        {"$set": {
            "FixedResponseEn": "The last date to apply for UG courses (B.A., B.Sc., B.Com) is 31 May 2026. For professional courses (BCA, BBA, B.Com-Hons), it is also 31 May 2026.",
            "FixedResponseHi": "यूजी पाठ्यक्रमों (बीए, बीएससी, बीकॉम) के लिए आवेदन करने की अंतिम तिथि 31 मई 2026 है। व्यावसायिक पाठ्यक्रमों (बीसीए, बीबीए) के लिए भी यह 31 मई 2026 है।"
        }}
    )
    
    await db.chatbotknowledge.update_one(
        {"Intent": "LIBRARY_INFRA"},
        {"$set": {
            "FixedResponseEn": "NPGC has excellent facilities including a well-stocked Library with N-List access, a modern Computer Lab, and a well-maintained Canteen. The campus is Wi-Fi enabled and features smart classrooms for an enhanced learning experience.",
            "FixedResponseHi": "NPGC में उत्कृष्ट सुविधाएं हैं जिनमें एन-लिस्ट एक्सेस वाली एक सुसज्जित लाइब्रेरी, एक आधुनिक कंप्यूटर लैब और एक अच्छी तरह से व्यवस्थित कैंटीन शामिल है।"
        }}
    )

    print("Hardened Fixed Responses (v2) added to MongoDB.")

    client.close()

if __name__ == "__main__":
    asyncio.run(fix())
