from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from app.core.config import settings


def test_migration_preserves_legacy_data_reports_and_evidence(
    tmp_path: Path, monkeypatch
) -> None:
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database}"
    monkeypatch.setattr(settings, "database_url", url)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    command.upgrade(config, "20261104_0005")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO platforms (id,name,slug,website_url) VALUES (1,'HTB','htb','https://example.com')"))
        connection.execute(text("INSERT INTO categories (id,name,slug,platform_id) VALUES (1,'Web','web',1)"))
        connection.execute(text("""
            INSERT INTO labs (id,title,slug,platform_id,category_id,status,notes,objective,
                vulnerability_description,impact,mitigation,learnings,resolution_steps)
            VALUES (1,'Legacy','legacy',1,1,'documented','general','objective','legacy vuln',
                'legacy impact','legacy fix','legacy learning','legacy steps')
        """))
        connection.execute(text("""
            INSERT INTO evidences (id,lab_id,original_filename,stored_filename,mime_type,file_size,
                sha256,description,display_order) VALUES (1,1,'proof.txt','proof.txt','text/plain',4,
                'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','proof',0)
        """))
        connection.execute(text("""
            INSERT INTO reports (id,lab_id,markdown,evidence_manifest,revision)
            VALUES (1,1,'# Manual preserved','{}',7)
        """))
    command.upgrade(config, "head")
    with engine.connect() as connection:
        finding = connection.execute(text("SELECT * FROM findings WHERE lab_id=1")).mappings().one()
        assert finding["description"] == "legacy vuln"
        assert finding["reproduction_steps"] == "legacy steps"
        assert connection.execute(text("SELECT markdown FROM reports WHERE lab_id=1")).scalar_one() == "# Manual preserved"
        evidence = connection.execute(text("SELECT finding_id FROM evidences WHERE id=1")).scalar_one_or_none()
        assert evidence is None
        legacy = connection.execute(text("SELECT vulnerability_description FROM labs WHERE id=1")).scalar_one()
        assert legacy == "legacy vuln"
        tables = set(inspect(connection).get_table_names())
        assert {"findings", "cvss_assessments", "legacy_ai_report_versions", "legacy_smart_evidence_analyses"}.issubset(tables)
        assert "ai_report_versions" not in tables and "smart_evidence_analyses" not in tables
    engine.dispose()
