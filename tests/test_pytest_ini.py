def test_pytest_ini_present():
    import pathlib

    assert pathlib.Path("pytest.ini").exists()
