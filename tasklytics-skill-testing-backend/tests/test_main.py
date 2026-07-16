"""Regression test for the nginx /api proxy prefix fix.

nginx proxies /api/ -> this app's root, stripping the prefix before
forwarding (nginx/default.conf). Without root_path="/api" set on the
FastAPI app, Swagger UI's embedded openapi.json fetch and the OpenAPI
schema's `servers` entry are generated root-relative, ignoring the proxy
prefix - this breaks /api/docs in production even though route matching
itself still works. See app/main.py's comment on the FastAPI() call for
the full explanation, and PHASE_5_EXECUTION_TRACKER.md for the incident
this fixes.

This test can't exercise real reverse-proxy behavior the way an actual
end-to-end HTTP request through nginx does - see the manual verification
performed when this fix landed for that. What it *can* catch: someone
later removing root_path="/api" by accident, which would silently
reintroduce the bug without any test failing to say so otherwise.
"""

from app.main import app


class TestApiProxyPrefixConfiguration:
    def test_root_path_is_set_for_the_api_proxy_prefix(self):
        assert app.root_path == "/api"

    def test_openapi_schema_advertises_the_proxy_prefix(self, client):
        # Deliberately a real request through the ASGI app (via the `client`
        # fixture), not a direct app.openapi() call: FastAPI only injects the
        # `servers` field from request-scope root_path handling when actually
        # serving /openapi.json, not when the schema dict is built in isolation
        # - confirmed by hitting this exact gap when first writing this test.
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert resp.json().get("servers") == [{"url": "/api"}]

    def test_docs_page_embeds_prefixed_openapi_url(self, client):
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "/api/openapi.json" in resp.text
