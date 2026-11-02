import json
from pathlib import Path

from przeglad import do_oceny, przygotuj_publiczne, wczytaj_decyzje, wczytaj_zgloszenia, zapisz_decyzje


def dopisz(plik: Path, *wiersze):
    plik.parent.mkdir(parents=True, exist_ok=True)
    with plik.open("a", encoding="utf-8") as f:
        for w in wiersze:
            f.write(json.dumps(w, ensure_ascii=False) + "\n")


def skrzynka(tmp_path):
    s = tmp_path / "skrzynka"
    dopisz(s / "data" / "teksty-a.jsonl", {"id": "t1", "czas": "2026-11-02T10:00:00", "tekst": "Jo żech je z Rudy.", "miejscowosc": ""})
    dopisz(s / "data" / "poprawki-a.jsonl", {"id": "p1", "czas": "2026-11-02T09:00:00", "pl": "a", "bielik": "b", "poprawka": "c", "miejscowosc": "Bytōm"})
    dopisz(s / "data" / "nagrania-b.jsonl", {"id": "n1", "czas": "2026-11-02T11:00:00", "zdanie_id": "z", "zdanie": "Zdanie.", "plik": "nagrania/n1.wav", "sekundy": 2.0, "miejscowosc": ""})
    (s / "data" / "nagrania" / "n1.wav").parent.mkdir(parents=True)
    (s / "data" / "nagrania" / "n1.wav").write_bytes(b"RIFF-atrapa")
    return s


def test_zgloszenia_od_najstarszego_z_rodzajem(tmp_path):
    z = wczytaj_zgloszenia(skrzynka(tmp_path))
    assert [x["id"] for x in z] == ["p1", "t1", "n1"]
    assert [x["rodzaj"] for x in z] == ["poprawki", "teksty", "nagrania"]


def test_ocenione_nie_wracaja(tmp_path):
    s = skrzynka(tmp_path)
    zapisz_decyzje({"t1": "tak", "p1": "nie"}, s / "decyzje" / "1.jsonl")
    assert [x["id"] for x in do_oceny(wczytaj_zgloszenia(s), wczytaj_decyzje(s))] == ["n1"]


def test_pozniejsza_decyzja_wygrywa(tmp_path):
    s = tmp_path / "s"
    zapisz_decyzje({"t1": "nie"}, s / "decyzje" / "1.jsonl")
    zapisz_decyzje({"t1": "tak"}, s / "decyzje" / "2.jsonl")
    assert wczytaj_decyzje(s) == {"t1": "tak"}


def test_publiczne_tylko_zatwierdzone_z_nagraniami(tmp_path):
    s = skrzynka(tmp_path)
    zgl = {x["id"]: x for x in wczytaj_zgloszenia(s)}
    cel = tmp_path / "pub"
    przygotuj_publiczne([zgl["t1"], zgl["n1"]], s, cel, "X")
    assert sorted(p.relative_to(cel).as_posix() for p in cel.rglob("*") if p.is_file()) == [
        "data/nagrania-X.jsonl", "data/nagrania/n1.wav", "data/teksty-X.jsonl"]
    [w] = [json.loads(l) for l in (cel / "data" / "teksty-X.jsonl").read_text().splitlines()]
    assert w == {"id": "t1", "czas": "2026-11-02T10:00:00", "tekst": "Jo żech je z Rudy.", "miejscowosc": ""}
    assert (cel / "data" / "nagrania" / "n1.wav").read_bytes() == b"RIFF-atrapa"
