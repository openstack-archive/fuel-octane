import io

from octane import app as o_app


def test_help():
    out, err = io.BytesIO(), io.BytesIO()
    app = o_app.OctaneApp(stdin=io.BytesIO(), stdout=out, stderr=err)
    try:
        rv = app.run(["--help"])
    except SystemExit as e:
        assert e.code == 0
    assert not err.getvalue()
    assert 'Could not' not in out.getvalue()
