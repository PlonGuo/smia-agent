# PydanticAI + Langfuse + RAG 从零到一完整教程

> 基于 SmIA 项目的真实代码，由浅入深讲解。

---

## 目录

0. [FastAPI 基础与项目架构](#0-fastapi-基础与项目架构)
1. [PydanticAI 核心概念](#1-pydanticai-核心概念)
2. [SmIA 项目中的三种 Agent 架构](#2-smia-项目中的三种-agent-架构)
3. [Tool 系统详解](#3-tool-系统详解)
4. [依赖注入 (Dependencies)](#4-依赖注入-dependencies)
5. [结构化输出 (Structured Output)](#5-结构化输出-structured-output)
6. [Agent 运行生命周期](#6-agent-运行生命周期)
7. [Langfuse 可观测性](#7-langfuse-可观测性)
8. [RAG + Embedding + Vector DB](#8-rag--embedding--vector-db)
9. [PydanticAI vs LangChain 对比](#9-pydanticai-vs-langchain-对比)

---

## 0. FastAPI 基础与项目架构

### 0.1 FastAPI 是什么？

FastAPI 是一个现代 Python Web 框架，核心特点：

- **类型驱动**：用 Python 类型注解自动生成 API schema、请求验证、文档
- **异步原生**：基于 `async/await`，天然适合 I/O 密集型应用（API 调用、数据库、爬虫）
- **自动文档**：访问 `/docs` 就有 Swagger UI，`/redoc` 有 ReDoc
- **依赖注入**：内置 DI 系统，用于 auth、数据库连接等

### 0.2 SmIA 的 FastAPI 入口

**文件**: `api/index.py`

```python
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Lifespan — 应用启动/关闭时执行的逻辑
@asynccontextmanager
async def lifespan(app):
    # 启动时：初始化（比如 seed 管理员）
    from services.database import seed_admin_if_empty
    seed_admin_if_empty()
    yield
    # 关闭时：清理资源（这里没有需要清理的）

app = FastAPI(title="SmIA API", version="0.1.0", lifespan=lifespan)
```

**Lifespan 的作用**：
- 替代旧版的 `@app.on_event("startup")` 和 `@app.on_event("shutdown")`
- `yield` 之前的代码 = 启动逻辑
- `yield` 之后的代码 = 关闭逻辑
- 适合初始化数据库连接池、缓存客户端等

### 0.3 中间件 (Middleware)

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smia-agent.vercel.app",        # 生产前端
        "http://localhost:5173",                  # 开发前端
    ],
    allow_origin_regex=r"https://smia-agent(-[\w-]+)?-xxx\.vercel\.app",  # Preview 部署
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "x-internal-secret"],
)
```

**CORS 是什么**：
- 浏览器安全策略：前端 (`smia-agent.vercel.app`) 访问后端 (`smia-agent.fly.dev`) 属于跨域
- 必须在后端声明允许哪些 origin
- `allow_credentials=True`：允许发送 cookies/auth headers
- `allow_origin_regex`：Vercel preview 部署的 URL 是动态的，用正则匹配

### 0.4 Router（路由组织）

FastAPI 用 `APIRouter` 拆分不同功能模块：

```python
# api/routes/analyze.py
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["analyze"])

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest, ...):
    ...

@router.get("/analyze/quota", response_model=QuotaResponse)
async def get_quota(...):
    ...
```

```python
# api/index.py — 注册所有 router
app.include_router(analyze_router)        # /api/analyze, /api/analyze/quota
app.include_router(ai_daily_report_router) # /api/ai-daily-report/*
app.include_router(telegram_router)        # /api/telegram/webhook
app.include_router(auth_router)           # /api/auth/*
app.include_router(admin_router)          # /api/admin/*
# ...
```

**`prefix`**：所有这个 router 下的路由自动加前缀（`/api`）
**`tags`**：在 Swagger 文档中分组显示
**`response_model`**：自动用 Pydantic model 验证响应 + 生成文档

### 0.5 请求与响应模型

FastAPI 深度集成 Pydantic：

```python
# api/models/schemas.py
from pydantic import BaseModel, Field
from typing import Literal

class AnalyzeRequest(BaseModel):
    query: str = Field(min_length=3, max_length=200)  # 自动验证长度
    time_range: Literal["day", "week", "month", "year"] = "week"  # 枚举
    force_refresh: bool = False

class AnalyzeResponse(BaseModel):
    report: TrendReport
    message: str = "Analysis complete"
    cached: bool = False
    remaining: int | None = None
```

**工作原理**：
1. 请求进来 → FastAPI 用 `AnalyzeRequest` 解析 JSON body
2. 验证不通过 → 自动返回 422 + 详细错误信息
3. 你的代码只需处理已验证的数据
4. 响应 → FastAPI 用 `AnalyzeResponse` 序列化 + 过滤字段

```python
# 使用方式 — body 已经是验证过的 AnalyzeRequest 对象
@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(body: AnalyzeRequest, ...):
    query = body.query  # str, 长度 3-200，已验证
    time_range = body.time_range  # "day"|"week"|"month"|"year"
```

### 0.6 依赖注入 (Depends)

FastAPI 的 `Depends` 是其最强大的特性之一：

```python
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 定义依赖
_bearer_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    """从 Authorization header 提取 JWT，验证后返回用户信息."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    token = credentials.credentials
    # 用 Supabase 验证 JWT
    user_response = client.auth.get_user(token)
    return AuthenticatedUser(user_id=user.id, access_token=token)


# 在路由中使用 — user 参数自动通过 DI 注入
@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    user: AuthenticatedUser = Depends(get_current_user),  # ⭐ DI
):
    # user 已经是验证过的 AuthenticatedUser
    print(user.user_id)  # "abc-123"
```

**依赖注入链**：

```
HTTP Request (Authorization: Bearer xxx)
    │
    ├── FastAPI 自动调用 _bearer_scheme
    │   └── 提取 Bearer token → HTTPAuthorizationCredentials
    │
    ├── FastAPI 自动调用 get_current_user(credentials)
    │   └── 验证 JWT → AuthenticatedUser
    │
    └── 注入到路由函数的 user 参数
```

**DI 的好处**：
- 不需要在每个路由里手动解析 header
- 验证逻辑集中在一处
- 测试时可以 override（`app.dependency_overrides[get_current_user] = mock_user`）

### 0.7 异常处理

```python
from fastapi import HTTPException, status

# 在路由中抛出
raise HTTPException(
    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
    detail="Rate limit exceeded. You can perform 5 analyses per day.",
)

# 全局异常处理器
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    print(f"[VALIDATION] {request.url.path}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # 捕获所有未处理的异常，记录日志，返回安全的错误信息
    tb = traceback.format_exc()
    print(f"[UNHANDLED] {request.url.path}: {exc}\n{tb[-500:]}")
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})
```

**设计原则**：
- `HTTPException`：预期的错误（401, 403, 404, 429）— 返回详细信息
- 全局 handler：意外的错误 — 记录完整 traceback，但只返回通用信息（不泄露内部细节）
- 开发环境可以返回详细错误（`if settings.environment == "development"`）

### 0.8 Background Tasks（后台任务）

SmIA 的 Digest 使用 `asyncio.create_task` 模式（不是 FastAPI 的 `BackgroundTasks`）：

```python
# api/routes/ai_daily_report.py

# 跟踪后台任务，防止被 GC 回收
_background_tasks: set[asyncio.Task] = set()

def _task_done(task: asyncio.Task) -> None:
    _background_tasks.discard(task)
    if not task.cancelled() and task.exception():
        logger.error("Background digest failed: %s", task.exception())

@router.get("/today")
async def get_today_digest(
    topic: str = Query("ai"),
    user: AuthenticatedUser = Depends(get_current_user),
):
    result = claim_or_get_digest(user.user_id, user.access_token, topic=topic)

    if result.get("claimed"):
        # ⭐ 启动后台任务，HTTP 立即返回
        task = asyncio.create_task(run_digest(result["digest_id"], topic=topic))
        _background_tasks.add(task)       # 防止 GC
        task.add_done_callback(_task_done) # 错误处理

    return result  # 立即返回 {"status": "collecting"}
```

**为什么不用 FastAPI 的 `BackgroundTasks`**：
- FastAPI 的 `BackgroundTasks` 在 response 发送后才执行
- `asyncio.create_task` 更灵活 — 任务立即开始，不等 response
- 需要手动管理任务引用（`_background_tasks` set），否则 Python GC 会回收

**Digest 的轮询模式**：

```
前端:                           后端:
GET /today ──────────────────→ claim lock, start background task
         ←────────────────── {"status": "collecting"}
GET /today (2s later) ───────→ check status
         ←────────────────── {"status": "analyzing"}
GET /today (2s later) ───────→ check status
         ←────────────────── {"status": "completed", "digest": {...}}
```

### 0.9 配置管理 (Pydantic Settings)

```python
# api/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 每个字段 = 一个配置项，自动从环境变量读取
    supabase_url: str = ""
    openai_api_key: str = ""
    analysis_model: str = "gpt-4.1"
    environment: str = ""

    @property
    def effective_openai_key(self) -> str:
        """两个可能的 key 名，取有值的那个."""
        return (self.openai_api_key or self.open_ai_api_key).strip()

    model_config = {
        "env_file": str(_env_file),  # 从 local.env 读取
        "extra": "ignore",           # 忽略 .env 中多余的变量
    }

# 单例 — 整个应用共享
settings = Settings()
```

**加载优先级**（高到低）：
1. 环境变量（Fly.io / Vercel 设置的）
2. `.env` 文件（`local.env`）
3. 默认值（`= ""`）

### 0.10 Query 参数

```python
from fastapi import Query

@router.get("/list")
async def list_digests(
    topic: str = Query("ai"),                    # 默认值 "ai"
    page: int = Query(1, ge=1),                  # >= 1
    per_page: int = Query(20, ge=1, le=100),     # 1-100
    user: AuthenticatedUser = Depends(get_current_user),
):
    # topic, page, per_page 已验证
    offset = (page - 1) * per_page
    ...
```

### 0.11 MCP Server 挂载

SmIA 把 MCP server 作为子应用挂载：

```python
from routes.mcp_server import mcp

# 挂载到 /mcp 路径
app.mount("/mcp", mcp.streamable_http_app())
```

`app.mount()` 让你可以把任何 ASGI 应用挂载到 FastAPI 下。

### 0.12 SmIA 项目目录结构

```
api/
├── index.py                    # FastAPI 入口（app 创建、中间件、路由注册）
├── core/                       # 基础设施
│   ├── config.py              # Pydantic Settings（环境变量 → Python 对象）
│   ├── auth.py                # JWT 认证依赖
│   ├── rate_limit.py          # 速率限制
│   └── langfuse_config.py     # Langfuse 初始化
├── models/                     # Pydantic 数据模型
│   ├── schemas.py             # 分析相关：TrendReport, AnalyzeRequest...
│   ├── digest_schemas.py      # Digest 相关：DigestItem, DailyDigestLLMOutput...
│   └── update_schemas.py      # 更新通知相关
├── routes/                     # HTTP 路由（Controller 层）
│   ├── analyze.py             # POST /api/analyze
│   ├── ai_daily_report.py     # Digest 生命周期
│   ├── telegram.py            # Telegram webhook
│   ├── auth.py                # 绑定码等
│   ├── admin.py               # 管理后台
│   └── ...
├── services/                   # 业务逻辑（Service 层）
│   ├── agent.py               # PydanticAI Agent 配置 + analyze_topic()
│   ├── tools.py               # PydanticAI Tool 定义
│   ├── crawler.py             # 数据抓取（Reddit, YouTube, Amazon...）
│   ├── digest_service.py      # Digest 编排（收集 → 分析 → 保存 → 通知）
│   ├── digest_agent.py        # Digest LLM Agent
│   ├── database.py            # Supabase 操作
│   ├── cache.py               # 两级缓存
│   └── collectors/            # 数据源收集器
│       ├── base.py            # Collector Protocol
│       ├── arxiv_collector.py
│       ├── hackernews_collector.py
│       └── ...
├── config/
│   └── digest_topics.py       # Topic 配置（AI, Geopolitics...）
└── tests/                      # 测试
    ├── conftest.py            # 测试 fixtures
    └── test_services/         # 服务层测试
```

**分层架构**：

```
Route (Controller) → Service → Agent/Tool → Crawler → 外部 API
      ↑                 ↑          ↑
   验证请求         业务逻辑      AI 决策
   权限检查         缓存管理      数据处理
   错误处理         元数据注入    格式化输出
```

### 0.13 FastAPI + PydanticAI 集成模式总结

```
┌─────────────────── FastAPI 层 ──────────────────────┐
│                                                      │
│  Request → Pydantic Model 验证 → Depends(auth)      │
│                    │                                  │
│                    ▼                                  │
│  ┌─────────── Service 层 ──────────┐                 │
│  │                                  │                 │
│  │  缓存检查 → Langfuse trace →    │                 │
│  │                                  │                 │
│  │  ┌─── PydanticAI Agent ───┐     │                 │
│  │  │ model + prompt + tools │     │                 │
│  │  │         │              │     │                 │
│  │  │    LLM 决策            │     │                 │
│  │  │    ├── Tool 1          │     │                 │
│  │  │    ├── Tool 2          │     │                 │
│  │  │    └── 综合分析        │     │                 │
│  │  │         │              │     │                 │
│  │  │  output_type 验证      │     │                 │
│  │  └────────│───────────────┘     │                 │
│  │           │                      │                 │
│  │  元数据注入 → 缓存存储 → flush   │                 │
│  └───────────│──────────────────────┘                 │
│              ▼                                        │
│  Pydantic Model 序列化 → Response                     │
└──────────────────────────────────────────────────────┘
```

---

## 1. PydanticAI 核心概念

### 1.1 PydanticAI 是什么？

PydanticAI 是由 Pydantic 团队开发的 AI Agent 框架。核心思想：

- **用 Pydantic 模型定义 LLM 的输出结构** — LLM 不再返回自由文本，而是返回你定义的 Python 对象
- **用 Python 函数定义 Tool** — LLM 可以调用你的函数获取信息
- **类型安全** — 依赖注入、输出类型、工具参数全部有类型检查
- **模型无关** — 同一个 Agent 可以用 OpenAI、Anthropic、Gemini 等

### 1.2 核心组件

```
┌─────────────────────────────────────────────────┐
│                    Agent                         │
│  ┌───────────┐ ┌──────────┐ ┌───────────────┐  │
│  │   Model   │ │  System  │ │  Output Type  │  │
│  │ openai:   │ │  Prompt  │ │  (Pydantic)   │  │
│  │ gpt-4.1   │ │          │ │  TrendReport  │  │
│  └───────────┘ └──────────┘ └───────────────┘  │
│  ┌──────────────────────────────────────────┐   │
│  │              Tools[]                      │   │
│  │  fetch_youtube, fetch_hackernews, ...     │   │
│  └──────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────┐   │
│  │         Dependencies (Deps)               │   │
│  │  AnalysisDeps(query, time_range)          │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

### 1.3 最简 Agent（概念演示）

```python
from pydantic import BaseModel
from pydantic_ai import Agent

# 1. 定义输出结构
class Sentiment(BaseModel):
    score: float      # 0.0 - 1.0
    label: str        # "Positive" / "Negative" / "Neutral"
    reasoning: str

# 2. 创建 Agent
agent = Agent(
    model="openai:gpt-4.1",
    output_type=Sentiment,
    system_prompt="Analyze the sentiment of user input.",
)

# 3. 运行
result = await agent.run("I love this product!")
print(result.output)
# Sentiment(score=0.92, label="Positive", reasoning="Strong positive language...")
print(result.usage())
# Usage(requests=1, request_tokens=45, response_tokens=32, total_tokens=77)
```

**关键要点**：
- `output_type=Sentiment` 告诉 PydanticAI："让 LLM 返回一个 `Sentiment` 对象"
- PydanticAI 在底层使用 OpenAI 的 structured output 或 function calling 来确保 LLM 严格返回符合 schema 的 JSON
- `result.output` 是一个 **Python 对象**，不是字符串
- `result.usage()` 返回 token 消耗信息

---

## 2. SmIA 项目中的三种 Agent 架构

SmIA 实际使用了 **三个不同的 Agent**，展示了三种不同的架构模式：

### 2.1 Analysis Agent（多工具 Agent + 单例模式）

**文件**: `api/services/agent.py`

```python
# 依赖类型 — 通过 RunContext 传递给每个 Tool
@dataclass
class AnalysisDeps:
    query: str
    time_range: str = "week"

# Agent 创建（工厂函数）
def create_agent() -> Agent[AnalysisDeps, TrendReport]:
    return Agent(
        model=f"openai:{_get_model_name()}",  # "openai:gpt-4.1"
        output_type=TrendReport,               # 结构化输出类型
        system_prompt=SYSTEM_PROMPT,            # 系统提示词
        tools=[                                 # 9 个工具
            fetch_youtube_tool,
            fetch_amazon_tool,
            fetch_hackernews_tool,
            # ...
        ],
        retries=2,                              # 输出校验失败时重试次数
        name="smia-analyzer",                   # 在 Langfuse 中显示的名称
        defer_model_check=True,                 # 延迟模型验证（serverless 必需）
    )

# 单例模式 — 创建一次，所有请求复用
agent = create_agent()
```

**架构特点**：
- **泛型类型** `Agent[AnalysisDeps, TrendReport]`：第一个类型参数是依赖，第二个是输出
- **单例模式**：`Agent` 对象是轻量配置，不持有连接或状态，可以安全复用
- **defer_model_check=True**：在 serverless 环境（Vercel/Fly.io）中，启动时 API key 可能还没设置，延迟到 `.run()` 时才验证

### 2.2 Digest Agent（无工具 Agent + 动态 Prompt + 非单例）

**文件**: `api/services/digest_agent.py`

```python
def _create_digest_agent(topic: str) -> Agent[None, DailyDigestLLMOutput]:
    return Agent(
        model=f"openai:{settings.digest_model}",
        output_type=DailyDigestLLMOutput,
        system_prompt=_build_system_prompt(topic),  # 动态构建 prompt
        retries=2,
        name=f"digest-{topic}",                     # 动态名称
        defer_model_check=True,
    )
```

**架构特点**：
- **`Agent[None, ...]`**：没有依赖注入，因为 digest 不需要 Tool
- **没有 tools**：这是一个纯分析 Agent，接收预格式化的文本，输出结构化摘要
- **每次创建新实例**：因为 prompt 是 topic-specific 的（AI / Geopolitics / Climate...）
- Agent 对象创建没有网络开销，只是配置对象

### 2.3 Update Summarizer（最简 Agent + 后处理验证）

**文件**: `api/services/update_summarizer.py`

```python
_summarizer = Agent(
    model="openai:gpt-4o-mini",      # 便宜的模型
    output_type=UpdateSummary,
    system_prompt=SYSTEM_PROMPT,
    retries=1,
    name="update-summarizer",
    defer_model_check=True,
)

# 后处理：验证 LLM 输出不包含 URL 或 HTML（防 prompt injection）
def _validate_summary(summary: UpdateSummary) -> UpdateSummary:
    for text in [summary.headline, summary.summary, *summary.highlights]:
        if _URL_PATTERN.search(text):
            raise ValueError(f"Summary contains URL: {text[:80]}")
    return summary
```

**架构特点**：
- **最简形式**：无 tools，无 deps，固定 prompt
- **后处理验证**：PydanticAI 保证结构正确，但你仍然需要额外的业务逻辑验证
- **低成本模型**：对于简单任务用 gpt-4o-mini 节省成本

### 2.4 三种模式对比

| 特性 | Analysis Agent | Digest Agent | Update Summarizer |
|------|---------------|-------------|-------------------|
| 依赖类型 | `AnalysisDeps` | `None` | `None` |
| 输出类型 | `TrendReport` | `DailyDigestLLMOutput` | `UpdateSummary` |
| Tools | 9 个 | 0 | 0 |
| 实例化 | 单例 | 每次新建 | 单例 |
| Prompt | 静态 | 动态（per topic） | 静态 |
| 模型 | gpt-4.1（可配） | 可配 | gpt-4o-mini（固定） |
| 后处理 | 元数据注入 | 无 | URL/HTML 检查 |

---

## 3. Tool 系统详解

### 3.1 Tool 的本质

PydanticAI 的 Tool 就是一个普通的 Python async 函数，LLM 会在需要时自动调用它。

**核心概念**：
1. 函数签名 → 自动转换为 JSON Schema → 传给 LLM 的 `tools` 参数
2. LLM 决定调用哪个 tool，传什么参数
3. PydanticAI 执行函数，把返回值（字符串）传回 LLM
4. LLM 可以调用多个 tool，循环直到它认为信息足够

### 3.2 SmIA 的 Tool 注册方式：函数列表

SmIA 使用的是 **列表传递** 方式（而非装饰器方式）：

```python
# 方式 1：函数列表（SmIA 使用的）
agent = Agent(
    model="openai:gpt-4.1",
    tools=[fetch_youtube_tool, fetch_hackernews_tool, ...],
    ...
)

# 方式 2：装饰器（另一种常见方式）
agent = Agent(model="openai:gpt-4.1", ...)

@agent.tool
async def fetch_youtube(ctx: RunContext, query: str) -> str:
    ...
```

两种方式功能完全相同。SmIA 选择列表方式是因为 tools 定义在单独的文件 (`tools.py`) 中。

### 3.3 Tool 函数签名解析

```python
# api/services/tools.py
async def fetch_hackernews_tool(ctx: RunContext, query: str) -> str:
    """Fetch discussions from Hacker News (Y Combinator's tech community).
    SOURCE: Hacker News (news.ycombinator.com) via Algolia search API.
    BEST FOR: tech news, startup discussions, developer opinions...
    NOT FOR: world politics, sports, entertainment..."""
```

**参数规则**：
- **第一个参数必须是 `ctx: RunContext`**：PydanticAI 自动注入，包含 `ctx.deps`（你的依赖）
- **之后的参数就是 LLM 要填的**：`query: str` → LLM 会传入搜索词
- **返回值必须是 `str`**：返回给 LLM 的文本（LLM 看不到 Python 对象）
- **docstring 极其重要**：PydanticAI 把它转成 tool description，LLM 靠它决定何时使用这个 tool

### 3.4 Tool 执行流程（以一次 analyze 为例）

```
用户请求: "What do people think about the new iPhone?"
    │
    ▼
Agent.run("What do people think about the new iPhone?")
    │
    ▼
LLM 收到: system_prompt + user_message + 9 个 tool 的 JSON Schema
    │
    ▼
LLM 决策: "这是消费产品话题，我应该用 Amazon + YouTube"
    │
    ├── tool_call: fetch_amazon_tool(query="new iPhone")
    │   └── 返回: "# Amazon Results for 'new iPhone' (5 products)\n..."
    │
    ├── tool_call: fetch_youtube_tool(query="new iPhone review")
    │   └── 返回: "# YouTube Results for 'new iPhone' (8 videos)\n..."
    │
    ▼
LLM 收到所有 tool 结果，综合分析
    │
    ▼
LLM 输出: TrendReport JSON（结构化输出）
    │
    ▼
PydanticAI 验证 JSON → TrendReport 对象
```

### 3.5 Tool 内部的典型模式

SmIA 的 tool 遵循一个统一模式：

```python
async def fetch_xxx_tool(ctx: RunContext, query: str) -> str:
    # 1. 从依赖中获取配置
    time_range = getattr(ctx.deps, "time_range", "week")
    limits = get_fetch_limits(time_range)

    # 2. 检查缓存
    cached = get_cached_fetch(query, time_range, "xxx")
    if cached is not None:
        items = cached
    else:
        # 3. 实际抓取数据
        items = await fetch_xxx(query, limit=limits["xxx"])
        if items:
            set_cached_fetch(query, time_range, "xxx", items)

    if not items:
        return f"No results found for '{query}'."

    # 4. LLM 相关性过滤（可选）
    relevant, yield_ratio = await relevance_filter(query, items, "xxx")

    # 5. 自适应重取（如果相关性低于 50%）
    if yield_ratio < 0.5 and len(items) >= initial_limit and cached is None:
        items = await fetch_xxx(query, limit=initial_limit * 2)
        relevant, _ = await relevance_filter(query, items, "xxx")

    # 6. 格式化为 Markdown 返回给 LLM
    sections = [f"### {item['title']}\n{item['body']}" for item in relevant]
    return f"# Results ({len(sections)} items)\n\n" + "\n\n---\n\n".join(sections)
```

### 3.6 System Prompt 中的 Tool 选择引导

SmIA 不是让 LLM 盲目选择 tool，而是在 system prompt 中写了详细的路由规则：

```
## TOOL SELECTION STRATEGY
### Tech / Programming / AI topics:
→ Use: fetch_hackernews, fetch_devto, fetch_stackexchange, fetch_youtube

### World News / Politics / Current Events:
→ Use: fetch_guardian, fetch_news, fetch_youtube

### Consumer Products / Shopping:
→ Use: fetch_amazon, fetch_youtube

### Rules:
- Pick 2-4 tools, not all of them
- NEVER use all tools at once — it wastes time and tokens
```

**为什么需要这样做**：
- LLM 默认可能会调用所有 9 个 tool，浪费 API 费用和时间
- 通过 prompt 引导，LLM 像人类分析师一样，根据话题类型选择最合适的 2-4 个数据源

---

## 4. 依赖注入 (Dependencies)

### 4.1 概念

PydanticAI 的依赖注入让你把 **运行时上下文** 传递给 tools，而不需要全局变量。

```python
@dataclass
class AnalysisDeps:
    query: str
    time_range: str = "week"
```

### 4.2 注入流程

```
1. 创建依赖对象
   deps = AnalysisDeps(query="iPhone", time_range="month")

2. 传给 agent.run()
   result = await agent.run("Analyze iPhone sentiment", deps=deps)

3. Tool 中通过 ctx.deps 访问
   async def fetch_youtube_tool(ctx: RunContext, query: str) -> str:
       time_range = ctx.deps.time_range  # "month"
       ...
```

### 4.3 实际代码

```python
# api/services/agent.py:155-158
@observe(name="pydantic_ai_agent_run")
async def _run_agent(query: str, time_range: str = "week"):
    deps = AnalysisDeps(query=query, time_range=time_range)
    return await agent.run(query, deps=deps)
```

### 4.4 更复杂的依赖场景（假设扩展）

如果需要传递数据库连接、API client 等：

```python
@dataclass
class AnalysisDeps:
    query: str
    time_range: str = "week"
    db: AsyncClient = None          # Supabase client
    user_id: str = None             # 当前用户
    langfuse_span: Span = None      # 用于嵌套 tracing
```

这是 PydanticAI 相比 LangChain 的优势之一 — **依赖注入是类型安全的**，IDE 自动补全。

---

## 5. 结构化输出 (Structured Output)

### 5.1 核心原理

PydanticAI 使用 Pydantic BaseModel 作为输出类型。底层实现：

1. 从 `output_type` 提取 JSON Schema
2. 通过 OpenAI 的 `response_format={"type": "json_schema", "json_schema": ...}` 强制 LLM 输出合规 JSON
3. 用 Pydantic 解析验证 LLM 返回的 JSON
4. 如果验证失败，自动重试（最多 `retries` 次），并把错误信息传回 LLM

### 5.2 SmIA 的 TrendReport

```python
# api/models/schemas.py
class TopDiscussion(BaseModel):
    title: str
    url: str
    source: str
    score: int | None = None
    snippet: str | None = None

class TrendReport(BaseModel):
    topic: str = Field(description="Main topic analyzed")
    sentiment: Literal["Positive", "Negative", "Neutral"]
    sentiment_score: float = Field(ge=0, le=1)         # Pydantic 验证：0-1
    summary: str = Field(min_length=50, max_length=500) # Pydantic 验证：长度
    key_insights: list[str] = Field(min_length=3, max_length=5)
    top_discussions: list[TopDiscussion] = Field(max_length=15)
    keywords: list[str] = Field(min_length=5, max_length=10)
    source_breakdown: dict[str, int]
    charts_data: dict = Field(default_factory=dict)

    # Metadata（不由 LLM 填，后续代码注入）
    id: str | None = None
    user_id: str | None = None
    langfuse_trace_id: str | None = None
    ...
```

**设计要点**：
- `Literal["Positive", "Negative", "Neutral"]` → LLM 只能在这三个值中选
- `Field(ge=0, le=1)` → 自动验证范围，不合格就重试
- `Field(min_length=3, max_length=5)` → 列表长度约束
- `description="..."` → 传给 LLM 的 JSON Schema 中的 description 字段
- **Metadata 字段用 `None` 默认值**：LLM 不填这些，由服务层代码设置

### 5.3 重试机制

```python
agent = Agent(
    ...,
    retries=2,  # 如果 Pydantic 验证失败，最多重试 2 次
)
```

重试流程：
1. LLM 输出 JSON
2. Pydantic 验证失败（比如 `sentiment_score=1.5` 超过 `le=1`）
3. PydanticAI 把错误信息附加到 messages 里，再请求 LLM
4. LLM 看到错误，修正输出
5. 最多重试 `retries` 次，都失败就抛 `ValidationError`

---

## 6. Agent 运行生命周期

### 6.1 完整调用链

以 `POST /api/analyze` 为例：

```
HTTP Request
    │
    ▼
[Route] analyze.py:analyze()
    ├── auth: get_current_user(JWT) → AuthenticatedUser
    ├── rate_limit: check_rate_limit(user_id)
    │
    ▼
[Service] agent.py:analyze_topic()
    ├── 检查 Tier 2 缓存 (analysis_cache)
    │   └── 命中 → 返回 (TrendReport, cached=True)
    │
    ├── 设置 Langfuse trace 元数据
    │
    ├── _run_agent(query, time_range)
    │   ├── 创建 AnalysisDeps
    │   └── agent.run(query, deps=deps)
    │       │
    │       ├── [内部] 发送 system_prompt + user_msg + tools schema 给 LLM
    │       ├── [内部] LLM 返回 tool_call(fetch_hackernews, query="...")
    │       ├── [内部] PydanticAI 执行 fetch_hackernews_tool(ctx, query)
    │       │   └── 抓取 → 缓存 → 过滤 → 格式化 → 返回字符串
    │       ├── [内部] LLM 返回 tool_call(fetch_youtube, query="...")
    │       ├── [内部] PydanticAI 执行 fetch_youtube_tool(ctx, query)
    │       ├── [内部] LLM 收到所有 tool 结果
    │       ├── [内部] LLM 输出 TrendReport JSON
    │       └── [内部] Pydantic 验证 → TrendReport 对象
    │
    ├── 注入元数据 (query, user_id, processing_time, langfuse_trace_id, token_usage)
    ├── 写入 Tier 2 缓存
    ├── flush Langfuse
    └── 返回 (TrendReport, cached=False)
    │
    ▼
[Route] 返回 AnalyzeResponse(report=..., cached=False, remaining=4)
```

### 6.2 Digest Agent 的不同模式

Digest 使用 **background task** 模式（因为收集+分析要 30-60 秒）：

```
GET /api/ai-daily-report/today?topic=ai
    │
    ▼
claim_or_get_digest(user_id, topic)
    ├── 调用 Supabase RPC "claim_digest_generation"（分布式锁）
    │   ├── 已有 completed → 直接返回 digest
    │   ├── 已有 in-progress → 返回 status: "analyzing"
    │   └── claimed → 返回 status: "collecting"
    │
    ▼ (HTTP 立即返回，不等待)

asyncio.create_task(run_digest(digest_id, topic))
    │
    ▼ (后台运行)
run_digest()
    ├── Phase 1: 并行收集（asyncio.gather）
    │   ├── arxiv_collector.collect()
    │   ├── github_collector.collect()
    │   ├── rss_collector.collect()
    │   └── bluesky_collector.collect()
    │
    ├── Phase 2: LLM 分析
    │   ├── _create_digest_agent(topic="ai")  # 每次新建
    │   └── agent.run(items_text) → DailyDigestLLMOutput
    │
    ├── Phase 3: 保存到 DB
    └── Phase 4: Telegram 通知

前端轮询 GET /status/{digest_id} 直到 status=completed
```

---

## 7. Langfuse 可观测性

### 7.1 Langfuse 是什么？

Langfuse 是 LLM 应用的可观测性平台（类似 Datadog 但专为 LLM 设计），提供：
- **Traces**：完整请求链路追踪
- **Generations**：每次 LLM 调用的输入/输出/token/cost
- **Spans**：自定义的代码段耗时跟踪
- **Dashboard**：token 用量、延迟、成本统计

### 7.2 初始化

```python
# api/core/langfuse_config.py

def init_langfuse() -> None:
    # 1. 设置环境变量（Langfuse v3 从环境变量读取配置）
    os.environ["LANGFUSE_PUBLIC_KEY"] = settings.langfuse_public_key
    os.environ["LANGFUSE_SECRET_KEY"] = settings.langfuse_secret_key
    os.environ["LANGFUSE_HOST"] = settings.langfuse_base_url

    # 2. ⭐ 核心：一行代码 instrument 所有 PydanticAI agent
    Agent.instrument_all()
```

**`Agent.instrument_all()` 做了什么？**
- PydanticAI 内置了 OpenTelemetry 支持
- 这一行让所有 `agent.run()` 自动导出 span 到 Langfuse
- 自动记录：model name, input messages, output, tokens, cost, latency
- **零代码改动**就能观测所有 Agent 行为

### 7.3 @observe 装饰器

Langfuse v3 的 `@observe` 让你手动创建 span：

```python
from langfuse import observe, get_client

# 自动创建 span，函数执行时间被记录
@observe(name="pydantic_ai_agent_run")
async def _run_agent(query: str, time_range: str = "week"):
    deps = AnalysisDeps(query=query, time_range=time_range)
    return await agent.run(query, deps=deps)

@observe()  # 不传 name 则使用函数名
async def analyze_topic(...):
    ...
```

### 7.4 Trace 层级结构

Langfuse 中的 trace 是层级的（parent → child）：

```
Trace: analyze_topic
 ├── Span: pydantic_ai_agent_run
 │   ├── Generation: gpt-4.1 (tool selection)
 │   │   └── input: system_prompt + user_msg + tools
 │   │       output: tool_call(fetch_hackernews)
 │   │
 │   ├── Span: fetch_hackernews (crawler.py @observe)
 │   │   └── HTTP call to Algolia API
 │   │
 │   ├── Span: relevance_filter (@observe)
 │   │   └── Generation: gpt-4.1-nano
 │   │       └── input: items + query
 │   │           output: [true, false, true, ...]
 │   │
 │   ├── Span: fetch_youtube (crawler.py @observe)
 │   │   └── HTTP call to YouTube API
 │   │
 │   └── Generation: gpt-4.1 (final synthesis)
 │       └── input: all tool results
 │           output: TrendReport JSON
 │
 └── Metadata: user_id, session_id, tags, trace_id
```

### 7.5 设置 Trace 元数据

```python
# api/core/langfuse_config.py
def trace_metadata(user_id, session_id=None, source="web", tags=None):
    client = get_client()
    client.update_current_trace(
        user_id=user_id,                              # 谁触发的
        session_id=session_id,                         # 可选会话
        tags=["analysis", "web", "time:week", "production"],  # 筛选标签
        metadata={"source": source, "environment": "production"},
    )
```

### 7.6 获取 Trace ID

```python
# 存到数据库，方便从 report 跳转到 Langfuse 查看详情
report.langfuse_trace_id = get_client().get_current_trace_id()
```

### 7.7 Flush

```python
# 确保事件发送到 Langfuse 服务器
flush_langfuse()
```

Langfuse SDK 是异步批量发送的，如果你的函数执行完就退出（比如 serverless），事件可能来不及发送。`flush()` 强制立即发送。

### 7.8 OpenAI 客户端包装

```python
from langfuse.openai import AsyncOpenAI  # ⭐ 不是 openai.AsyncOpenAI

# 这个客户端的所有 API 调用自动被 Langfuse 追踪
_openai_client = AsyncOpenAI(api_key=settings.effective_openai_key)
```

SmIA 在 `relevance_filter` 中直接调用 OpenAI API（不通过 PydanticAI），使用 Langfuse 包装的客户端来保持 tracing 连续性。

### 7.9 Langfuse Dashboard 能看到什么？

1. **每次请求的完整链路**：从 API 入口到每个 tool 调用到最终输出
2. **Token 用量**：每个 LLM 调用消耗的 tokens
3. **成本估算**：根据 token 数和模型价格自动计算
4. **延迟分布**：哪些 tool 最慢
5. **按用户/标签筛选**：查看特定用户或时间范围的 traces
6. **输入输出**：查看发给 LLM 的 prompt 和返回的 response

---

## 8. RAG + Embedding + Vector DB

### 8.1 什么是 RAG？

RAG (Retrieval-Augmented Generation) 的核心思想：

```
传统 LLM：
  用户问题 → LLM → 回答（仅凭训练数据）

RAG：
  用户问题 → 检索相关文档 → 文档 + 用户问题 → LLM → 回答（有据可依）
```

### 8.2 RAG 的完整流程

```
┌─────────────────── 离线阶段（Indexing）────────────────────┐
│                                                             │
│  文档 → 分块(Chunk) → Embedding 模型 → 向量 → 存入 Vector DB │
│                                                             │
│  "PydanticAI is a framework..."                             │
│      ↓ chunk                                                │
│  ["PydanticAI is a framework...", "It supports..."]         │
│      ↓ embed                                                │
│  [[0.12, -0.34, 0.56, ...], [0.78, -0.12, ...]]           │
│      ↓ store                                                │
│  Vector DB (Supabase pgvector / Pinecone / Qdrant)          │
│                                                             │
└─────────────────────────────────────────────────────────────┘

┌─────────────────── 在线阶段（Query）──────────────────────┐
│                                                             │
│  用户问题 → Embedding 模型 → 查询向量                        │
│      ↓ similarity search                                    │
│  Vector DB 返回 Top-K 最相关的 chunks                        │
│      ↓                                                      │
│  System Prompt + 相关 chunks + 用户问题 → LLM → 回答        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 8.3 用 PydanticAI 实现 RAG

PydanticAI 的 RAG 非常直观 — **把检索逻辑放在 Tool 里**：

```python
from dataclasses import dataclass
from supabase import AsyncClient
from openai import AsyncOpenAI
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

# ============================================================
# 1. 定义依赖
# ============================================================

@dataclass
class RAGDeps:
    supabase: AsyncClient        # 数据库（含 pgvector）
    openai: AsyncOpenAI          # 用于生成 embedding
    user_id: str

# ============================================================
# 2. 定义输出
# ============================================================

class RAGAnswer(BaseModel):
    answer: str
    sources: list[str]           # 引用的文档来源
    confidence: float            # 0-1

# ============================================================
# 3. 创建 Agent + 检索 Tool
# ============================================================

rag_agent = Agent(
    model="openai:gpt-4.1",
    output_type=RAGAnswer,
    deps_type=RAGDeps,
    system_prompt="""\
You are a knowledge assistant. Use the retrieve_docs tool to find
relevant information before answering. Always cite your sources.
If you can't find relevant information, say so honestly.
""",
    retries=2,
)

@rag_agent.tool
async def retrieve_docs(ctx: RunContext[RAGDeps], query: str) -> str:
    """Search the knowledge base for documents relevant to the query.

    Use this tool to find information before answering any question.
    You can call it multiple times with different queries if needed.
    """
    # (a) 生成查询向量
    embedding_response = await ctx.deps.openai.embeddings.create(
        model="text-embedding-3-small",
        input=query,
    )
    query_vector = embedding_response.data[0].embedding

    # (b) 在 Supabase pgvector 中搜索
    result = await ctx.deps.supabase.rpc(
        "match_documents",
        {
            "query_embedding": query_vector,
            "match_threshold": 0.7,
            "match_count": 5,
        },
    ).execute()

    if not result.data:
        return "No relevant documents found."

    # (c) 格式化返回给 LLM
    chunks = []
    for doc in result.data:
        chunks.append(
            f"[Source: {doc['source']}] (similarity: {doc['similarity']:.2f})\n"
            f"{doc['content']}"
        )
    return "\n\n---\n\n".join(chunks)

# ============================================================
# 4. 运行
# ============================================================

async def answer_question(question: str, user_id: str):
    deps = RAGDeps(
        supabase=get_supabase_client(),
        openai=AsyncOpenAI(api_key=settings.openai_api_key),
        user_id=user_id,
    )
    result = await rag_agent.run(question, deps=deps)
    return result.output  # RAGAnswer(answer="...", sources=[...], confidence=0.85)
```

### 8.4 Indexing Pipeline（文档入库）

```python
from openai import AsyncOpenAI

async def index_document(
    supabase: AsyncClient,
    openai_client: AsyncOpenAI,
    content: str,
    source: str,
    metadata: dict = None,
):
    """将文档分块、embedding、存入 pgvector."""

    # (1) 分块 — 简单按字符数分
    chunks = chunk_text(content, chunk_size=500, overlap=50)

    # (2) 批量 embedding
    embedding_response = await openai_client.embeddings.create(
        model="text-embedding-3-small",
        input=chunks,
    )

    # (3) 存入 Supabase (pgvector)
    rows = []
    for i, (chunk, emb_data) in enumerate(zip(chunks, embedding_response.data)):
        rows.append({
            "content": chunk,
            "embedding": emb_data.embedding,  # list[float], 1536 维
            "source": source,
            "metadata": metadata or {},
            "chunk_index": i,
        })

    await supabase.table("documents").insert(rows).execute()


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """将长文本切分为重叠的 chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # 向前重叠，避免句子被截断
    return chunks
```

### 8.5 Supabase pgvector 数据库设置

```sql
-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 文档表
CREATE TABLE documents (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    content TEXT NOT NULL,
    embedding VECTOR(1536),          -- OpenAI text-embedding-3-small 的维度
    source TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    chunk_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 向量相似度搜索索引（IVFFlat，适合 <100万 条记录）
CREATE INDEX ON documents
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- 搜索函数
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(1536),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    source TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        d.id,
        d.content,
        d.source,
        d.metadata,
        1 - (d.embedding <=> query_embedding) AS similarity
    FROM documents d
    WHERE 1 - (d.embedding <=> query_embedding) > match_threshold
    ORDER BY d.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
```

### 8.6 完整 RAG 架构（融入 SmIA 项目的话）

```
┌──────────────── SmIA + RAG 架构 ────────────────────┐
│                                                      │
│  POST /api/analyze (现有)                             │
│  ├── PydanticAI Agent (工具路由)                       │
│  │   ├── fetch_hackernews_tool                       │
│  │   ├── fetch_youtube_tool                          │
│  │   └── ...                                         │
│  │                                                    │
│  POST /api/ask (新增 RAG)                             │
│  ├── PydanticAI Agent (RAG 路由)                      │
│  │   ├── retrieve_docs_tool ← pgvector 搜索           │
│  │   └── (可选) search_web_tool ← 互联网补充           │
│  │                                                    │
│  POST /api/index (新增 Indexing)                      │
│  └── 分块 → Embedding → pgvector 入库                  │
│                                                      │
│  ┌───────────────────────────────────┐                │
│  │        Supabase PostgreSQL        │                │
│  │  ┌─────────────┐ ┌────────────┐  │                │
│  │  │ documents   │ │ daily_     │  │                │
│  │  │ (pgvector)  │ │ digests    │  │                │
│  │  └─────────────┘ └────────────┘  │                │
│  └───────────────────────────────────┘                │
└──────────────────────────────────────────────────────┘
```

### 8.7 高级技巧：Hybrid Search

结合关键词搜索 + 向量搜索，效果更好：

```python
@rag_agent.tool
async def hybrid_search(ctx: RunContext[RAGDeps], query: str) -> str:
    """Search using both semantic similarity and keyword matching."""
    # 向量搜索
    vector_results = await vector_search(ctx.deps, query, limit=5)

    # 关键词搜索（PostgreSQL full-text search）
    keyword_results = await ctx.deps.supabase.rpc(
        "keyword_search",
        {"search_query": query, "match_count": 5},
    ).execute()

    # 合并去重，按综合分数排序
    combined = merge_and_rerank(vector_results, keyword_results.data)
    return format_results(combined)
```

### 8.8 添加 Langfuse 可观测性

```python
@observe(name="rag_retrieve")
async def retrieve_docs(ctx: RunContext[RAGDeps], query: str) -> str:
    """检索文档 — 自动被 Langfuse 追踪."""
    # Langfuse 会记录：
    # - 函数执行时间
    # - 嵌套在 agent 的 trace 下
    # - 可以看到每次检索的 query 和返回的 chunks 数量
    ...
```

---

## 9. PydanticAI vs LangChain 对比

### 9.1 核心理念差异

| 维度 | PydanticAI | LangChain |
|------|-----------|-----------|
| **理念** | 用 Python 类型系统驱动 AI | 用抽象链式（Chain）组合 AI 组件 |
| **复杂度** | 极简 — 一个 Agent 类就够 | 重度抽象 — Chain, Memory, Retriever, VectorStore, Loader... |
| **学习曲线** | 低 — 会 Pydantic 就会用 | 高 — 大量概念和 API 要记 |
| **类型安全** | 完整 — 泛型、类型推断 | 弱 — 大量 `Any` 和 `dict` |
| **灵活性** | 高 — 你控制所有逻辑 | 中 — 框架决定很多事 |
| **生态** | 小（新框架） | 大（但质量参差不齐） |

### 9.2 RAG 代码对比

#### PydanticAI 版本

```python
# ✅ PydanticAI：简洁、透明、类型安全

@dataclass
class RAGDeps:
    supabase: AsyncClient
    openai: AsyncOpenAI

agent = Agent(
    model="openai:gpt-4.1",
    output_type=RAGAnswer,
    deps_type=RAGDeps,
    system_prompt="Answer questions using retrieved documents.",
)

@agent.tool
async def retrieve(ctx: RunContext[RAGDeps], query: str) -> str:
    # 你完全控制检索逻辑
    embedding = await ctx.deps.openai.embeddings.create(
        model="text-embedding-3-small", input=query
    )
    results = await ctx.deps.supabase.rpc(
        "match_documents",
        {"query_embedding": embedding.data[0].embedding, "match_count": 5}
    ).execute()
    return "\n".join(r["content"] for r in results.data)

# 运行
result = await agent.run("What is PydanticAI?", deps=deps)
answer: RAGAnswer = result.output
```

#### LangChain 版本

```python
# LangChain：更多抽象、更多导入、更多概念

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. Embedding 模型
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 2. Vector Store（LangChain 的抽象）
vector_store = SupabaseVectorStore(
    client=supabase_client,
    embedding=embeddings,
    table_name="documents",
    query_name="match_documents",
)

# 3. Retriever（从 vector store 自动创建）
retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5},
)

# 4. Prompt 模板
prompt = ChatPromptTemplate.from_messages([
    ("system", "Answer questions using this context:\n\n{context}"),
    ("human", "{question}"),
])

# 5. LLM
llm = ChatOpenAI(model="gpt-4.1")

# 6. Chain（LCEL 语法）
chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
    | StrOutputParser()
)

# 运行
answer = await chain.ainvoke("What is PydanticAI?")
# answer 是 str，不是类型安全的对象
```

### 9.3 Indexing 对比

#### PydanticAI 版本

```python
# 你自己写分块和 embedding 逻辑
async def index_doc(content: str, source: str):
    chunks = chunk_text(content, chunk_size=500, overlap=50)
    embeddings = await openai.embeddings.create(
        model="text-embedding-3-small", input=chunks
    )
    rows = [
        {"content": c, "embedding": e.embedding, "source": source}
        for c, e in zip(chunks, embeddings.data)
    ]
    await supabase.table("documents").insert(rows).execute()
```

#### LangChain 版本

```python
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader

# LangChain 有大量内置 Loader 和 Splitter
loader = TextLoader("document.txt")
docs = loader.load()

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = splitter.split_documents(docs)

# 自动 embedding + 入库
vector_store.add_documents(chunks)
```

### 9.4 何时选哪个？

| 场景 | 推荐 | 原因 |
|------|------|------|
| **你已经有 FastAPI + Pydantic** | PydanticAI | 无缝集成，同一个类型系统 |
| **需要类型安全的结构化输出** | PydanticAI | 这是它的核心优势 |
| **需要大量内置 Loader/Splitter** | LangChain | 生态丰富（PDF, HTML, Notion...） |
| **需要快速原型** | LangChain | 开箱即用的组件多 |
| **生产系统** | PydanticAI | 更少抽象 = 更少 bug |
| **Agent + Tools** | PydanticAI | Tool 就是函数，简单直接 |
| **复杂 Chain（多步骤 pipeline）** | LangChain | LCEL 表达力强（虽然难读） |
| **团队新手多** | PydanticAI | 学习成本低，代码可读 |

### 9.5 混合使用的可能

你可以用 PydanticAI 做 Agent 层，用 LangChain 的 text_splitter 做 chunking：

```python
# 只用 LangChain 的分块器
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", ".", " "],  # 按自然边界分块
)

# 其他一切用 PydanticAI
chunks = splitter.split_text(content)
# ... 然后自己 embedding + pgvector
```

LangChain 的 text splitter 是它最好的独立组件之一，完全可以单独使用。

---

## 附录 A：PydanticAI API 速查

```python
from pydantic_ai import Agent, RunContext

# --- 创建 Agent ---
agent = Agent(
    model="openai:gpt-4.1",           # 模型
    output_type=MyModel,               # Pydantic 输出类型
    deps_type=MyDeps,                  # 依赖类型（可选）
    system_prompt="...",               # 系统提示词
    tools=[tool1, tool2],              # 工具列表（方式一）
    retries=2,                         # 验证失败重试次数
    name="my-agent",                   # 名称（用于 tracing）
    defer_model_check=True,            # 延迟模型验证
)

# --- 注册 Tool（方式二：装饰器）---
@agent.tool
async def my_tool(ctx: RunContext[MyDeps], query: str) -> str:
    """Tool description — LLM 靠这个决定何时调用."""
    db = ctx.deps.db  # 访问注入的依赖
    return "result string"

# --- 运行 ---
result = await agent.run("user input", deps=my_deps)
result.output        # MyModel 实例
result.usage()       # Usage(request_tokens=..., response_tokens=..., total_tokens=...)

# --- 流式运行（SmIA 没有使用）---
async with agent.run_stream("user input", deps=my_deps) as stream:
    async for chunk in stream.stream_text():
        print(chunk, end="")

# --- Instrument for Langfuse ---
Agent.instrument_all()  # 全局 instrument 所有 agent
```

## 附录 B：Langfuse API 速查

```python
from langfuse import observe, get_client

# --- 初始化 ---
# 设置环境变量后自动初始化：
# LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST

# --- @observe 装饰器 ---
@observe(name="my_function")     # 自动创建 span
async def my_function():
    pass

@observe()                       # 使用函数名作为 span name
async def another_function():
    pass

# --- 获取当前 trace ---
client = get_client()
trace_id = client.get_current_trace_id()

# --- 更新 trace 元数据 ---
client.update_current_trace(
    user_id="user_123",
    session_id="session_abc",
    tags=["analysis", "production"],
    metadata={"source": "web"},
)

# --- Flush ---
client.flush()  # 强制发送待发事件

# --- OpenAI 客户端包装 ---
from langfuse.openai import AsyncOpenAI  # 自动追踪所有调用
openai_client = AsyncOpenAI(api_key="...")
```

## 附录 C：Embedding 模型选择

| 模型 | 维度 | 价格 | 适用 |
|------|------|------|------|
| text-embedding-3-small | 1536 | $0.02/1M tokens | 通用，性价比高 |
| text-embedding-3-large | 3072 | $0.13/1M tokens | 高精度需求 |
| text-embedding-ada-002 | 1536 | $0.10/1M tokens | 旧版，不推荐 |

SmIA 推荐用 `text-embedding-3-small`，Supabase 免费版支持 pgvector。

## 附录 D：Vector DB 选择

| DB | 特点 | 适合 |
|----|------|------|
| Supabase pgvector | 和你的 PostgreSQL 一起，免运维 | SmIA（已用 Supabase） |
| Pinecone | 全托管，自动扩展 | 大规模（>100万文档） |
| Qdrant | 开源，功能丰富 | 需要高级过滤 |
| Weaviate | 内置 ML 模型 | 需要多模态搜索 |
| ChromaDB | 极简，本地开发 | 原型/实验 |

**SmIA 推荐 Supabase pgvector**：零额外基础设施，直接在现有数据库上启用。
