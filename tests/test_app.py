"""Test całej strony w przeglądarce-atrapie Streamlit (bez sieci, bez HF_TOKEN)."""
import io
import json
import wave
from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "streamlit_app.py"
DANE = APP.parent / "dane"


@pytest.fixture
def at(monkeypatch):
    monkeypatch.delenv("HF_TOKEN", raising=False)
    for p in DANE.glob("*.jsonl"):
        p.unlink()
    a = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not a.exception
    yield a
    for p in DANE.glob("*.jsonl"):
        p.unlink()


def wiersze(rodzaj):
    return [json.loads(l) for p in DANE.glob(f"{rodzaj}-*.jsonl") for l in p.read_text().splitlines()]


def test_tekst_bez_zgody_odrzucony(at):
    at.text_area[0].input("Jo żech je z Rudy, a ty skōnd żeś je?")
    at.button[0].click().run()
    assert any("zgod" in e.value for e in at.error)
    assert wiersze("teksty") == []


def test_tekst_z_zgoda_zapisany(at):
    at.text_input[0].input("Ruda Śląska")
    at.checkbox[0].check()
    at.text_area[0].input("Jo żech je z Rudy, a ty skōnd żeś je?")
    at.button[0].click().run()
    assert not at.error
    [w] = wiersze("teksty")
    assert w["miejscowosc"] == "Ruda Śląska"


def test_poprawka_zapisana_i_nowe_zdanie(at):
    at.checkbox[0].check()
    pl_przed = at.session_state["tl"]["pl"]
    at.text_area(key="poprawka").input("Moja poprawka po ślōnsku.")
    [b for b in at.button if b.label == "Wyślij poprawkę"][0].click().run()
    assert not at.exception and not at.error
    [w] = wiersze("poprawki")
    assert w["pl"] == pl_przed and w["poprawka"] == "Moja poprawka po ślōnsku."
