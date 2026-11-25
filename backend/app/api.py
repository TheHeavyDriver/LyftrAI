"""FastAPI application factory and the three public contract routes."""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import Settings
from .database import Database
from .errors import AllProvidersUnavailable
from .gateway import LLMGateway, LiteLLMGateway
from .repository import SessionRepository
from .schemas import ChatMetadata, ChatRequest, ChatResponse
from .service import ChatService
from .simulation import parse_simulation_header

logger = logging.getLogger("lyftr.api")


def get_repository(request: Request) -> SessionRepository:
    return request.app.state.repository


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway


def get_service(request: Request) -> ChatService:
    return request.app.state.chat_service


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("LiteLLM").setLevel(logging.WARNING)
    logging.getLogger("LiteLLM Router").setLevel(logging.WARNING)


def create_app(
    settings: Settings | None = None,
    gateway: LLMGateway | None = None,
) -> FastAPI:
    settings = settings or Settings()
    _configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        database = Database(settings.database_url)
        await database.create_schema()
        repository = SessionRepository(database)
        active_gateway = gateway or LiteLLMGateway(settings)

        try:
            await active_gateway.startup()
        except Exception:
            await database.dispose()
            raise

        app.state.settings = settings
        app.state.database = database
        app.state.repository = repository
        app.state.gateway = active_gateway
        app.state.chat_service = ChatService(repository, active_gateway, settings)

        try:
            yield
        finally:
            await active_gateway.shutdown()
            await database.dispose()

    app = FastAPI(
        title="Lyftr AI",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.enable_docs else None,
        redoc_url="/redoc" if settings.enable_docs else None,
        openapi_url="/openapi.json" if settings.enable_docs else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Simulate-Failure", "Accept"],
    )

    @app.exception_handler(AllProvidersUnavailable)
    async def _all_providers_unavailable_handler(
        _request: Request, _exc: AllProvidersUnavailable
    ) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "all providers unavailable"}
        )

    @app.exception_handler(Exception)
    async def _unhandled_exception_handler(
        _request: Request, exc: Exception
    ) -> JSONResponse:
        # Log the traceback server-side only; never expose it to a client.
        logger.exception("unhandled_error error=%s", type(exc).__name__)
        return JSONResponse(
            status_code=500, content={"detail": "internal server error"}
        )

    @app.get("/health")
    async def health(
        repository: Annotated[SessionRepository, Depends(get_repository)],
        active_gateway: Annotated[LLMGateway, Depends(get_gateway)],
    ) -> JSONResponse:
        try:
            await repository.ping()
        except Exception:
            logger.warning("health_check_failed component=database")
            return JSONResponse(
                status_code=503, content={"detail": "database unavailable"}
            )

        if active_gateway.keys_configured < 2:
            return JSONResponse(
                status_code=503, content={"detail": "key pool unavailable"}
            )

        if not active_gateway.cache_enabled:
            return JSONResponse(
                status_code=503, content={"detail": "cache unavailable"}
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": "ok",
                "keys_configured": active_gateway.keys_configured,
                "cache_enabled": True,
            },
        )

    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        payload: ChatRequest,
        request: Request,
        service: Annotated[ChatService, Depends(get_service)],
        x_simulate_failure: Annotated[
            str | None, Header(alias="X-Simulate-Failure")
        ] = None,
    ) -> ChatResponse:
        request_id = uuid.uuid4().hex[:12]
        started = time.perf_counter()
        simulation = parse_simulation_header(
            x_simulate_failure,
            key_ids=settings.key_ids,
            enabled=settings.enable_failure_simulation,
        )

        try:
            result = await service.chat(
                session_id=payload.session_id,
                message=payload.message,
                system_prompt=payload.system_prompt,
                simulation=simulation,
            )
        except AllProvidersUnavailable:
            logger.warning(
                "chat_outcome request_id=%s session_id=%s outcome=all_providers_"
                "unavailable elapsed_ms=%s simulated=%s",
                request_id,
                payload.session_id,
                int((time.perf_counter() - started) * 1000),
                bool(simulation),
            )
            raise
        except Exception as exc:
            logger.exception(
                "chat_outcome request_id=%s session_id=%s outcome=error error=%s",
                request_id,
                payload.session_id,
                type(exc).__name__,
            )
            raise

        logger.info(
            "chat_outcome request_id=%s session_id=%s outcome=ok source=%s "
            "model=%s key_id=%s fallback_attempts=%s latency_ms=%s "
            "input_tokens=%s output_tokens=%s simulated=%s",
            request_id,
            payload.session_id,
            result.metadata["resolution_source"],
            result.metadata["model"],
            result.metadata["key_id"],
            result.metadata["fallback_attempts"],
            result.metadata["latency_ms"],
            result.metadata["input_tokens"],
            result.metadata["output_tokens"],
            bool(simulation),
        )

        return ChatResponse(
            session_id=result.session_id,
            reply=result.reply,
            metadata=ChatMetadata(**result.metadata),
        )

    @app.get("/sessions/{session_id}/messages")
    async def session_messages(
        session_id: str,
        repository: Annotated[SessionRepository, Depends(get_repository)],
    ) -> dict:
        session = await repository.get_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")

        records = await repository.get_messages(session_id)
        messages: list[dict] = []
        for record in records:
            item: dict = {"role": record.role, "content": record.content}
            if record.role == "assistant":
                try:
                    item["metadata"] = (
                        json.loads(record.metadata_json)
                        if record.metadata_json
                        else {}
                    )
                except (TypeError, ValueError):
                    item["metadata"] = {}
            messages.append(item)

        return {"session_id": session_id, "messages": messages}

    return app
