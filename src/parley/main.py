"""ASGI entry point for the Parley backend."""

from parley.bootstrap.application import create_application


app = create_application()
