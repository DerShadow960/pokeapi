import logging
from contextlib import asynccontextmanager

import strawberry
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from strawberry.asgi import GraphQL
from strawberry.extensions import MaskErrors

from app import config
from app.db.database import init_db
from app.schema.mutations import Mutation
from app.schema.queries import Query
from app.services import pokemon_service as service

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


def _should_mask(error) -> bool:
    # Se muestran los UserError y los errores de sintaxis/validación de GraphQL; lo demás se oculta.
    original = error.original_error
    return original is not None and not isinstance(original, service.UserError)


class AppSchema(strawberry.Schema):
    def process_errors(self, errors, execution_context=None):
        # Los UserError son respuestas esperadas, no fallas: no se registran como errores.
        unexpected = [e for e in errors if not isinstance(e.original_error, service.UserError)]
        super().process_errors(unexpected, execution_context)


schema = AppSchema(
    query=Query,
    mutation=Mutation,
    extensions=[MaskErrors(should_mask_error=_should_mask, error_message="Error interno. Intenta de nuevo.")],
)


@asynccontextmanager
async def lifespan(app):
    init_db()
    try:
        await service.ensure_index()
        log.info("Índice listo")
    except service.UserError:
        log.warning("Arrancando sin índice; se reintentará en la primera búsqueda")
    yield


app = Starlette(
    routes=[Route("/graphql", GraphQL(schema))],
    middleware=[Middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_methods=["GET", "POST"], allow_headers=["*"])],
    lifespan=lifespan,
)