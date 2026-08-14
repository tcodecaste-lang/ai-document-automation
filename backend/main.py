# backend/main.py

import os
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from dotenv import load_dotenv

# Load environment variables from .env file relative to main.py location
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(base_dir, ".env"))

from backend.services.database import init_db
init_db()

from backend.api.endpoints import router as api_router
from backend.schemas.processing import ErrorResponse

app = FastAPI(
    title="AI Document Automation API",
    version="1.0.0",
    description="Backend processing engine for structural PDF extraction and validation"
)

# Enable CORS for frontend clients
# Allow local development origins and typical production deployment domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For demo convenience. In production, restrict to frontend URLs.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers to match API specifications
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(success=False, error=exc.detail).model_dump()
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Formulate validation error message
    errors = exc.errors()
    msg = "Validation failed: "
    if errors:
        loc = " -> ".join(str(l) for l in errors[0].get("loc", []))
        msg += f"{errors[0].get('msg')} at path '{loc}'."
    else:
        msg += str(exc)
        
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(success=False, error=msg).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Hide traceback, provide friendly error message
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            success=False,
            error=f"An unexpected server error occurred: {str(exc)}"
        ).model_dump()
    )

# Include the endpoints router
app.include_router(api_router, prefix="/api")

# Add a simple health check root
@app.get("/")
def read_root():
    return {"status": "ok", "app": "AI Document Automation API"}
