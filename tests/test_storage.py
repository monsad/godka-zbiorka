import json
import threading
import wave

import numpy as np
import pytest

from storage import Zbior, BladZgloszenia


@pytest.fixture
def zbior(tmp_path):
    return Zbior(tmp_path, threading.Lock(), sesja="test")


def wiersze(path):
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines()]


def test_tekst_zapisany(zbior, tmp_path):
    zbior.zapisz_tekst("  Jo żech je z Rudy, a ty skōnd żeś je?  ", "Ruda Śląska", zgoda=True)
    [w] = wiersze(tmp_path / "teksty-test.jsonl")
    assert w["tekst"] == "Jo żech je z Rudy, a ty skōnd żeś je?"
    assert w["miejscowosc"] == "Ruda Śląska"
    assert w["id"] and w["czas"]


def test_bez_zgody_odrzucone(zbior, tmp_path):
    with pytest.raises(BladZgloszenia, match="zgod"):
        zbior.zapisz_tekst("Jo żech je z Rudy, a ty?", "", zgoda=False)
    assert not (tmp_path / "teksty-test.jsonl").exists()


@pytest.mark.parametrize("tekst", ["", "krótki", "x" * 5001])
def test_zla_dlugosc_tekstu(zbior, tekst):
    with pytest.raises(BladZgloszenia):
        zbior.zapisz_tekst(tekst, "", zgoda=True)


def test_miejscowosc_przycieta(zbior, tmp_path):
    zbior.zapisz_tekst("Jo żech je z Rudy, a ty?", "a" * 500, zgoda=True)
    [w] = wiersze(tmp_path / "teksty-test.jsonl")
    assert len(w["miejscowosc"]) == 100


def test_nagranie_zapisane_jako_wav(zbior, tmp_path):
    sr = 16000
    dane = (np.sin(np.linspace(0, 100, sr * 2)) * 10000).astype(np.int16)
    zbior.zapisz_nagranie((sr, dane), "z1", "Jo żech je ze Ślōnska.", "Bytom", zgoda=True)
    [w] = wiersze(tmp_path / "nagrania-test.jsonl")
    assert w["zdanie_id"] == "z1" and w["sekundy"] == 2.0
    with wave.open(str(tmp_path / w["plik"])) as f:
        assert f.getframerate() == sr and f.getnchannels() == 1 and f.getnframes() == sr * 2


def test_nagranie_stereo_float_zamienione_na_mono(zbior, tmp_path):
    sr = 8000
    dane = np.full((sr, 2), 0.5, dtype=np.float32)
    zbior.zapisz_nagranie((sr, dane), "z1", "Zdanie.", "", zgoda=True)
    [w] = wiersze(tmp_path / "nagrania-test.jsonl")
    with wave.open(str(tmp_path / w["plik"])) as f:
        assert f.getnchannels() == 1 and f.getsampwidth() == 2


@pytest.mark.parametrize("sekundy", [0.5, 31])
def test_nagranie_zla_dlugosc(zbior, sekundy):
    sr = 8000
    dane = np.zeros(int(sr * sekundy), dtype=np.int16)
    with pytest.raises(BladZgloszenia):
        zbior.zapisz_nagranie((sr, dane), "z1", "Zdanie.", "", zgoda=True)


def test_brak_nagrania(zbior):
    with pytest.raises(BladZgloszenia, match="nagra"):
        zbior.zapisz_nagranie(None, "z1", "Zdanie.", "", zgoda=True)


def test_poprawka_zapisana(zbior, tmp_path):
    zbior.zapisz_poprawke("Dzień dobry", "Dobry dziyń", "Dobry dzień", "", zgoda=True)
    [w] = wiersze(tmp_path / "poprawki-test.jsonl")
    assert (w["pl"], w["bielik"], w["poprawka"]) == ("Dzień dobry", "Dobry dziyń", "Dobry dzień")


def test_pusta_poprawka_odrzucona(zbior):
    with pytest.raises(BladZgloszenia):
        zbior.zapisz_poprawke("Dzień dobry", "Dobry dziyń", "   ", "", zgoda=True)


def _wav_bytes(sr, dane, kanaly=1):
    import io
    buf = io.BytesIO()
    with wave.open(buf, "wb") as f:
        f.setnchannels(kanaly)
        f.setsampwidth(dane.dtype.itemsize)
        f.setframerate(sr)
        f.writeframes(dane.tobytes())
    return buf.getvalue()


def test_wav_z_przegladarki_mono():
    from storage import wav_do_numpy
    dane = np.arange(-100, 100, dtype=np.int16)
    sr, wynik = wav_do_numpy(_wav_bytes(48000, dane))
    assert sr == 48000 and np.array_equal(wynik, dane)


def test_wav_z_przegladarki_stereo():
    from storage import wav_do_numpy
    dane = np.array([[1, 3], [5, 7]], dtype=np.int16)
    sr, wynik = wav_do_numpy(_wav_bytes(44100, dane, kanaly=2))
    assert wynik.shape == (2, 2) and wynik[1, 1] == 7


def test_wav_uszkodzony():
    from storage import wav_do_numpy
    with pytest.raises(BladZgloszenia):
        wav_do_numpy(b"to nie jest wav")
