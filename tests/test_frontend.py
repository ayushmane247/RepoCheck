from fastapi.testclient import TestClient

from app.main import FRONTEND_BUILD_DIR, app


client = TestClient(app)


def test_frontend_serves_the_react_build_or_preserves_the_unbuilt_fallback():
    response = client.get("/")

    assert response.status_code == 200
    if (FRONTEND_BUILD_DIR / "index.html").is_file():
        assert "RepoCheck" in response.text
        assert 'id="root"' in response.text
        assert "/assets/" in response.text
        assert client.get("/rooftop-scout.svg").status_code == 200
        assert client.get("/opening-city.svg").status_code == 200
    else:
        assert 'id="intro-screen"' in response.text
        assert 'id="briefing-screen"' in response.text
        assert 'id="analysis-screen"' in response.text
        assert 'id="get-started"' in response.text
        assert 'id="skip-intro"' in response.text
        assert "<svg" in response.text


def test_frontend_assets_keep_api_accessibility_motion_and_feedback():
    if (FRONTEND_BUILD_DIR / "index.html").is_file():
        built_assets = list((FRONTEND_BUILD_DIR / "assets").glob("*.js"))
        built_css = list((FRONTEND_BUILD_DIR / "assets").glob("*.css"))
        assert built_assets and built_css
        assert client.get(f"/assets/{built_assets[0].name}").status_code == 200
        css = client.get(f"/assets/{built_css[0].name}").text
        assert "prefers-reduced-motion" in css
        assert ":focus-visible" in css
    else:
        stylesheet = client.get("/static/styles.css")
        script = client.get("/static/app.js")
        feedback = client.get("/static/feedback.js")
        assert stylesheet.status_code == 200
        assert "prefers-reduced-motion: reduce" in stylesheet.text
        assert ":focus-visible" in stylesheet.text
        assert script.status_code == 200
        assert 'fetch("/repositories/validate"' in script.text
        assert "The API returns a final result" in script.text
        assert feedback.status_code == 200
        assert "enrichFindings" in feedback.text


def test_report_controls_and_safe_text_rendering_are_in_the_active_frontend():
    page = client.get("/").text
    if (FRONTEND_BUILD_DIR / "index.html").is_file():
        app_bundle = next((FRONTEND_BUILD_DIR / "assets").glob("*.js"))
        script = client.get(f"/assets/{app_bundle.name}").text
        assert 'id="root"' in page
        assert "/repositories/validate" in script
        assert "COPY SUMMARY" in script
        assert "COPY REPORT" in script
        assert "TERMINAL RECORD" in script
        assert "WARNINGS" in script
    else:
        script = client.get("/static/app.js").text
        assert 'id="copy-summary"' in page
        assert 'id="copy-report"' in page
        assert 'data-copy="logs"' in page
        assert 'data-filter="warning"' in page
        assert 'data-filter="error"' in page
        assert 'id="run-again"' in page
        assert 'document.querySelector("#test-logs").textContent' in script
