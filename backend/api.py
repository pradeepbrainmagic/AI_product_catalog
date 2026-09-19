import os
import mysql.connector
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, UploadFile, File

from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.database.database_layer import DatabaseLayer
from backend.voice.speech_to_text import speech_to_text

from backend.catalog.catalog_search import CatalogSearch
from backend.catalog.catalog_adapter import CatalogAdapter

from backend.conversation.conversation_manager import (
    ConversationManager
)
from backend.voice.speech_to_text import speech_to_text


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="AI Product Catalog API"
)

# =========================================================
# PRODUCT IMAGE DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

PRODUCT_IMAGES_DIR = os.path.join(
    BASE_DIR,
    "data",
    "product_images"
)


# =========================================================
# SERVE PRODUCT IMAGES
# =========================================================

app.mount(
    "/product-images",
    StaticFiles(
        directory=PRODUCT_IMAGES_DIR
    ),
    name="product-images"
)

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"],
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def create_database_connection():

    return mysql.connector.connect(

        host=os.getenv(
            "CATALOG_DB_HOST",
            "localhost"
        ),

        port=int(
            os.getenv(
                "CATALOG_DB_PORT",
                "3306"
            )
        ),

        user=os.getenv(
            "CATALOG_DB_USER",
            "root"
        ),

        password=os.getenv(
            "CATALOG_DB_PASSWORD",
            "Kavi@2"
        ),

        database=os.getenv(
            "CATALOG_DB_NAME",
            "ai_catalog"
        )
    )


# =========================================================
# CREATE BACKEND OBJECTS
# =========================================================

connection = create_database_connection()


database_layer = DatabaseLayer(
    db_connection=connection
)


catalog_adapter = CatalogAdapter()


catalog_search = CatalogSearch(
    catalog_adapter=catalog_adapter
)


conversation_manager = ConversationManager(
    catalog_search=catalog_search,
    database_layer=database_layer
)


# =========================================================
# REQUEST MODEL
# =========================================================

class ChatRequest(BaseModel):

    message: str
    
# =========================================================
# VOICE TRANSCRIPTION
# =========================================================

@app.post("/api/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...)
):

    try:

        # -----------------------------------------------------
        # SAVE TEMPORARY AUDIO FILE
        # -----------------------------------------------------

        import tempfile

        suffix = os.path.splitext(
            audio.filename or ""
        )[1]

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix
        ) as temp_file:

            audio_content = await audio.read()

            temp_file.write(
                audio_content
            )

            temp_audio_path = temp_file.name

        try:

            # -------------------------------------------------
            # WHISPER TRANSCRIPTION
            # -------------------------------------------------

            result = speech_to_text.transcribe(
                temp_audio_path
            )

        finally:

            # -------------------------------------------------
            # DELETE TEMP FILE
            # -------------------------------------------------

            if os.path.exists(
                temp_audio_path
            ):
                os.remove(
                    temp_audio_path
                )

        # -----------------------------------------------------
        # EMPTY TRANSCRIPTION
        # -----------------------------------------------------

        if not result.get("text"):

            return {
                "success": False,
                "message": "Could not understand the audio."
            }

        # -----------------------------------------------------
        # RETURN TRANSCRIPTION
        # -----------------------------------------------------

        return {
            "success": True,
            "data": {
                "text": result["text"],
                "language": result["language"]
            }
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/")
def root():

    return {
        "status": "success",
        "message": "AI Product Catalog API is running."
    }


# =========================================================
# CHAT
# =========================================================

@app.post("/api/chat")
def chat(request: ChatRequest):

    user_message = request.message.strip()

    if not user_message:

        return {
            "success": False,
            "message": "Please enter a message."
        }

    try:

        response = (
            conversation_manager.process_message(
                user_message
            )
        )

        return {
            "success": True,
            "data": response
        }

    except Exception as e:

        import traceback

        print("\n========== CHAT API ERROR ==========")
        print("ERROR:", str(e))
        traceback.print_exc()
        print("====================================\n")

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# VOICE / SPEECH TO TEXT
# =========================================================

from fastapi import UploadFile, File


@app.post("/api/voice")
async def voice_to_text(
    audio: UploadFile = File(...)
):

    try:

        # -----------------------------------------------------
        # READ UPLOADED AUDIO
        # -----------------------------------------------------

        audio_bytes = await audio.read()

        if not audio_bytes:

            return {
                "success": False,
                "message": "Audio file is empty."
            }

        # -----------------------------------------------------
        # TEMPORARY AUDIO FILE
        # -----------------------------------------------------

        import tempfile

        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".webm"
        ) as temp_file:

            temp_file.write(audio_bytes)

            temp_audio_path = temp_file.name

        # -----------------------------------------------------
        # SPEECH TO TEXT
        # -----------------------------------------------------

        result = speech_to_text.transcribe(
            temp_audio_path
        )

        # -----------------------------------------------------
        # CLEANUP
        # -----------------------------------------------------

        try:

            os.remove(
                temp_audio_path
            )

        except Exception:

            pass

        # -----------------------------------------------------
        # RETURN TEXT + LANGUAGE
        # -----------------------------------------------------

        return {

            "success": True,

            "data": {

                "text":
                    result.get(
                        "text",
                        ""
                    ),

                "language":
                    result.get(
                        "language",
                        ""
                    )

            }

        }

    except Exception as e:

        return {

            "success": False,

            "error": str(e)

        }

# =========================================================
# RESET CONVERSATION
# =========================================================

@app.post("/api/reset")
def reset():

    try:

        conversation_manager.reset()

        return {
            "success": True,
            "message": "Conversation reset successfully."
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


# =========================================================
# SHUTDOWN
# =========================================================

@app.on_event("shutdown")
def shutdown():

    global connection

    try:

        if connection:
            connection.close()

    except Exception:
        pass