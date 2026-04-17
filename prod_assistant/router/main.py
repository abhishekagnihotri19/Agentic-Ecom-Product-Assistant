from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
import os


from prod_assistant.workflow.agentic_workflow_with_mcp_webresearch import AgenticRAG

# ✅ Create ONE global agent instance
agent = AgenticRAG()

# ✅ Lifespan (modern startup handler)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔄 Initializing MCP tools...")
    await agent.initialize()
    print("✅ MCP initialized")

    yield

    print("🛑 Shutting down app...")


# ✅ FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# ✅ Templates
templates = Jinja2Templates(directory="templates")



app.mount(
    "/static",
    StaticFiles(directory=os.path.join(os.getcwd(), "static")),
    name="static"
)

# ---------------- ROUTES ---------------- #
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    print("🔥 INDEX ROUTE HIT")
    return templates.TemplateResponse(
        request,                 # ✅ FIRST
        "index.html",            # ✅ SECOND
        {"request": request}     # ✅ THIRD
    )
@app.post("/get", response_class=PlainTextResponse)
async def chat(msg: str = Form(...)):
    try:
        answer = agent.run_pipeline(msg)
        return answer   # ✅ already string now

    except Exception as e:
        print("❌ ERROR:", str(e))
        return f"⚠️ AI Error: {str(e)}"

"""
import uvicorn
import os
from fastapi import FastAPI, Request,Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from prod_assistant.workflow.agentic_workflow_with_mcp_webresearch import AgenticRAG
from jinja2 import Environment, FileSystemLoader


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

app= FastAPI()
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

templates= Jinja2Templates(directory="templates")
templates.env.cache = {}  #  IMPORTANT FIX

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

#FastAPI Endpoints

@app.get("/", response_class= HTMLResponse)
async def index(request:Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/get")
async def chat (msg:str= Form(...)):
    rag_agent= AgenticRAG()
    answer= await rag_agent.run(msg)
    return answer """